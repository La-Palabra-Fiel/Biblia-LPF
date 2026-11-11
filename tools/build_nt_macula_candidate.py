#!/usr/bin/env python3
"""Build one review-only MACULA structural candidate for a TR1894 chapter."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "pipeline"))

from books import get_book  # noqa: E402
from nt_macula import (  # noqa: E402
    apply_structure_adjudications,
    apply_tr_authority_adaptations,
    apply_tr_authority_fallbacks,
    project_chapter_candidate,
    sha256,
    validate_mapping_ledger,
)

MAPPING = ROOT / "source" / "greek" / "TR1894" / "macula-structure-mapping.json"
MANIFEST = ROOT / "source" / "greek" / "TR1894" / "MACULA_GREEK_MANIFEST.json"
ADJUDICATIONS = ROOT / "source" / "greek" / "TR1894" / "MACULA_STRUCTURE_ADJUDICATIONS.json"


def chapter_adjudication_sha256(adjudications: dict, book: str, chapter: int) -> str:
    """Bind a candidate only to decisions that can alter that chapter."""
    relevant = [
        decision
        for decision in adjudications.get("decisions") or []
        if decision.get("book") == book and decision.get("chapter") == chapter
    ]
    payload = {
        "schema": adjudications.get("schema"),
        "book": book,
        "chapter": chapter,
        "decisions": relevant,
    }
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("book")
    parser.add_argument("chapter", type=int)
    args = parser.parse_args()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if sha256(MAPPING) != manifest.get("mapping", {}).get("sha256"):
        raise ValueError("MACULA Greek mapping ledger is stale")
    mapping = json.loads(MAPPING.read_text(encoding="utf-8"))
    validate_mapping_ledger(mapping)
    book = get_book(args.book)
    if book.testament != "nt":
        raise ValueError("MACULA Greek candidates are NT only")
    candidate = project_chapter_candidate(book, args.chapter, mapping)
    adjudications = json.loads(ADJUDICATIONS.read_text(encoding="utf-8"))
    candidate = apply_tr_authority_adaptations(candidate, mapping, adjudications)
    candidate = apply_structure_adjudications(candidate, adjudications)
    candidate = apply_tr_authority_fallbacks(candidate, mapping)
    candidate["provenance"]["structureAdjudications"] = {
        "path": str(ADJUDICATIONS.relative_to(ROOT)),
        "scope": "chapter",
        "sha256": chapter_adjudication_sha256(
            adjudications, book.slug, args.chapter
        ),
    }
    output = ROOT / "nt-syntax" / "candidates" / f"{book.utr_stem}.{args.chapter}.macula.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(candidate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"candidate {output.relative_to(ROOT)}: "
        f"{candidate['summary']['exactGroups']} exact groups; "
        f"{candidate['summary']['humanAdjudicatedGroups']} human-adjudicated groups; "
        f"{candidate['summary'].get('trAuthorityAdaptedGroups', 0)} TR-authority adapted groups; "
        f"{candidate['summary']['holdGroups']} HOLD groups; "
        f"{candidate['summary']['mappedWords']} mapped words; "
        f"{candidate['summary'].get('trAuthorityAdaptedWords', 0)} adapted TR words; "
        f"{candidate['summary']['humanAdjudicatedWords']} human-adjudicated TR words"
        f"; {candidate['summary'].get('trAuthorityFallbackVerses', 0)} TR fallback verses"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
