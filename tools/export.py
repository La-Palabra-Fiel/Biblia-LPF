#!/usr/bin/env python3
"""Export a finished LPF book for a cgv-data publisher PR.

Does not write a checked-out cgv-data working tree.
Requires translation and alignment both `done` in STATUS.md.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from consumer_books import consumer_book_id

ROOT = Path(__file__).resolve().parents[1]
STATUS_PATH = ROOT / "STATUS.md"
READER_TOKEN_BRIDGE_PATH = ROOT / "source" / "greek" / "TR1894" / "reader-token-bridge.json"

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


def committed_source_problem(book: str, row: dict[str, str]) -> str | None:
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
    dirty = git(
        ROOT,
        "status",
        "--porcelain",
        "--",
        f"translation/{row['testament']}/{book}.md",
        f"alignment/{row['testament']}/{book}",
    )
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
    consumer_id: str,
    row: dict[str, str],
    verses: list[tuple[int, int, str]],
    commit: str,
) -> str:
    label = CONSUMER_LABEL.get(book, book)
    header = [
        "<!-- LPF (technical id: LBF)",
        f"     book: {consumer_id}",
        "     translation: done",
        "     alignment: done",
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


def load_reader_token_bridge(book: str) -> tuple[dict, dict]:
    if not READER_TOKEN_BRIDGE_PATH.is_file():
        raise SystemExit(
            "NT Reader token bridge is missing. "
            "Run: python3 tools/build_nt_reader_token_bridge.py"
        )
    bridge = json.loads(READER_TOKEN_BRIDGE_PATH.read_text(encoding="utf-8"))
    if bridge.get("schema") != "lpf-tr-to-reader-token-bridge-v1":
        raise SystemExit("NT Reader token bridge has an unsupported schema")
    generator = bridge.get("generator") or {}
    generator_path = ROOT / str(generator.get("path") or "")
    if (
        generator.get("command") != "python3 tools/build_nt_reader_token_bridge.py"
        or not generator_path.is_file()
        or sha256_file(generator_path) != generator.get("sha256")
    ):
        raise SystemExit(
            "NT Reader token bridge generator is stale. "
            "Run: python3 tools/build_nt_reader_token_bridge.py"
        )
    book_bridge = (bridge.get("books") or {}).get(book)
    if not isinstance(book_bridge, dict):
        raise SystemExit(f"NT Reader token bridge has no entry for {book}")
    return bridge, book_bridge


def committed_reader_bridge_problem(row: dict[str, str]) -> str | None:
    if row["testament"] != "nt":
        return None
    required = [READER_TOKEN_BRIDGE_PATH, ROOT / "tools" / "build_nt_reader_token_bridge.py"]
    problems: list[str] = []
    for path in required:
        relative = str(path.relative_to(ROOT))
        committed = git(ROOT, "show", f"HEAD:{relative}", check=False)
        if not committed:
            problems.append(f"{relative} is not present at HEAD")
            continue
        committed_hash = hashlib.sha256((committed + "\n").encode("utf-8")).hexdigest()
        if committed_hash != sha256_file(path):
            problems.append(f"{relative} differs from HEAD")
    if not problems:
        return None
    return (
        "the NT Reader token bridge is not committed:\n"
        + "\n".join(f"   {problem}" for problem in problems)
        + "\nCommit the bridge and its generator before exporting."
    )


NT_SOURCE_TOKEN_ID = re.compile(r"^n(\d{2})(\d{3})(\d{3})(\d{3})$")


def reader_token_id(source_token_id: str, book_bridge: dict) -> str | None:
    match = NT_SOURCE_TOKEN_ID.fullmatch(source_token_id)
    if not match:
        raise SystemExit(f"invalid canonical NT source token id: {source_token_id}")
    book_code, chapter, verse, ordinal = (int(value) for value in match.groups())
    expected_code = int(book_bridge.get("bookCode", 0))
    if book_code != expected_code:
        raise SystemExit(
            f"canonical token {source_token_id} belongs to book {book_code}, expected {expected_code}"
        )
    verse_map = (book_bridge.get("verses") or {}).get(f"{chapter}:{verse}")
    if not isinstance(verse_map, list) or ordinal < 1 or ordinal > len(verse_map):
        raise SystemExit(f"Reader token bridge does not cover canonical token {source_token_id}")
    reader_ordinal = verse_map[ordinal - 1]
    if reader_ordinal is None:
        return None
    return f"n{book_code:02d}{chapter:03d}{verse:03d}{int(reader_ordinal):03d}"


def build_reader_links(book: str, links: list[dict]) -> tuple[list[dict], dict]:
    bridge, book_bridge = load_reader_token_bridge(book)
    exported = copy.deepcopy(links)
    canonical_ids: set[str] = set()
    reader_ids: set[str] = set()
    unmapped_ids: set[str] = set()
    for link in exported:
        for unit in link.get("units") or []:
            original = [str(value) for value in (unit.get("sourceTokenIds") or [])]
            unit["canonicalSourceTokenIds"] = original
            mapped: list[str] = []
            for source_token_id in original:
                canonical_ids.add(source_token_id)
                target = reader_token_id(source_token_id, book_bridge)
                if target is None:
                    unmapped_ids.add(source_token_id)
                elif target not in mapped:
                    mapped.append(target)
                    reader_ids.add(target)
            unit["sourceTokenIds"] = mapped
    metadata = {
        "schema": bridge["schema"],
        "mappingPolicy": bridge["mappingPolicy"],
        "sourceTokenBasis": bridge["sourceTokenBasis"],
        "readerTokenBasis": bridge["readerTokenBasis"],
        "referenceDataset": bridge["referenceDataset"],
        "referenceRevision": bridge["referenceRevision"],
        "bridgeFile": str(READER_TOKEN_BRIDGE_PATH.relative_to(ROOT)),
        "bridgeSha256": sha256_file(READER_TOKEN_BRIDGE_PATH),
        "canonicalSourceTokenField": "canonicalSourceTokenIds",
        "readerSourceTokenField": "sourceTokenIds",
        "canonicalTokenCount": len(canonical_ids),
        "mappedReaderTokenCount": len(reader_ids),
        "unmappedCanonicalTokenCount": len(unmapped_ids),
    }
    return exported, metadata


def build_alignment(
    book: str,
    consumer_id: str,
    row: dict[str, str],
    src: Path,
    commit: str,
) -> dict:
    data = json.loads(src.read_text(encoding="utf-8"))
    links = data["links"]
    reader_bridge = None
    if row["testament"] == "nt":
        links, reader_bridge = build_reader_links(book, links)
    result = {
        "generated": True,
        "doNotEdit": True,
        "sourceRepository": "La-Palabra-Fiel/Biblia-LPF",
        "sourceCommit": commit,
        "sourceFile": str(src.relative_to(ROOT)),
        "sourceSha256": sha256_file(src),
        "generator": "tools/export.py",
        "publishedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "bookId": consumer_id,
        "sourceBookId": book,
        "textualBasis": data.get("textualBasis"),
        "schemaVersion": data.get("schemaVersion", 1),
        "numbering": data.get("numbering", "protestant"),
        "translation_by": row["translation_by"],
        "alignment_by": row["alignment_by"],
        "links": links,
    }
    if reader_bridge is not None:
        result["readerTokenBridge"] = reader_bridge
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("book")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("/tmp/lbf-export"),
        help="Directory for the export package (default: /tmp/lbf-export)",
    )
    args = parser.parse_args()
    book = args.book
    consumer_id = consumer_book_id(book)
    row = parse_status_row(book)
    if row["translation"] != "done" or row["alignment"] != "done":
        print(
            f"{book} is not finished. translation={row['translation']} alignment={row['alignment']}",
            file=sys.stderr,
        )
        return 2
    if not row["translation_by"] or not row["alignment_by"]:
        print(f"{book} is done but unsigned", file=sys.stderr)
        return 2

    t_path = ROOT / "translation" / row["testament"] / f"{book}.md"
    a_path = ROOT / "alignment" / row["testament"] / book / f"{book}-reverse-links.json"
    if not t_path.is_file() or not a_path.is_file():
        print("missing translation or alignment file", file=sys.stderr)
        return 2

    problem = committed_source_problem(book, row)
    if problem:
        print(problem, file=sys.stderr)
        return 2
    bridge_problem = committed_reader_bridge_problem(row)
    if bridge_problem:
        print(bridge_problem, file=sys.stderr)
        return 2

    check = subprocess.run([sys.executable, str(ROOT / "tools" / "status.py"), book], cwd=ROOT)
    if check.returncode != 0:
        return check.returncode

    verses = parse_verses(t_path)
    commit = git_head()
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    consumer = out / f"{consumer_id}.lbf.md"
    alignment = out / f"{consumer_id}.alignment.json"
    consumer.write_text(
        build_consumer(book, consumer_id, row, verses, commit),
        encoding="utf-8",
    )
    alignment.write_text(
        json.dumps(
            build_alignment(book, consumer_id, row, a_path, commit),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(consumer)
    print(alignment)
    print(f"verses {len(verses)}")
    print(f"sourceCommit {commit}")
    print("Do not copy these into a checked-out cgv-data tree. Open a publisher PR.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
