#!/usr/bin/env python3
"""Inventory biblical source families relevant to inherited Spanish 'salvación'."""

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
    "G4982": {"strong": 4982, "label": "σῴζω", "role": "core-family"},
    "G4991": {"strong": 4991, "label": "σωτηρία", "role": "core-family"},
    "G4992": {"strong": 4992, "label": "σωτήριον", "role": "core-family"},
    "G4990": {"strong": 4990, "label": "σωτήρ", "role": "core-family"},
    "G1295": {"strong": 1295, "label": "διασῴζω", "role": "contrast-family"},
    "G4506": {"strong": 4506, "label": "ῥύομαι", "role": "contrast-family"},
    "G1807": {"strong": 1807, "label": "ἐξαιρέω", "role": "contrast-family"},
    "G3084": {"strong": 3084, "label": "λυτρόω", "role": "contrast-family"},
}

OT_FAMILIES = {
    "H3444": {"index": "3444", "label": "יְשׁוּעָה", "role": "core-family"},
    "H3467": {"index": "3467", "label": "יָשַׁע", "role": "core-family"},
    "H3468": {"index": "3468", "label": "יֶשַׁע", "role": "core-family"},
    "H8668": {"index": "8668", "label": "תְּשׁוּעָה", "role": "core-family"},
    "H4422": {"index": "4422", "label": "מָלַט", "role": "contrast-family"},
    "H6403": {"index": "6403", "label": "פָּלַט", "role": "contrast-family"},
    "H5337": {"index": "5337", "label": "נָצַל", "role": "contrast-family"},
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
        "schema": "lpf-biblical-salvation-term-inventory-v1",
        "question": "Source families relevant to Spanish salvación, rescate, liberación, preservación, and sanidad",
        "semanticJudgment": "none-source-inventory-only",
        "scopeNote": "The y-sh-ʿ and sōzō/sōtēria families are central; adjacent rescue, escape, and redemption families are controls and are not presumed synonyms.",
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
        default=ROOT / "notes/research/inventories/salvation-terms.json",
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
