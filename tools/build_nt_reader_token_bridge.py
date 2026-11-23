#!/usr/bin/env python3
"""Build the pinned Scrivener/TR -> Reader SBLGNT token bridge.

Canonical NT reverse links cite the SCV-authoritative TR token ordinal.  The
Reader's structural spine uses MorphGNT/SBLGNT ordinals.  Equal ordinals are
not token identity: readings can be reordered, inserted, or omitted.  This
bridge records only exact normalized Greek-surface correspondences that are
forced by order or unique within the remaining verse.
"""

from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "pipeline"))

from books import NT  # noqa: E402
from nt_macula import (  # noqa: E402
    LOWFAT_FILENAMES,
    MACULA_ATTRIBUTION,
    MACULA_COMMIT,
    MACULA_LICENSE,
    TR_CODE_BY_STEM,
    normalized_greek,
    parse_macula_reference,
    scv_beta_key,
    sha256,
    stable_lcs_pairs,
    verify_checkout,
)
from nt_source import load_reconciled_verse, load_robinson_book  # noqa: E402

OUT = ROOT / "source" / "greek" / "TR1894" / "reader-token-bridge.json"
SBLGNT_ROOT = ROOT / "source" / "greek" / "macula-greek" / "SBLGNT" / "lowfat"


def load_sblgnt_words(book) -> tuple[Path, dict[str, list[str]]]:
    path = SBLGNT_ROOT / LOWFAT_FILENAMES[book.utr_stem]
    expected_code = TR_CODE_BY_STEM[book.utr_stem]
    rows: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for _, element in ET.iterparse(path, events=("end",)):
        if element.tag.rsplit("}", 1)[-1] != "w":
            continue
        code, chapter, verse, ordinal = parse_macula_reference(element.get("ref") or "")
        if code != expected_code:
            raise ValueError(f"{path.name}: unexpected book code {code}")
        surface = normalized_greek("".join(element.itertext()).strip())
        if not surface:
            raise ValueError(f"{code}.{chapter}.{verse}!{ordinal}: empty SBLGNT terminal")
        rows[f"{code}.{chapter}.{verse}"].append((ordinal, surface))
        element.clear()

    words: dict[str, list[str]] = {}
    for reference, terminals in rows.items():
        terminals.sort()
        if [ordinal for ordinal, _ in terminals] != list(range(1, len(terminals) + 1)):
            raise ValueError(f"{reference}: nonconsecutive SBLGNT terminal ordinals")
        words[reference] = [surface for _, surface in terminals]
    return path, words


def safe_pairs(left: list[str], right: list[str]) -> list[tuple[int, int]]:
    """Map exact surfaces without guessing repeated or textually different words."""
    pairs = set(stable_lcs_pairs(left, right))
    unmatched_left = set(range(len(left))) - {i for i, _ in pairs}
    unmatched_right = set(range(len(right))) - {j for _, j in pairs}
    left_by_surface: dict[str, list[int]] = defaultdict(list)
    right_by_surface: dict[str, list[int]] = defaultdict(list)
    for index in unmatched_left:
        left_by_surface[left[index]].append(index)
    for index in unmatched_right:
        right_by_surface[right[index]].append(index)
    for surface, left_indexes in left_by_surface.items():
        right_indexes = right_by_surface.get(surface, [])
        if len(left_indexes) == 1 and len(right_indexes) == 1:
            pairs.add((left_indexes[0], right_indexes[0]))
    return sorted(pairs)


def main() -> int:
    verify_checkout()
    books: dict[str, dict] = {}
    source_files: list[dict[str, str]] = []
    total_tr = total_mapped = total_verses = partial_verses = 0

    for book in NT:
        path, sblgnt = load_sblgnt_words(book)
        source_files.append({"path": str(path.relative_to(ROOT)), "sha256": sha256(path)})
        verse_maps: dict[str, list[int | None]] = {}
        book_tr = book_mapped = book_partial = 0
        references = sorted(
            load_robinson_book(book),
            key=lambda reference: tuple(int(part) for part in reference.split(".")[1:]),
        )
        for reference in references:
            _, chapter_text, verse_text = reference.split(".")
            chapter, verse = int(chapter_text), int(verse_text)
            reconciled = load_reconciled_verse(book, chapter, verse)
            tr_surfaces = [scv_beta_key(token["surfaceBeta"]) for token in reconciled["trTokens"]]
            reader_surfaces = sblgnt.get(reference, [])
            mapping: list[int | None] = [None] * len(tr_surfaces)
            for tr_index, reader_index in safe_pairs(tr_surfaces, reader_surfaces):
                mapping[tr_index] = reader_index + 1
            verse_maps[f"{chapter}:{verse}"] = mapping
            mapped = sum(value is not None for value in mapping)
            book_tr += len(mapping)
            book_mapped += mapped
            if mapped != len(mapping):
                book_partial += 1

        books[book.slug] = {
            "bookCode": book.book_code,
            "trTokenCount": book_tr,
            "mappedTokenCount": book_mapped,
            "unmappedTokenCount": book_tr - book_mapped,
            "partialVerseCount": book_partial,
            "verses": verse_maps,
        }
        total_tr += book_tr
        total_mapped += book_mapped
        total_verses += len(verse_maps)
        partial_verses += book_partial

    document = {
        "schema": "lpf-tr-to-reader-token-bridge-v1",
        "sourceTokenBasis": "Scrivener TR1894, SCV-authoritative token order",
        "readerTokenBasis": "SBLGNT token order used by MorphGNT",
        "mappingPolicy": "exact-normalized-greek-forced-or-unique-v1",
        "referenceDataset": "Clear-Bible/macula-greek SBLGNT lowfat",
        "referenceRevision": MACULA_COMMIT,
        "license": MACULA_LICENSE,
        "attribution": MACULA_ATTRIBUTION,
        "sourceFiles": source_files,
        "generator": {
            "command": "python3 tools/build_nt_reader_token_bridge.py",
            "path": str(Path(__file__).resolve().relative_to(ROOT)),
            "sha256": sha256(Path(__file__).resolve()),
        },
        "summary": {
            "verses": total_verses,
            "trTokens": total_tr,
            "mappedTokens": total_mapped,
            "unmappedTokens": total_tr - total_mapped,
            "partialVerses": partial_verses,
        },
        "books": books,
    }
    OUT.write_text(json.dumps(document, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(
        f"Reader token bridge: {total_mapped}/{total_tr} exact safe mappings; "
        f"{partial_verses}/{total_verses} verses retain one or more explicit gaps"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
