"""Stable source-to-consumer book identities for LPF publication.

The editable source identifier is allowed to differ from the established
consumer identifier, but that difference must be declared here.  Export and
publish import the same resolver so they cannot disagree about filenames or
metadata.
"""

from __future__ import annotations

import json
from pathlib import Path


MAPPING_PATH = Path(__file__).with_name("consumer_books.json")


def _load_mapping() -> dict[str, str]:
    raw = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not all(
        isinstance(source, str) and source
        and isinstance(consumer, str) and consumer
        for source, consumer in raw.items()
    ):
        raise RuntimeError(f"invalid consumer book mapping: {MAPPING_PATH}")
    if len(set(raw.values())) != len(raw):
        raise RuntimeError(f"consumer book IDs must be unique: {MAPPING_PATH}")
    return raw


SOURCE_TO_CONSUMER_BOOK_ID = _load_mapping()


def consumer_book_id(source_book: str) -> str:
    """Return the stable cgv-data/Reader identifier for a source book."""
    return SOURCE_TO_CONSUMER_BOOK_ID.get(source_book, source_book)
