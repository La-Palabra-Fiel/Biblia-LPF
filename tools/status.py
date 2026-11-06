#!/usr/bin/env python3
"""Print LBF status. Never writes `done` or `ready`."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUS_PATH = ROOT / "STATUS.md"

# Protestant verse counts. Never MT.
EXPECTED_VERSES = {
    "genesis": 1533,
    "exodo": 1213,
    "levitico": 859,
    "numeros": 1288,
    "deuteronomio": 959,
    "josue": 658,
    "jueces": 618,
    "rut": 85,
    "1samuel": 810,
    "2samuel": 695,
    "1reyes": 816,
    "2reyes": 719,
    "1cronicas": 942,
    "2cronicas": 822,
    "esdras": 280,
    "nehemias": 406,
    "ester": 167,
    "job": 1070,
    "salmos": 2461,
    "proverbios": 915,
    "eclesiastes": 222,
    "cantares": 117,
    "isaias": 1292,
    "jeremias": 1364,
    "lamentaciones": 154,
    "ezequiel": 1273,
    "daniel": 357,
    "oseas": 197,
    "joel": 73,
    "amos": 146,
    "abdias": 21,
    "jonas": 48,
    "miqueas": 105,
    "nahum": 47,
    "habacuc": 56,
    "sofonias": 53,
    "hageo": 38,
    "zacarias": 211,
    "malaquias": 55,
    "mateo": 1071,
    "marcos": 678,
    "lucas": 1151,
    "juan": 879,
    "hechos": 1007,
    "romanos": 433,
    "1corintios": 437,
    "2corintios": 257,
    "galatas": 149,
    "efesios": 155,
    "filipenses": 104,
    "colosenses": 95,
    "1tesalonicenses": 89,
    "2tesalonicenses": 47,
    "1timoteo": 113,
    "2timoteo": 83,
    "titus": 46,
    "filemon": 25,
    "hebreos": 303,
    "santiago": 108,
    "1pedro": 105,
    "2pedro": 61,
    "1juan": 105,
    "2juan": 13,
    "3juan": 15,
    "judas": 25,
    "apocalipsis": 404,
}

VERSE_HEADING = re.compile(r"^###\s+(\d+):(\d+)\s*$")
REF_IN_LINK = re.compile(r"(\d+):(\d+)")
AUTO_METHODS = {"auto", "auto-zip"}
GLOSS_METHODS = {"gloss", "gloss-match", "gloss-seed", "verse-span-resynchronization"}
HAND_METHODS = {"hand", "manual", "manual-realign"}
# Finished phrase statuses. `mapped` = map-integrity acceptance in Translator
# (Spanish + gloss/Strong's pairing). `hand`/`manual`/`manual-realign` =
# source walk or legacy. Seeded-* statuses remain unfinished.
FINISHED_LINK_STATUSES = {"mapped", "hand", "manual", "manual-realign"}
HAND_LINK_STATUSES = FINISHED_LINK_STATUSES  # alias for older callers
CHECKED_STATES = {"ready", "done"}


def words_only_surface(text: str) -> bool:
    return bool(re.fullmatch(r"[^\W_]+(?:\s+[^\W_]+)*", str(text or ""), re.UNICODE))


def translation_path(book: str, testament: str) -> Path:
    return ROOT / "translation" / testament / f"{book}.md"


def alignment_path(book: str, testament: str) -> Path:
    return ROOT / "alignment" / testament / book / f"{book}-reverse-links.json"


def parse_verses(path: Path) -> dict[tuple[int, int], str]:
    verses: dict[tuple[int, int], str] = {}
    if not path.is_file():
        return verses
    cur: tuple[int, int] | None = None
    buf: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = VERSE_HEADING.match(line)
        if match:
            if cur is not None:
                verses[cur] = " ".join(buf).strip()
            cur = (int(match.group(1)), int(match.group(2)))
            buf = []
            continue
        if cur is not None and line.strip() and not line.startswith("#") and not line.startswith(">"):
            buf.append(line.strip())
    if cur is not None:
        verses[cur] = " ".join(buf).strip()
    return verses


def count_verses(path: Path) -> int:
    return len(parse_verses(path))


def alignment_counts(path: Path) -> dict[str, int]:
    counts = Counter()
    if not path.is_file():
        return {
            "phrases": 0,
            "hand": 0,
            "auto": 0,
            "gloss": 0,
            "unwalked": 0,
            "unconfirmed": 0,
            "other": 0,
        }
    data = json.loads(path.read_text(encoding="utf-8"))
    for link in data.get("links") or []:
        counts["phrases"] += 1
        units = link.get("units") or []
        status = str(link.get("status") or "")
        if not units or status == "unwalked":
            counts["unwalked"] += 1
            continue
        methods = [str(unit.get("method") or "") for unit in units]
        if any(method in AUTO_METHODS for method in methods):
            counts["auto"] += 1
        elif any(method in GLOSS_METHODS for method in methods):
            counts["gloss"] += 1
        elif status not in FINISHED_LINK_STATUSES:
            # Unit-level `method: hand` is not finished. Seeded links become
            # `mapped` only through explicit phrase map-acceptance in Translator.
            counts["unconfirmed"] += 1
        elif all(method in HAND_METHODS for method in methods):
            counts["hand"] += 1
        else:
            counts["other"] += 1
    return counts


def translation_errors(book: str, testament: str, expected: int | None) -> list[str]:
    path = translation_path(book, testament)
    if not path.is_file():
        return [f"{book}: translation file missing"]
    verses = parse_verses(path)
    if expected is not None and len(verses) != expected:
        return [f"{book}: translation verses are {len(verses)}, expected {expected}"]
    return []


def ai_alignment_audit_path(book: str, testament: str) -> Path:
    return ROOT / "alignment" / testament / book / f"{book}-ai-alignment-audit.json"


def ai_alignment_audit_errors(book: str, testament: str, link_count: int) -> list[str]:
    """Require a passing AI alignment audit covering every phrase."""
    path = ai_alignment_audit_path(book, testament)
    if not path.is_file():
        return [
            f"{book}: missing AI alignment audit "
            f"(run: python3 tools/audit_alignment_ai.py {book})"
        ]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [f"{book}: AI alignment audit is not valid JSON"]
    errors: list[str] = []
    if str(data.get("verdict") or "") != "pass":
        summary = data.get("summary") or {}
        errors.append(
            f"{book}: AI alignment audit verdict is {data.get('verdict')!r} "
            f"(fail={summary.get('fail', '?')} error={summary.get('error', '?')})"
        )
    phrases = data.get("phrases") or []
    covered = {
        int(row["phraseIndex"])
        for row in phrases
        if isinstance(row, dict) and "phraseIndex" in row
    }
    if link_count and len(covered) < link_count:
        errors.append(
            f"{book}: AI alignment audit covers {len(covered)} phrases, expected {link_count}"
        )
    bad = [
        row
        for row in phrases
        if isinstance(row, dict) and str(row.get("verdict") or "") in {"fail", "error"}
    ]
    if bad:
        sample = ", ".join(
            f"{row.get('phraseIndex')}:{row.get('reference') or '?'}" for row in bad[:5]
        )
        errors.append(f"{book}: AI alignment audit still has fail/error phrases ({sample})")
    return errors


def alignment_errors(book: str, testament: str, expected: int | None) -> list[str]:
    path = alignment_path(book, testament)
    if not path.is_file():
        return [f"{book}: alignment file missing"]
    data = json.loads(path.read_text(encoding="utf-8"))
    links = data.get("links") or []
    if not links:
        return [f"{book}: alignment has no links"]

    errors: list[str] = []
    counts = alignment_counts(path)
    if (
        counts["auto"]
        or counts["gloss"]
        or counts["unwalked"]
        or counts["unconfirmed"]
        or counts["other"]
    ):
        errors.append(
            f"{book}: alignment still has auto={counts['auto']} gloss={counts['gloss']} "
            f"unwalked={counts['unwalked']} unconfirmed={counts['unconfirmed']} "
            f"other={counts['other']}"
        )
    if counts["hand"] == 0:
        errors.append(f"{book}: alignment has no finished map units")

    verses = parse_verses(translation_path(book, testament))
    links_by_verse: dict[tuple[int, int], list[dict]] = {}
    word_surface_errors: set[tuple[int, int]] = set()
    for link in links:
        match = REF_IN_LINK.search(str(link.get("reference") or ""))
        if not match:
            errors.append(f"{book}: alignment link missing verse reference")
            continue
        key = (int(match.group(1)), int(match.group(2)))
        links_by_verse.setdefault(key, []).append(link)
        for unit in link.get("units") or []:
            if not unit.get("sourceTokenIds"):
                errors.append(f"{book} {key[0]}:{key[1]}: a unit has no source tokens")
                break
            if not words_only_surface(unit.get("surface") or ""):
                if key not in word_surface_errors:
                    errors.append(
                        f"{book} {key[0]}:{key[1]}: alignment surfaces must contain words only"
                    )
                    word_surface_errors.add(key)
                break

    for key, verse_links in links_by_verse.items():
        reconstructed = "".join(
            str(unit.get("surface") or "")
            for link in verse_links
            for unit in (link.get("units") or [])
        )
        expected_text = verses.get(key, "")
        # Reverse links are phrase-level. Unit surfaces intentionally omit the
        # whitespace and punctuation between units, so compare the complete
        # verse's ordered lexical text after removing those separators.
        normalized_units = re.sub(r"[^\w]+", "", reconstructed, flags=re.UNICODE).casefold()
        normalized_verse = re.sub(r"[^\w]+", "", expected_text, flags=re.UNICODE).casefold()
        if expected_text and normalized_units != normalized_verse:
            errors.append(f"{book} {key[0]}:{key[1]}: units do not reconstruct Spanish")

    covered = set(links_by_verse)
    if expected is not None and len(covered) != expected:
        errors.append(f"{book}: alignment covers {len(covered)} verses, expected {expected}")
    missing = sorted(set(verses) - covered)
    if missing:
        shown = ", ".join(f"{ch}:{vs}" for ch, vs in missing[:5])
        errors.append(f"{book}: alignment missing verses {shown}")

    # AI lexical check: required for the `mapped` finish path (non-Hebraist owner).
    # Legacy hand/manual books stay valid without an audit until one is written.
    link_statuses = {str(link.get("status") or "") for link in links}
    audit_file = ai_alignment_audit_path(book, testament)
    if "mapped" in link_statuses or audit_file.is_file():
        errors.extend(ai_alignment_audit_errors(book, testament, len(links)))
    return errors


def parse_status_table(text: str) -> list[dict[str, str]]:
    rows = []
    for line in text.splitlines():
        if not line.startswith("| "):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 9 or cells[0] in {"book", "---"} or cells[0].startswith("-"):
            continue
        rows.append(
            {
                "book": cells[0],
                "testament": cells[1],
                "translation": cells[2],
                "alignment": cells[3],
                "translation_by": cells[4],
                "translation_on": cells[5],
                "alignment_by": cells[6],
                "alignment_on": cells[7],
                "notes": cells[8] if len(cells) > 8 else "",
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("book", nargs="?", help="Check one book slug. Default: every book.")
    args = parser.parse_args()
    if not STATUS_PATH.is_file():
        print("STATUS.md is missing", file=sys.stderr)
        return 2
    rows = parse_status_table(STATUS_PATH.read_text(encoding="utf-8"))
    if not rows:
        print("STATUS.md has no book rows", file=sys.stderr)
        return 2
    if args.book:
        rows = [row for row in rows if row["book"] == args.book]
        if not rows:
            print(f"{args.book} is not in STATUS.md", file=sys.stderr)
            return 2

    errors: list[str] = []
    print(
        f"{'book':<16} {'tr':<7} {'verses':<12} {'al':<7} "
        f"{'hand':<6} {'auto':<6} {'gloss':<6} {'unw':<6} {'unconf':<7}"
    )
    for row in rows:
        book = row["book"]
        testament = row["testament"]
        expected = EXPECTED_VERSES.get(book)
        t_path = translation_path(book, testament)
        a_path = alignment_path(book, testament)
        verses = count_verses(t_path)
        counts = alignment_counts(a_path)
        verse_label = f"{verses}/{expected}" if expected is not None else str(verses)
        print(
            f"{book:<16} {row['translation']:<7} {verse_label:<12} {row['alignment']:<7} "
            f"{counts['hand']:<6} {counts['auto']:<6} {counts['gloss']:<6} "
            f"{counts['unwalked']:<6} {counts['unconfirmed']:<7}"
        )

        if row["translation"] in CHECKED_STATES:
            errors.extend(translation_errors(book, testament, expected))
            if row["translation"] == "done" and (not row["translation_by"] or not row["translation_on"]):
                errors.append(f"{book}: translation is done but unsigned")
        if row["alignment"] in CHECKED_STATES:
            errors.extend(alignment_errors(book, testament, expected))
            if row["alignment"] == "done" and (not row["alignment_by"] or not row["alignment_on"]):
                errors.append(f"{book}: alignment is done but unsigned")

    if errors:
        print("\nFAILED")
        for item in errors:
            print(f"  {item}")
        return 1
    print("\nOK — no stale ready/done labels")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
