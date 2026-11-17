#!/usr/bin/env python3
"""Inventory biblical source families relevant to Spanish bautizar/bautismo."""

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
from nt_source import ROBINSON_COMMIT, SCRIVENER_COMMIT, beta_to_unicode, load_robinson_book  # noqa: E402
from canonical_ot_inventory import protestant_ot_occurrences  # noqa: E402


NT_FAMILIES = {
    "G907": {"strong": 907, "label": "βαπτίζω", "role": "central-family"},
    "G908": {"strong": 908, "label": "βάπτισμα", "role": "central-family"},
    "G909": {"strong": 909, "label": "βαπτισμός", "role": "central-family"},
    "G910": {"strong": 910, "label": "βαπτιστής", "role": "title-family"},
    "G911": {"strong": 911, "label": "βάπτω", "role": "contrast-family"},
    "G3067": {"strong": 3067, "label": "λουτρόν", "role": "contrast-family"},
    "G2512": {"strong": 2512, "label": "καθαρισμός", "role": "contrast-family"},
}

OT_FAMILIES = {
    "H2881": {"index": "2881", "label": "טָבַל", "role": "background-family"},
    "H7364": {"index": "7364", "label": "רָחַץ", "role": "contrast-family"},
    "H3526": {"index": "3526", "label": "כָּבַס", "role": "contrast-family"},
}


def nt_occurrences(strong: int) -> list[dict]:
    rows = []
    for book in NT:
        for reference, tokens in load_robinson_book(book).items():
            for token in tokens:
                if strong not in token.strongs:
                    continue
                rows.append({
                    "reference": reference, "ordinal": token.ordinal,
                    "surfaceBeta": token.surface_beta,
                    "surface": beta_to_unicode(token.surface_beta),
                    "morphology": token.raw_tag, "strong": f"G{strong}",
                })
    return rows


def build() -> dict:
    families = {}
    for key, definition in NT_FAMILIES.items():
        occurrences = nt_occurrences(definition["strong"])
        families[key] = {
            "sourceLabel": definition["label"], "researchRole": definition["role"],
            "occurrenceCount": len(occurrences), "occurrences": occurrences,
        }
    for key, definition in OT_FAMILIES.items():
        occurrences = protestant_ot_occurrences(definition["index"])
        families[key] = {
            "sourceLabel": definition["label"], "researchRole": definition["role"],
            "occurrenceCount": len(occurrences), "occurrences": occurrences,
        }
    return {
        "schema": "lpf-biblical-baptism-term-inventory-v1",
        "question": "Source families relevant to Spanish bautizar, bautismo, sumergir, lavar, and purificar",
        "semanticJudgment": "none-source-inventory-only",
        "scopeNote": "Baptizo, baptisma, baptismos, and Baptistes remain distinct from dip, wash, bathe, and purification controls.",
        "sources": {
            "ntSurface": "Scrivener TR1894", "ntSurfaceCommit": SCRIVENER_COMMIT,
            "ntMorphology": "Robinson UTR", "ntMorphologyCommit": ROBINSON_COMMIT,
            "otSurfaceAndMorphology": "WLC in OSHB",
        },
        "families": families,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "notes/research/inventories/baptism-terms.json")
    args = parser.parse_args()
    payload = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v["occurrenceCount"] for k, v in payload["families"].items()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
