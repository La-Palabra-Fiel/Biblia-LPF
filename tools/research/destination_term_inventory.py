#!/usr/bin/env python3
"""Inventory biblical source terms often collapsed into Spanish 'infierno'."""

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
    "G86": {"strong": 86, "label": "ᾅδης"},
    "G1067": {"strong": 1067, "label": "γέεννα"},
    "G5020": {"strong": 5020, "label": "ταρταρόω"},
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


def sheol_occurrences() -> list[dict]:
    return protestant_ot_occurrences("7585")


def build() -> dict:
    families = {}
    for key, definition in NT_FAMILIES.items():
        occurrences = nt_occurrences(definition["strong"])
        families[key] = {
            "sourceLabel": definition["label"],
            "occurrenceCount": len(occurrences),
            "occurrences": occurrences,
        }
    sheol = sheol_occurrences()
    families["H7585"] = {
        "sourceLabel": "שְׁאוֹל",
        "occurrenceCount": len(sheol),
        "occurrences": sheol,
    }
    return {
        "schema": "lpf-biblical-destination-term-inventory-v1",
        "question": "Source terms historically collapsed into Spanish infierno",
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
        default=ROOT / "notes/research/inventories/destination-terms.json",
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

