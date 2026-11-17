#!/usr/bin/env python3
"""Inventory biblical source terms relevant to Spanish pacto/testamento."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/pipeline"))
sys.path.insert(0, str(ROOT / "tools/research"))

from books import NT  # noqa: E402
from nt_source import (  # noqa: E402
    ROBINSON_COMMIT,
    SCRIVENER_COMMIT,
    beta_to_unicode,
    load_robinson_book,
)
from canonical_ot_inventory import protestant_ot_occurrences  # noqa: E402


NT_FAMILIES = {
    "G1242": {"strong": 1242, "label": "διαθήκη"},
    "G1303": {"strong": 1303, "label": "διατίθεμαι"},
}


def nt_occurrences(strong: int) -> list[dict]:
    rows = []
    for book in NT:
        for reference, tokens in load_robinson_book(book).items():
            for token in tokens:
                if strong in token.strongs:
                    rows.append({
                        "reference": reference,
                        "ordinal": token.ordinal,
                        "surfaceBeta": token.surface_beta,
                        "surface": beta_to_unicode(token.surface_beta),
                        "morphology": token.raw_tag,
                        "strong": f"G{strong}",
                    })
    return rows


def berit_occurrences() -> list[dict]:
    return protestant_ot_occurrences("1285")


def build() -> dict:
    families = {}
    for key, definition in NT_FAMILIES.items():
        occurrences = nt_occurrences(definition["strong"])
        families[key] = {
            "sourceLabel": definition["label"],
            "occurrenceCount": len(occurrences),
            "occurrences": occurrences,
        }
    berit = berit_occurrences()
    families["H1285"] = {
        "sourceLabel": "בְּרִית",
        "occurrenceCount": len(berit),
        "immediatelyAdjacentToH3772Count": sum(
            row["previousLemma"] == "3772" or row["nextLemma"] == "3772"
            for row in berit
        ),
        "occurrences": berit,
    }
    return {
        "schema": "lpf-biblical-covenant-term-inventory-v1",
        "question": "Source terms relevant to inherited Spanish pacto/testamento",
        "semanticJudgment": "none-source-inventory-only",
        "sources": {
            "ntSurface": "Scrivener TR1894",
            "ntSurfaceCommit": SCRIVENER_COMMIT,
            "ntMorphology": "Robinson UTR",
            "ntMorphologyCommit": ROBINSON_COMMIT,
            "otSurfaceAndMorphology": "WLC in OSHB",
        },
        "families": families,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "notes/research/inventories/covenant-terms.json",
    )
    args = parser.parse_args()
    inventory = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(
        {key: value["occurrenceCount"] for key, value in inventory["families"].items()},
        ensure_ascii=False,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

