#!/usr/bin/env python3
"""Inventory biblical source families relevant to Spanish 'iglesia'."""

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
    "G1577": {"strong": 1577, "label": "ἐκκλησία", "role": "central-family"},
    "G4864": {"strong": 4864, "label": "συναγωγή", "role": "contrast-family"},
    "G4892": {"strong": 4892, "label": "συνέδριον", "role": "contrast-family"},
    "G3831": {"strong": 3831, "label": "πανήγυρις", "role": "contrast-family"},
}

OT_FAMILIES = {
    "H6951": {"index": "6951", "label": "קָהָל", "role": "background-family"},
    "H5712": {"index": "5712", "label": "עֵדָה", "role": "contrast-family"},
    "H4150": {"index": "4150", "label": "מוֹעֵד", "role": "contrast-family"},
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
        occurrences = protestant_ot_occurrences(definition["index"])
        families[key] = {
            "sourceLabel": definition["label"],
            "researchRole": definition["role"],
            "occurrenceCount": len(occurrences),
            "occurrences": occurrences,
        }
    return {
        "schema": "lpf-biblical-church-term-inventory-v1",
        "question": "Source families relevant to Spanish iglesia, asamblea, congregación, sinagoga, and consejo",
        "semanticJudgment": "none-source-inventory-only",
        "scopeNote": "Ekklesia is inventoried with distinct assembly and council families; Hebrew qahal supplies canonical background but is not presumed to be lexically identical.",
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
        "--output", type=Path,
        default=ROOT / "notes/research/inventories/church-terms.json",
    )
    args = parser.parse_args()
    inventory = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v["occurrenceCount"] for k, v in inventory["families"].items()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
