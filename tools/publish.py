#!/usr/bin/env python3
"""Publish an exported LPF book to cgv-data as a publisher PR branch.

Consumes the package written by `tools/export.py`. It does not write the
caller's `cgv-data` working tree: the commit is made in a temporary git
worktree cut from `<remote>/<base>`, so the branch contains only the three
historical LBF technical paths and a dirty local checkout is left untouched.

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
    git,
    git_head,
    parse_status_row,
    sha256_file,
)
from publication_progress import approved_progress_source_paths, publication_progress  # noqa: E402

TEXT_TARGET = "bibles/LBF/{book}.lbf.md"
ALIGN_TARGET = "bibles/LBF/alignments/{book}.alignment.json"
STATUS_TARGET = "bibles/LBF/status/{book}.status.json"

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


def read_package(pkg: Path, book: str) -> tuple[Path, Path, Path, dict, dict]:
    text_path = pkg / f"{book}.lbf.md"
    align_path = pkg / f"{book}.alignment.json"
    status_path = pkg / f"{book}.status.json"
    missing = [str(p) for p in (text_path, align_path, status_path) if not p.is_file()]
    if missing:
        raise SystemExit(
            "export package incomplete: " + ", ".join(missing) + f"\nRun: python3 tools/export.py {book} --out {pkg}"
        )
    meta = json.loads(align_path.read_text(encoding="utf-8"))
    progress = json.loads(status_path.read_text(encoding="utf-8"))
    return text_path, align_path, status_path, meta, progress


def check_package_current(
    book: str,
    row: dict[str, str],
    text_path: Path,
    meta: dict,
    progress: dict,
) -> None:
    """Refuse a package that no longer matches the repository it came from."""
    head = git_head()
    header = HEADER_COMMIT.search(text_path.read_text(encoding="utf-8"))
    if not header:
        raise SystemExit(f"{text_path} has no sourceCommit header. Re-export.")
    text_commit = header.group(1)
    align_commit = meta.get("sourceCommit")
    progress_commit = progress.get("sourceCommit")
    if text_commit != align_commit or text_commit != progress_commit:
        raise SystemExit(
            f"package is inconsistent: text sourceCommit {text_commit[:12]} "
            f"alignment {str(align_commit)[:12]} progress {str(progress_commit)[:12]}. Re-export."
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
    finished = progress.get("bookStatus") == "approved"
    if finished:
        if row["translation"] != "done" or row["alignment"] != "done":
            raise SystemExit(
                f"{book} is not finished. translation={row['translation']} alignment={row['alignment']}"
            )
        if not row["translation_by"] or not row["alignment_by"]:
            raise SystemExit(f"{book} is done but unsigned")
    else:
        if progress.get("schema") != "lpf-publication-progress-v1":
            raise SystemExit("progressive package has no supported LPF status schema. Re-export.")
        current = publication_progress(
            book=book,
            testament=row["testament"],
            book_finished=False,
            source_commit=head,
        )
        for key in ("bookStatus", "chapterStatuses", "approvedChapters", "draftChapters"):
            if progress.get(key) != current.get(key):
                raise SystemExit(f"progressive package {key} is stale. Re-export.")
        if not progress.get("approvedChapters"):
            raise SystemExit(f"{book} has no approved chapter to publish progressively")


def status_gate(book: str) -> None:
    check = subprocess.run([sys.executable, str(ROOT / "tools" / "status.py"), book], cwd=ROOT)
    if check.returncode != 0:
        raise SystemExit("tools/status.py failed. Not publishing.")


def branch_name(book: str, meta: dict) -> str:
    stamp = PUBLISHED_AT.match(str(meta.get("publishedAt", "")))
    if not stamp:
        raise SystemExit("package alignment has no usable publishedAt. Re-export.")
    return f"lbf-{book}-{''.join(stamp.groups())}"


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
    status_path: Path,
    message: str,
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
        targets = {
            TEXT_TARGET.format(book=book): text_path,
            ALIGN_TARGET.format(book=book): align_path,
            STATUS_TARGET.format(book=book): status_path,
        }
        for rel, src in targets.items():
            dest = work / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)
        git(work, "add", "--", *targets)
        staged = git(work, "diff", "--cached", "--name-only")
        if not staged:
            raise SystemExit(f"{book} is already published at {base_ref}. Nothing to do.")
        # Only the three historical LBF technical paths may appear. Fewer is normal: republishing an
        # unchanged book restages only the alignment, whose publishedAt moves.
        unexpected = sorted(set(staged.splitlines()) - set(targets))
        if unexpected:
            raise SystemExit("refusing to commit unexpected paths:\n  " + "\n  ".join(unexpected))
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
    args = parser.parse_args()

    book = args.book
    row = parse_status_row(book)
    text_path, align_path, progress_path, meta, progress = read_package(args.package, book)
    progress_sources = approved_progress_source_paths(progress, row["testament"])
    problem = committed_source_problem(book, row, progress_sources)
    if problem:
        raise SystemExit(problem)
    check_package_current(book, row, text_path, meta, progress)
    if progress.get("bookStatus") == "approved":
        status_gate(book)

    repo = resolve_data_repo(args.data_repo)
    require_data_repo(repo)
    branch = args.branch or branch_name(book, meta)
    base_ref = start_point(repo, args.remote, args.base, fetch=not args.no_fetch)
    label = DISPLAY_NAME.get(book, book.capitalize())
    mode = "approved" if progress.get("bookStatus") == "approved" else "unfinished"
    message = f"Publish {mode} {label} LPF text, alignment, and status."

    sha = publish(
        book, repo, branch, base_ref, text_path, align_path, progress_path, message
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
