#!/usr/bin/env python3
"""Export an LPF book for a cgv-data publisher PR.

Does not write a checked-out cgv-data working tree.
Complete publication requires translation and alignment both `done` in
STATUS.md. ``--progressive`` permits a committed unfinished book when at least
one chapter has explicit human approval and canonical alignment.

``LBF`` remains the historical technical identifier in filenames and paths.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from publication_progress import approved_progress_source_paths, publication_progress

ROOT = Path(__file__).resolve().parents[1]
STATUS_PATH = ROOT / "STATUS.md"

CONSUMER_LABEL = {
    "zacarias": "Zechariah",
    "daniel": "Daniel",
    "titus": "Tito",
    "1juan": "1Juan",
    "1pedro": "1Pedro",
    "judas": "Judas",
    "filipenses": "Filipenses",
}

VERSE_HEADING = re.compile(r"^###\s+(\d+):(\d+)\s*$")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_status_row(book: str) -> dict[str, str]:
    for line in STATUS_PATH.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| "):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 8 or cells[0] != book:
            continue
        return {
            "book": cells[0],
            "testament": cells[1],
            "translation": cells[2],
            "alignment": cells[3],
            "translation_by": cells[4],
            "translation_on": cells[5],
            "alignment_by": cells[6],
            "alignment_on": cells[7],
        }
    raise SystemExit(f"{book} is not in STATUS.md")


def parse_verses(path: Path) -> list[tuple[int, int, str]]:
    verses: list[tuple[int, int, str]] = []
    cur: tuple[int, int] | None = None
    buf: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = VERSE_HEADING.match(line)
        if m:
            if cur is not None:
                verses.append((cur[0], cur[1], " ".join(buf).strip()))
            cur = (int(m.group(1)), int(m.group(2)))
            buf = []
            continue
        if cur is not None and line.strip() and not line.startswith("#") and not line.startswith(">"):
            buf.append(line.strip())
    if cur is not None:
        verses.append((cur[0], cur[1], " ".join(buf).strip()))
    return verses


def git_head() -> str:
    return subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
    ).strip()


def git(repo: Path, *args: str, check: bool = True) -> str:
    proc = subprocess.run(["git", "-C", str(repo), *args], text=True, capture_output=True)
    if check and proc.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def raw_status_row(text: str, book: str) -> str | None:
    for line in text.splitlines():
        if not line.startswith("| "):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if cells and cells[0] == book:
            return " | ".join(cells)
    return None


def committed_source_problem(
    book: str, row: dict[str, str], extra_paths: list[Path] | None = None
) -> str | None:
    """Why this book's `sourceCommit` would not name the work, or None if it would.

    `git_head()` records whatever HEAD happens to be; that says nothing about
    whether the bound text, alignment, or signature was ever committed. A
    package stamped against an uncommitted state carries provenance that
    cannot be resolved from the commit it names, so neither export nor
    publish may proceed past this.

    Only this book is checked. STATUS.md is one ledger for every book, so an
    unrelated pending row must not block an unrelated publish.

    Returns a message for the caller to report; callers choose the exit code.
    """
    problems: list[str] = []
    scoped_paths = [
        f"translation/{row['testament']}/{book}.md",
        f"alignment/{row['testament']}/{book}",
    ]
    scoped_paths.extend(
        str(path.relative_to(ROOT)) for path in (extra_paths or []) if path.is_relative_to(ROOT)
    )
    dirty = git(ROOT, "status", "--porcelain", "--", *scoped_paths)
    if dirty:
        problems.append(dirty)
    head_row = raw_status_row(git(ROOT, "show", "HEAD:STATUS.md", check=False), book)
    live_row = raw_status_row(STATUS_PATH.read_text(encoding="utf-8"), book)
    if head_row != live_row:
        problems.append(f"   STATUS.md row for {book} differs from HEAD (signature uncommitted)")
    if not problems:
        return None
    return (
        "the bound source is not committed:\n"
        + "\n".join(problems)
        + "\nA sourceCommit must name a commit that contains this work.\n"
        f"Commit Biblia-LBF, then export: python3 tools/export.py {book}"
    )


def build_consumer(
    book: str,
    row: dict[str, str],
    verses: list[tuple[int, int, str]],
    commit: str,
    progress: dict,
) -> str:
    label = CONSUMER_LABEL.get(book, book)
    header = [
        "<!-- LPF (technical id: LBF)",
        f"     book: {book}",
        f"     bookStatus: {progress['bookStatus']}",
        f"     translation: {row['translation']}",
        f"     alignment: {row['alignment']}",
        f"     approvedChapters: {','.join(map(str, progress['approvedChapters']))}",
        f"     draftChapters: {','.join(map(str, progress['draftChapters']))}",
        f"     progress: bibles/LBF/status/{book}.status.json",
        f"     translation_by: {row['translation_by']}",
        f"     translation_on: {row['translation_on']}",
        f"     alignment_by: {row['alignment_by']}",
        f"     alignment_on: {row['alignment_on']}",
        f"     source: Biblia-LBF/translation/{row['testament']}/{book}.md",
        f"     sourceCommit: {commit}",
        "-->",
    ]
    lines = header + [f"{label} {ch}:{vs} {text}" for ch, vs, text in verses]
    return "\n".join(lines) + "\n"


def build_alignment(
    book: str, row: dict[str, str], src: Path, commit: str, progress: dict
) -> dict:
    data = json.loads(src.read_text(encoding="utf-8"))
    return {
        "generated": True,
        "doNotEdit": True,
        "sourceRepository": "La-Biblia-Fiel/Biblia-LBF",
        "sourceCommit": commit,
        "sourceFile": str(src.relative_to(ROOT)),
        "sourceSha256": sha256_file(src),
        "generator": "tools/export.py",
        "publishedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "bookId": book,
        "technicalBibleId": "LBF",
        "displayName": "LPF",
        "bookStatus": progress["bookStatus"],
        "chapterStatuses": progress["chapterStatuses"],
        "approvedChapters": progress["approvedChapters"],
        "draftChapters": progress["draftChapters"],
        "textualBasis": data.get("textualBasis"),
        "schemaVersion": data.get("schemaVersion", 1),
        "numbering": data.get("numbering", "protestant"),
        "translation_by": row["translation_by"],
        "alignment_by": row["alignment_by"],
        "links": data["links"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("book")
    parser.add_argument(
        "--progressive",
        action="store_true",
        help="Export human-approved chapters while the overall book remains unfinished",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("/tmp/lbf-export"),
        help="Directory for the export package (default: /tmp/lbf-export)",
    )
    args = parser.parse_args()
    book = args.book
    row = parse_status_row(book)
    finished = row["translation"] == "done" and row["alignment"] == "done"
    if not finished and not args.progressive:
        print(
            f"{book} is not finished. translation={row['translation']} alignment={row['alignment']}. "
            "Use --progressive only to publish explicitly approved chapters as work in progress.",
            file=sys.stderr,
        )
        return 2
    if finished and (not row["translation_by"] or not row["alignment_by"]):
        print(f"{book} is done but unsigned", file=sys.stderr)
        return 2

    t_path = ROOT / "translation" / row["testament"] / f"{book}.md"
    a_path = ROOT / "alignment" / row["testament"] / book / f"{book}-reverse-links.json"
    if not t_path.is_file() or not a_path.is_file():
        print("missing translation or alignment file", file=sys.stderr)
        return 2

    progress = publication_progress(
        book=book,
        testament=row["testament"],
        book_finished=finished,
    )
    if args.progressive and not progress["approvedChapters"]:
        print(f"{book} has no chapter eligible for progressive publication", file=sys.stderr)
        return 2
    progress_sources = approved_progress_source_paths(progress, row["testament"])
    problem = committed_source_problem(book, row, progress_sources)
    if problem:
        print(problem, file=sys.stderr)
        return 2

    if finished:
        check = subprocess.run([sys.executable, str(ROOT / "tools" / "status.py"), book], cwd=ROOT)
        if check.returncode != 0:
            return check.returncode

    verses = parse_verses(t_path)
    commit = git_head()
    progress["sourceCommit"] = commit
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    consumer = out / f"{book}.lbf.md"
    alignment = out / f"{book}.alignment.json"
    status_file = out / f"{book}.status.json"
    consumer.write_text(build_consumer(book, row, verses, commit, progress), encoding="utf-8")
    alignment.write_text(
        json.dumps(build_alignment(book, row, a_path, commit, progress), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    status_file.write_text(
        json.dumps(progress, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(consumer)
    print(alignment)
    print(status_file)
    print(f"verses {len(verses)}")
    print(
        f"bookStatus {progress['bookStatus']} approvedChapters "
        f"{len(progress['approvedChapters'])}/{progress['chapterCount']}"
    )
    print(f"sourceCommit {commit}")
    print("Do not copy these into a checked-out cgv-data tree. Open a publisher PR.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
