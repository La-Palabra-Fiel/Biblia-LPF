"""Shared Protestant-reference extraction for canonical OT term inventories."""

from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from functools import lru_cache
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PIPELINE = ROOT / "tools/pipeline"
sys.path.insert(0, str(PIPELINE))

from books import OT  # noqa: E402
from ot_evidence import _corpus_index  # noqa: E402
from source_packet import local_name, protestant_segments  # noqa: E402


@lru_cache(maxsize=1)
def _protestant_reference_by_oshb_id() -> dict[str, str]:
    """Map each canonical OSHB word id to its Protestant verse label."""
    out: dict[str, str] = {}
    for book in OT:
        tree = ET.parse(book.xml_path)
        for verse in tree.getroot().iter():
            if local_name(verse.tag) != "verse":
                continue
            osis_id = str(verse.get("osisID") or "")
            match = re.fullmatch(
                rf"{re.escape(book.osis)}\.(\d+)\.(\d+)", osis_id
            )
            if not match:
                continue
            source_chapter, source_verse = int(match.group(1)), int(match.group(2))
            for chapter, verse_number, words in protestant_segments(
                verse, book.osis, source_chapter, source_verse
            ):
                reference = f"{book.osis}.{chapter}.{verse_number}"
                for word in words:
                    oshb_id = word.get("id")
                    if not oshb_id:
                        raise ValueError(f"OSHB word lacks id at {osis_id}")
                    prior = out.setdefault(oshb_id, reference)
                    if prior != reference:
                        raise ValueError(
                            f"OSHB word {oshb_id} mapped to both {prior} and {reference}"
                        )
    return out


def protestant_ot_occurrences(index_key: str) -> list[dict]:
    references = _protestant_reference_by_oshb_id()
    rows = []
    for row in _corpus_index().get(index_key, []):
        oshb_id = row["oshbId"]
        reference = references.get(oshb_id)
        if not reference:
            raise ValueError(f"no Protestant reference for OSHB word {oshb_id}")
        rows.append({
            "reference": reference,
            "position": row["mtPosition"],
            "surface": row["surface"],
            "lemma": row["lemma"],
            "morphology": row["morph"],
            "oshbId": oshb_id,
            "context": row["context"],
            "previousLemma": row["previousLemma"],
            "nextLemma": row["nextLemma"],
        })
    return rows
