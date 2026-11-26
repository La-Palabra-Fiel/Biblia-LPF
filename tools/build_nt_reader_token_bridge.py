#!/usr/bin/env python3
"""Build the pinned Scrivener/TR -> Reader SBLGNT token bridge.

Canonical NT reverse links cite the SCV-authoritative TR token ordinal.  The
Reader's structural spine uses MorphGNT/SBLGNT ordinals.  Equal ordinals are
not token identity: readings can be reordered, inserted, or omitted.  This
bridge records exact normalized Greek-surface correspondences that are forced
by order or unique within the remaining verse.  One-to-many gaps remain empty
unless a named-human decision in the committed adjudication ledger binds the
TR token to the pinned Reader terminals and their checked surfaces.
"""

from __future__ import annotations

import json
import re
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
ADJUDICATIONS = (
    ROOT / "source" / "greek" / "TR1894" / "READER_TOKEN_BRIDGE_ADJUDICATIONS.json"
)
SBLGNT_ROOT = ROOT / "source" / "greek" / "macula-greek" / "SBLGNT" / "lowfat"
BRIDGE_SCHEMA = "lpf-tr-to-reader-token-bridge-v2"
ADJUDICATION_SCHEMA = "lpf-tr-to-reader-token-bridge-adjudications-v1"
TR_TOKEN_ID = re.compile(r"^([A-Z0-9]+)\.(\d+)\.(\d+)\.w(\d{3})$")
READER_TOKEN_ID = re.compile(r"^n(\d{2})(\d{3})(\d{3})(\d{3})$")


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


def load_reviewed_mappings() -> tuple[dict[tuple[str, int, int], list[dict]], dict]:
    """Load named-human one-to-many decisions without treating them as text identity."""
    data = json.loads(ADJUDICATIONS.read_text(encoding="utf-8"))
    if data.get("schema") != ADJUDICATION_SCHEMA:
        raise ValueError(f"unsupported Reader bridge adjudication schema: {data.get('schema')!r}")
    decisions = data.get("decisions")
    if not isinstance(decisions, list):
        raise ValueError("Reader bridge adjudications must contain a decisions list")

    books = {book.slug: book for book in NT}
    grouped: dict[tuple[str, int, int], list[dict]] = defaultdict(list)
    decision_ids: set[str] = set()
    mapping_keys: set[tuple[str, int, int, int]] = set()
    for index, decision in enumerate(decisions):
        label = f"Reader bridge adjudication decisions[{index}]"
        if not isinstance(decision, dict):
            raise ValueError(f"{label} must be an object")
        decision_id = str(decision.get("decisionId") or "")
        if not decision_id or decision_id in decision_ids:
            raise ValueError(f"{label} has a missing or duplicate decisionId")
        decision_ids.add(decision_id)

        book = books.get(str(decision.get("book") or ""))
        if book is None:
            raise ValueError(f"{decision_id}: unknown book")
        tr_match = TR_TOKEN_ID.fullmatch(str(decision.get("trTokenId") or ""))
        if not tr_match:
            raise ValueError(f"{decision_id}: invalid trTokenId")
        code, chapter_text, verse_text, ordinal_text = tr_match.groups()
        chapter, verse, tr_ordinal = int(chapter_text), int(verse_text), int(ordinal_text)
        source_code = TR_CODE_BY_STEM[book.utr_stem]
        reference = f"{source_code}.{chapter}.{verse}"
        if code != source_code or decision.get("reference") != reference:
            raise ValueError(f"{decision_id}: reference does not match its book and TR token")

        reader_ids = decision.get("readerTokenIds")
        reader_surfaces = decision.get("readerSurfaces")
        if not isinstance(reader_ids, list) or len(reader_ids) < 2:
            raise ValueError(
                f"{decision_id}: reviewed one-to-many mapping requires at least two Reader token ids"
            )
        if not isinstance(reader_surfaces, list) or len(reader_surfaces) != len(reader_ids):
            raise ValueError(f"{decision_id}: readerSurfaces must match readerTokenIds")
        reader_ordinals: list[int] = []
        for reader_id in reader_ids:
            reader_match = READER_TOKEN_ID.fullmatch(str(reader_id))
            if not reader_match:
                raise ValueError(f"{decision_id}: invalid Reader token id {reader_id!r}")
            book_code, reader_chapter, reader_verse, reader_ordinal = (
                int(value) for value in reader_match.groups()
            )
            if (book_code, reader_chapter, reader_verse) != (book.book_code, chapter, verse):
                raise ValueError(f"{decision_id}: Reader token is outside the adjudicated verse")
            reader_ordinals.append(reader_ordinal)
        if reader_ordinals != sorted(set(reader_ordinals)):
            raise ValueError(f"{decision_id}: Reader token ids must be unique and ordered")

        if not normalized_greek(str(decision.get("trSurface") or "")):
            raise ValueError(f"{decision_id}: trSurface is empty")
        if any(not normalized_greek(str(surface)) for surface in reader_surfaces):
            raise ValueError(f"{decision_id}: readerSurfaces contains an empty surface")
        if not str(decision.get("reviewer") or "").strip():
            raise ValueError(f"{decision_id}: reviewer is required")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(decision.get("date") or "")):
            raise ValueError(f"{decision_id}: date must be YYYY-MM-DD")
        if not str(decision.get("reason") or "").strip():
            raise ValueError(f"{decision_id}: reason is required")

        mapping_key = (book.slug, chapter, verse, tr_ordinal)
        if mapping_key in mapping_keys:
            raise ValueError(f"{decision_id}: duplicate reviewed mapping for the TR token")
        mapping_keys.add(mapping_key)
        grouped[(book.slug, chapter, verse)].append({
            **decision,
            "trOrdinal": tr_ordinal,
            "readerOrdinals": reader_ordinals,
        })
    return grouped, data


def reader_ordinals_in(mapping: list[int | list[int] | None]) -> set[int]:
    result: set[int] = set()
    for value in mapping:
        if isinstance(value, int):
            result.add(value)
        elif isinstance(value, list):
            result.update(value)
    return result


def main() -> int:
    verify_checkout()
    reviewed_mappings, adjudication_data = load_reviewed_mappings()
    books: dict[str, dict] = {}
    source_files: list[dict[str, str]] = []
    total_tr = total_mapped = total_verses = partial_verses = reviewed_count = 0
    used_decisions: set[str] = set()

    for book in NT:
        path, sblgnt = load_sblgnt_words(book)
        source_files.append({"path": str(path.relative_to(ROOT)), "sha256": sha256(path)})
        verse_maps: dict[str, list[int | list[int] | None]] = {}
        book_tr = book_mapped = book_partial = book_reviewed = 0
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
            mapping: list[int | list[int] | None] = [None] * len(tr_surfaces)
            for tr_index, reader_index in safe_pairs(tr_surfaces, reader_surfaces):
                mapping[tr_index] = reader_index + 1
            for decision in reviewed_mappings.get((book.slug, chapter, verse), []):
                decision_id = decision["decisionId"]
                tr_index = int(decision["trOrdinal"]) - 1
                if tr_index < 0 or tr_index >= len(tr_surfaces):
                    raise ValueError(f"{decision_id}: TR token ordinal is outside the verse")
                if mapping[tr_index] is not None:
                    raise ValueError(f"{decision_id}: reviewed mapping would override an exact mapping")
                if reconciled["trTokens"][tr_index]["tokenId"] != decision["trTokenId"]:
                    raise ValueError(f"{decision_id}: trTokenId does not match the reconciled source")
                if normalized_greek(str(decision["trSurface"])) != tr_surfaces[tr_index]:
                    raise ValueError(f"{decision_id}: trSurface does not match the reconciled source")

                reader_ordinals = [int(value) for value in decision["readerOrdinals"]]
                if any(value < 1 or value > len(reader_surfaces) for value in reader_ordinals):
                    raise ValueError(f"{decision_id}: Reader token ordinal is outside the verse")
                actual_surfaces = [reader_surfaces[value - 1] for value in reader_ordinals]
                expected_surfaces = [
                    normalized_greek(str(value)) for value in decision["readerSurfaces"]
                ]
                if actual_surfaces != expected_surfaces:
                    raise ValueError(f"{decision_id}: readerSurfaces do not match the pinned Reader source")
                overlap = reader_ordinals_in(mapping).intersection(reader_ordinals)
                if overlap:
                    raise ValueError(f"{decision_id}: Reader token ids already belong to an exact mapping")

                mapping[tr_index] = reader_ordinals
                used_decisions.add(decision_id)
                book_reviewed += 1
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
            "reviewedMappingCount": book_reviewed,
            "verses": verse_maps,
        }
        total_tr += book_tr
        total_mapped += book_mapped
        total_verses += len(verse_maps)
        partial_verses += book_partial
        reviewed_count += book_reviewed

    declared_decisions = {
        str(decision.get("decisionId")) for decision in adjudication_data.get("decisions") or []
    }
    if used_decisions != declared_decisions:
        missing = sorted(declared_decisions - used_decisions)
        raise ValueError(f"unused Reader bridge adjudications: {missing}")

    document = {
        "schema": BRIDGE_SCHEMA,
        "sourceTokenBasis": "Scrivener TR1894, SCV-authoritative token order",
        "readerTokenBasis": "SBLGNT token order used by MorphGNT",
        "mappingPolicy": "exact-normalized-greek-forced-or-unique-plus-reviewed-one-to-many-v2",
        "referenceDataset": "Clear-Bible/macula-greek SBLGNT lowfat",
        "referenceRevision": MACULA_COMMIT,
        "license": MACULA_LICENSE,
        "attribution": MACULA_ATTRIBUTION,
        "sourceFiles": source_files,
        "adjudications": {
            "schema": ADJUDICATION_SCHEMA,
            "file": str(ADJUDICATIONS.relative_to(ROOT)),
            "sha256": sha256(ADJUDICATIONS),
            "decisionCount": len(declared_decisions),
        },
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
            "reviewedMappingCount": reviewed_count,
        },
        "books": books,
    }
    OUT.write_text(json.dumps(document, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(
        f"Reader token bridge: {total_mapped}/{total_tr} safe mappings; "
        f"{reviewed_count} reviewed one-to-many mappings; "
        f"{partial_verses}/{total_verses} verses retain one or more explicit gaps"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
