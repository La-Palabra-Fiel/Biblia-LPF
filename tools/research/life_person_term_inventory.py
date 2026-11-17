#!/usr/bin/env python3
"""Inventory biblical source families relevant to inherited Spanish 'alma'."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PIPELINE = ROOT / "tools/pipeline"
sys.path.insert(0, str(PIPELINE))
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
    "G5590": {"strong": 5590, "label": "ψυχή", "role": "core-family"},
    "G4151": {"strong": 4151, "label": "πνεῦμα", "role": "contrast-family"},
    "G2222": {"strong": 2222, "label": "ζωή", "role": "contrast-family"},
}

OT_FAMILIES = {
    "H5315": {"index": "5315", "label": "נֶפֶשׁ", "role": "core-family"},
    "H5397": {"index": "5397", "label": "נְשָׁמָה", "role": "contrast-family"},
    "H7307": {"index": "7307", "label": "רוּחַ", "role": "contrast-family"},
}


def nt_occurrences(strong: int) -> list[dict]:
    rows = []
    for book in NT:
        for reference, tokens in load_robinson_book(book).items():
            for token in tokens:
                if strong not in token.strongs:
                    continue
                rows.append({
                    "reference": reference,
                    "ordinal": token.ordinal,
                    "surfaceBeta": token.surface_beta,
                    "surface": beta_to_unicode(token.surface_beta),
                    "morphology": token.raw_tag,
                    "strong": f"G{strong}",
                })
    return rows


def ot_occurrences(index_key: str) -> list[dict]:
    return protestant_ot_occurrences(index_key)


def build() -> dict:
    families = {}
    for key, definition in NT_FAMILIES.items():
        occurrences = nt_occurrences(definition["strong"])
        families[key] = {
            "sourceLabel": definition["label"],
            "researchRole": definition["role"],
            "occurrenceCount": len(occurrences),
            "occurrences": occurrences,
        }
    for key, definition in OT_FAMILIES.items():
        occurrences = ot_occurrences(definition["index"])
        families[key] = {
            "sourceLabel": definition["label"],
            "researchRole": definition["role"],
            "occurrenceCount": len(occurrences),
            "occurrences": occurrences,
        }
    return {
        "schema": "lpf-biblical-life-person-term-inventory-v1",
        "question": "Source families relevant to Spanish alma, life, person, breath, and spirit",
        "semanticJudgment": "none-source-inventory-only",
        "scopeNote": "H5315 and G5590 are the core inquiry; adjacent families are controls and are not presumed synonyms.",
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
        default=ROOT / "notes/research/inventories/life-person-terms.json",
    )
    args = parser.parse_args()
    inventory = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(
        {key: value["occurrenceCount"] for key, value in inventory["families"].items()},
        ensure_ascii=False,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
