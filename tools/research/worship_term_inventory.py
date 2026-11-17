#!/usr/bin/env python3
"""Inventory biblical source families relevant to Spanish 'adorar/adoración'."""

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
    "G4352": {"strong": 4352, "label": "προσκυνέω", "role": "central-family"},
    "G3000": {"strong": 3000, "label": "λατρεύω", "role": "central-family"},
    "G4576": {"strong": 4576, "label": "σέβομαι", "role": "central-family"},
    "G2151": {"strong": 2151, "label": "εὐσεβέω", "role": "contrast-family"},
    "G2356": {"strong": 2356, "label": "θρησκεία", "role": "contrast-family"},
    "G1479": {"strong": 1479, "label": "ἐθελοθρησκεία", "role": "contrast-family"},
    "G1392": {"strong": 1392, "label": "δοξάζω", "role": "contrast-family"},
}

OT_FAMILIES = {
    "H7812": {"index": "7812", "label": "שָׁחָה", "role": "central-family"},
    "H5647": {"index": "5647", "label": "עָבַד", "role": "central-family"},
    "H5456": {"index": "5456", "label": "סְגִד", "role": "central-family"},
    "H6915": {"index": "6915", "label": "קָדַד", "role": "contrast-family"},
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
        "schema": "lpf-biblical-worship-term-inventory-v1",
        "question": "Source families relevant to Spanish adorar, postrarse, servir, rendir culto, and reverenciar",
        "semanticJudgment": "none-source-inventory-only",
        "scopeNote": "Bowing, service, reverence, religious practice, and glorifying are inventoried separately; overlap in Spanish does not make the source families synonyms.",
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
        default=ROOT / "notes/research/inventories/worship-terms.json",
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
