#!/usr/bin/env python3
"""Publish an exported LPF book to cgv-data as a publisher PR branch.

Consumes the package written by `tools/export.py`. It does not write the
caller's `cgv-data` working tree: the commit is made in a temporary git
worktree cut from `<remote>/<base>`, so the branch contains only the two
historical LBF technical paths and a dirty local checkout is left untouched.

An explicit corrective migration may additionally remove the two generated
source-ID aliases from an earlier bad publication.  That mode is guarded by a
declared source-to-consumer mapping and validates both aliases before deletion.

`cgv-data` is output only. This script never reads LBF text or alignment
back from it.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from export import (  # noqa: E402
    ROOT,
    committed_source_problem,
    committed_reader_bridge_problem,
    git,
    git_head,
    load_reader_token_bridge,
    parse_status_row,
    sha256_file,
)
from consumer_books import consumer_book_id  # noqa: E402

TEXT_TARGET = "bibles/LBF/{book}.lbf.md"
ALIGN_TARGET = "bibles/LBF/alignments/{book}.alignment.json"

DATA_REPO_SLUG = "cgv-data"
COMPARE_URL = (
    "https://github.com/Cultivados-en-Gracia-y-Verdad/cgv-data/compare/{base}...{branch}?expand=1"
)

# Spanish display names for the commit subject. The verse-label map lives in
# export.py and is a different thing: it prefixes every consumer line.
DISPLAY_NAME = {
    "1juan": "1 Juan",
    "1pedro": "1 Pedro",
    "apocalipsis": "Apocalipsis",
    "daniel": "Daniel",
    "filipenses": "Filipenses",
    "judas": "Judas",
    "titus": "Tito",
    "zacarias": "Zacarías",
}

HEADER_COMMIT = re.compile(r"^\s*sourceCommit:\s*([0-9a-f]{40})\s*$", re.MULTILINE)
HEADER_BOOK = re.compile(r"^\s*book:\s*([^\s]+)\s*$", re.MULTILINE)
HEADER_SOURCE = re.compile(r"^\s*source:\s*(\S+)\s*$", re.MULTILINE)
PUBLISHED_AT = re.compile(r"^(\d{4})-(\d{2})-(\d{2})T")


def resolve_data_repo(arg: Path | None) -> Path:
    candidates = [arg] if arg else []
    candidates.append(ROOT.parent / "cgv-data")
    for cand in candidates:
        if cand and (cand / ".git").exists():
            return cand.resolve()
    raise SystemExit(
        "cgv-data checkout not found. Pass --data-repo, or set CGV_DATA. "
        "Do not point this at an empty repository."
    )


def require_data_repo(repo: Path) -> None:
    url = git(repo, "remote", "get-url", "origin", check=False)
    if DATA_REPO_SLUG not in url:
        raise SystemExit(f"{repo} origin is not cgv-data: {url or '<no origin>'}")
    if not git(repo, "rev-parse", "--verify", "HEAD", check=False):
        raise SystemExit(f"{repo} has no commits. That is not the real cgv-data.")


def read_package(pkg: Path, book: str) -> tuple[Path, Path, dict]:
    consumer_id = consumer_book_id(book)
    text_path = pkg / f"{consumer_id}.lbf.md"
    align_path = pkg / f"{consumer_id}.alignment.json"
    missing = [str(p) for p in (text_path, align_path) if not p.is_file()]
    if missing:
        raise SystemExit(
            "export package incomplete: " + ", ".join(missing) + f"\nRun: python3 tools/export.py {book} --out {pkg}"
        )
    meta = json.loads(align_path.read_text(encoding="utf-8"))
    if meta.get("bookId") != consumer_id:
        raise SystemExit(
            f"package alignment bookId is {meta.get('bookId')!r}, expected {consumer_id!r}. Re-export."
        )
    if meta.get("sourceBookId") != book:
        raise SystemExit(
            f"package alignment sourceBookId is {meta.get('sourceBookId')!r}, expected {book!r}. Re-export."
        )
    return text_path, align_path, meta


def check_package_current(book: str, row: dict[str, str], text_path: Path, meta: dict) -> None:
    """Refuse a package that no longer matches the repository it came from."""
    head = git_head()
    text = text_path.read_text(encoding="utf-8")
    header = HEADER_COMMIT.search(text)
    if not header:
        raise SystemExit(f"{text_path} has no sourceCommit header. Re-export.")
    header_book = HEADER_BOOK.search(text)
    expected_consumer_id = consumer_book_id(book)
    if not header_book or header_book.group(1) != expected_consumer_id:
        raise SystemExit(
            f"{text_path} does not declare consumer book {expected_consumer_id}. Re-export."
        )
    text_commit = header.group(1)
    align_commit = meta.get("sourceCommit")
    if text_commit != align_commit:
        raise SystemExit(
            f"package is inconsistent: text sourceCommit {text_commit[:12]} "
            f"but alignment sourceCommit {str(align_commit)[:12]}. Re-export."
        )
    if text_commit != head:
        raise SystemExit(
            f"package is stale: exported at {text_commit[:12]}, Biblia-LBF HEAD is {head[:12]}.\n"
            f"Re-export before publishing: python3 tools/export.py {book}"
        )
    source_file = meta.get("sourceFile")
    if not source_file:
        raise SystemExit("package alignment has no sourceFile. Re-export.")
    live = ROOT / source_file
    if not live.is_file():
        raise SystemExit(f"alignment source is gone: {source_file}")
    if sha256_file(live) != meta.get("sourceSha256"):
        raise SystemExit(
            f"{source_file} changed since the export. The signature no longer binds it.\n"
            f"Re-export, or clear the `done` signature per DATA_CONTRACT.md."
        )
    reader_bridge = meta.get("readerTokenBridge")
    if row["testament"] == "nt":
        load_reader_token_bridge(book)
        if not isinstance(reader_bridge, dict):
            raise SystemExit("NT package has no explicit TR-to-Reader token bridge. Re-export.")
        bridge_path = ROOT / str(reader_bridge.get("bridgeFile") or "")
        if not bridge_path.is_file() or sha256_file(bridge_path) != reader_bridge.get("bridgeSha256"):
            raise SystemExit("NT package Reader token bridge is stale. Rebuild and re-export.")
    if row["translation"] != "done" or row["alignment"] != "done":
        raise SystemExit(
            f"{book} is not finished. translation={row['translation']} alignment={row['alignment']}"
        )
    if not row["translation_by"] or not row["alignment_by"]:
        raise SystemExit(f"{book} is done but unsigned")


def status_gate(book: str) -> None:
    check = subprocess.run([sys.executable, str(ROOT / "tools" / "status.py"), book], cwd=ROOT)
    if check.returncode != 0:
        raise SystemExit("tools/status.py failed. Not publishing.")


def branch_name(book: str, meta: dict) -> str:
    stamp = PUBLISHED_AT.match(str(meta.get("publishedAt", "")))
    if not stamp:
        raise SystemExit("package alignment has no usable publishedAt. Re-export.")
    return f"lbf-{consumer_book_id(book)}-{''.join(stamp.groups())}"


def validate_mispublished_aliases(
    work: Path,
    source_book: str,
    consumer_id: str,
    testament: str,
    package_meta: dict,
) -> list[str]:
    """Validate the exact generated alias pair before corrective deletion."""
    if source_book == consumer_id:
        raise SystemExit(
            "--cleanup-mispublished-source-id requires a declared source-to-consumer ID mapping"
        )

    text_rel = TEXT_TARGET.format(book=source_book)
    align_rel = ALIGN_TARGET.format(book=source_book)
    text_path = work / text_rel
    align_path = work / align_rel
    missing = [
        rel
        for rel, path in ((text_rel, text_path), (align_rel, align_path))
        if not path.is_file()
    ]
    if missing:
        raise SystemExit(
            "corrective cleanup requires the complete mispublished alias pair; missing:\n  "
            + "\n  ".join(missing)
        )

    text = text_path.read_text(encoding="utf-8")
    alias_book = HEADER_BOOK.search(text)
    alias_source = HEADER_SOURCE.search(text)
    alias_commit = HEADER_COMMIT.search(text)
    expected_source = f"Biblia-LBF/translation/{testament}/{source_book}.md"
    if not alias_book or alias_book.group(1) != source_book:
        raise SystemExit(f"refusing cleanup: {text_rel} does not declare book {source_book}")
    if not alias_source or alias_source.group(1) != expected_source:
        raise SystemExit(f"refusing cleanup: {text_rel} has unexpected source provenance")
    if not alias_commit:
        raise SystemExit(f"refusing cleanup: {text_rel} has no sourceCommit")

    try:
        alias_meta = json.loads(align_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"refusing cleanup: {align_rel} is malformed JSON: {exc}") from exc
    expected_alignment = {
        "generated": True,
        "doNotEdit": True,
        "sourceRepository": package_meta.get("sourceRepository"),
        "sourceFile": package_meta.get("sourceFile"),
        "generator": "tools/export.py",
        "bookId": source_book,
    }
    mismatches = [
        key for key, expected in expected_alignment.items() if alias_meta.get(key) != expected
    ]
    if mismatches:
        raise SystemExit(
            f"refusing cleanup: {align_rel} has unexpected generated provenance fields: "
            + ", ".join(mismatches)
        )
    if alias_meta.get("sourceCommit") != alias_commit.group(1):
        raise SystemExit("refusing cleanup: mispublished text/alignment sourceCommit values differ")
    return [text_rel, align_rel]


def start_point(repo: Path, remote: str, base: str, fetch: bool) -> str:
    if fetch:
        proc = subprocess.run(
            ["git", "-C", str(repo), "fetch", "--quiet", remote, base],
            text=True,
            capture_output=True,
        )
        if proc.returncode != 0:
            print(
                f"warning: could not fetch {remote}/{base} ({proc.stderr.strip() or 'no network'}). "
                f"Cutting the branch from the local ref, which may be behind.",
                file=sys.stderr,
            )
    tracking = f"{remote}/{base}"
    if git(repo, "rev-parse", "--verify", tracking, check=False):
        return tracking
    if git(repo, "rev-parse", "--verify", base, check=False):
        print(f"warning: {tracking} not found. Using local {base}.", file=sys.stderr)
        return base
    raise SystemExit(f"neither {tracking} nor {base} exists in {repo}")


def publish(
    book: str,
    repo: Path,
    branch: str,
    base_ref: str,
    text_path: Path,
    align_path: Path,
    package_meta: dict,
    testament: str,
    message: str,
    cleanup_mispublished_source_id: bool = False,
) -> str:
    if git(repo, "rev-parse", "--verify", branch, check=False):
        raise SystemExit(
            f"branch {branch} already exists in {repo}. "
            f"Delete it or finish the PR it belongs to."
        )
    tmp = Path(tempfile.mkdtemp(prefix=f"lbf-publish-{book}-"))
    work = tmp / "cgv-data"
    try:
        git(repo, "worktree", "add", "--quiet", "-b", branch, str(work), base_ref)
        consumer_id = consumer_book_id(book)
        targets = {
            TEXT_TARGET.format(book=consumer_id): text_path,
            ALIGN_TARGET.format(book=consumer_id): align_path,
        }
        cleanup_paths: list[str] = []
        if cleanup_mispublished_source_id:
            cleanup_paths = validate_mispublished_aliases(
                work,
                book,
                consumer_id,
                testament,
                package_meta,
            )
        for rel, src in targets.items():
            dest = work / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)
        for rel in cleanup_paths:
            (work / rel).unlink()
        expected_paths = set(targets) | set(cleanup_paths)
        git(work, "add", "--all", "--", *sorted(expected_paths))
        # Disable rename detection here: a correct consumer-ID repair replaces
        # two nearly identical generated files, but the safety gate must audit
        # all four literal paths rather than Git's collapsed rename display.
        staged = git(work, "diff", "--cached", "--name-only", "--no-renames")
        if not staged:
            raise SystemExit(f"{book} is already published at {base_ref}. Nothing to do.")
        staged_paths = set(staged.splitlines())
        # Only the two LBF paths may appear. Fewer is normal: republishing an
        # unchanged book restages only the alignment, whose publishedAt moves.
        unexpected = sorted(staged_paths - expected_paths)
        if unexpected:
            raise SystemExit("refusing to commit unexpected paths:\n  " + "\n  ".join(unexpected))
        if cleanup_mispublished_source_id and staged_paths != expected_paths:
            missing = sorted(expected_paths - staged_paths)
            raise SystemExit(
                "corrective cleanup must atomically change all four expected paths; unchanged:\n  "
                + "\n  ".join(missing)
            )
        git(work, "commit", "--quiet", "-m", message)
        sha = git(work, "rev-parse", "HEAD")
        print(git(work, "show", "--stat", "--oneline", "HEAD"))
        return sha
    finally:
        subprocess.run(
            ["git", "-C", str(repo), "worktree", "remove", "--force", str(work)],
            capture_output=True,
        )
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("book")
    parser.add_argument(
        "--package",
        type=Path,
        default=Path("/tmp/lbf-export"),
        help="Export package directory (default: /tmp/lbf-export)",
    )
    parser.add_argument(
        "--data-repo",
        type=Path,
        default=None,
        help="cgv-data checkout (default: sibling ../cgv-data)",
    )
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--base", default="main")
    parser.add_argument("--branch", default=None, help="Override the branch name")
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push the branch. Off by default: the commit is made locally first.",
    )
    parser.add_argument("--no-fetch", action="store_true", help="Do not fetch before branching")
    parser.add_argument(
        "--cleanup-mispublished-source-id",
        action="store_true",
        help=(
            "Atomically remove the validated generated source-ID alias pair while publishing "
            "to a declared consumer ID. Intended only for corrective migrations."
        ),
    )
    args = parser.parse_args()

    book = args.book
    row = parse_status_row(book)
    text_path, align_path, meta = read_package(args.package, book)
    problem = committed_source_problem(book, row)
    if problem:
        raise SystemExit(problem)
    bridge_problem = committed_reader_bridge_problem(row)
    if bridge_problem:
        raise SystemExit(bridge_problem)
    check_package_current(book, row, text_path, meta)
    status_gate(book)

    repo = resolve_data_repo(args.data_repo)
    require_data_repo(repo)
    branch = args.branch or branch_name(book, meta)
    base_ref = start_point(repo, args.remote, args.base, fetch=not args.no_fetch)
    label = DISPLAY_NAME.get(book, book.capitalize())
    message = (
        f"Correct {label} consumer ID and publish signed LPF text and alignment."
        if args.cleanup_mispublished_source_id
        else f"Publish signed {label} LPF text and alignment."
    )

    sha = publish(
        book,
        repo,
        branch,
        base_ref,
        text_path,
        align_path,
        meta,
        row["testament"],
        message,
        cleanup_mispublished_source_id=args.cleanup_mispublished_source_id,
    )

    print(f"\nbranch {branch}")
    print(f"commit {sha}")
    print(f"repo   {repo}")
    if not args.push:
        print("\nPUSH not requested. The branch exists locally only. To finish:")
        print(f"  git -C {repo} push -u {args.remote} {branch}")
        print(f"  {COMPARE_URL.format(base=args.base, branch=branch)}")
        return 0

    proc = subprocess.run(
        ["git", "-C", str(repo), "push", "-u", args.remote, branch],
        text=True,
    )
    if proc.returncode != 0:
        print(
            f"push failed. The branch is still in {repo}; push it yourself when you have network.",
            file=sys.stderr,
        )
        return 1
    print(f"\nOpen the publisher PR:\n  {COMPARE_URL.format(base=args.base, branch=branch)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
