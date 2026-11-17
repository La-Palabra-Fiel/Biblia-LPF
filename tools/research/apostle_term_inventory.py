#!/usr/bin/env python3
"""Inventory biblical source families relevant to Spanish apóstol/enviado."""

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
    "G652": {"strong": 652, "label": "ἀπόστολος", "role": "central-noun"},
    "G649": {"strong": 649, "label": "ἀποστέλλω", "role": "cognate-sending-verb"},
    "G3992": {"strong": 3992, "label": "πέμπω", "role": "contrast-sending-verb"},
    "G32": {"strong": 32, "label": "ἄγγελος", "role": "contrast-messenger-noun"},
}

OT_FAMILIES = {
    "H7971": {"index": "7971", "label": "שָׁלַח", "role": "sending-background"},
    "H4397": {"index": "4397", "label": "מַלְאָךְ", "role": "messenger-background"},
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
        "schema": "lpf-biblical-apostle-term-inventory-v1",
        "question": "Source families relevant to Spanish apóstol, enviado, emisario, and mensajero",
        "semanticJudgment": "none-source-inventory-only",
        "scopeNote": "Apostolos remains distinct from its cognate sending verb, another common sending verb, and angelos/malak messenger families.",
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
        default=ROOT / "notes/research/inventories/apostle-terms.json",
    )
    args = parser.parse_args()
    payload = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(
        {key: value["occurrenceCount"] for key, value in payload["families"].items()},
        ensure_ascii=False,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
