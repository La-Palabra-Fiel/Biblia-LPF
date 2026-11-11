"""Deterministic TR1894 context and corpus evidence for NT packets."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from functools import lru_cache

from books import NT, ROOT, Book
from nt_macula import (
    TR_AUTHORITY_FALLBACK_RULE,
    lowfat_path,
    validate_candidate,
    validate_mapping_ledger,
)
from nt_source import BOOK_BY_TR_CODE, load_reconciled_verse, load_robinson_book

MAPPING = ROOT / "source/greek/TR1894/macula-structure-mapping.json"
CORPUS_LIMIT = 12


def source_token_id(book: Book, chapter: int, verse: int, ordinal: int) -> str:
    return f"n{book.book_code:02d}{chapter:03d}{verse:03d}{ordinal:03d}"


def _reference_parts(reference: str) -> tuple[str, int, int]:
    code, chapter, verse = reference.split(".")
    return code, int(chapter), int(verse)


@lru_cache(maxsize=1)
def _mapping() -> tuple[dict[str, str], dict[str, str]]:
    ledger = json.loads(MAPPING.read_text(encoding="utf-8"))
    validate_mapping_ledger(ledger)
    anchors: dict[str, str] = {}
    verse_status: dict[str, str] = {}
    for row in ledger["verses"]:
        verse_status[row["reference"]] = row["status"]
        for item in row.get("mapping") or []:
            anchors[item["trTokenId"]] = item["maculaTerminalId"]
    return anchors, verse_status


@lru_cache(maxsize=1)
def _ordered_references() -> tuple[str, ...]:
    references = []
    for book in NT:
        references.extend(load_robinson_book(book))
    return tuple(references)


def _verse_record(reference: str, role: str) -> dict:
    code, chapter, verse = _reference_parts(reference)
    book = BOOK_BY_TR_CODE[code]
    rows = load_reconciled_verse(book, chapter, verse)["trTokens"]
    return {
        "role": role,
        "reference": reference,
        "surface": " ".join(row["surfaceGreek"] for row in rows),
        "tokens": [
            {
                "sourceTokenId": source_token_id(book, chapter, verse, row["ordinal"]),
                "surface": row["surfaceGreek"],
                "morph": row["morphology"]["rawTag"],
            }
            for row in rows
        ],
    }


@lru_cache(maxsize=None)
def _structural_paths(book: Book) -> dict[str, tuple[dict, ...]]:
    """Return allowlisted MACULA ancestor relations for exact terminal anchors."""
    paths: dict[str, tuple[dict, ...]] = {}

    def walk(element: ET.Element, ancestors: tuple[dict, ...]) -> None:
        name = element.tag.rsplit("}", 1)[-1]
        current = ancestors
        if name == "wg":
            descriptor = {
                key: value
                for source, key in (
                    ("class", "category"),
                    ("rule", "rule"),
                    ("role", "function"),
                    ("type", "clauseType"),
                    ("predication", "clauseType"),
                    ("head", "head"),
                )
                if (value := element.get(source))
            }
            current = ancestors + ((descriptor,) if descriptor else ())
        elif name == "w":
            terminal_id = element.get("{http://www.w3.org/XML/1998/namespace}id")
            if terminal_id:
                paths[terminal_id] = current
            return
        for child in list(element):
            walk(child, current)

    walk(ET.parse(lowfat_path(book)).getroot(), ())
    return paths


def original_language_context(book: Book, chapter: int, verse: int) -> list[dict]:
    reference = next(
        ref for ref in load_robinson_book(book)
        if _reference_parts(ref)[1:] == (chapter, verse)
    )
    book_refs = list(load_robinson_book(book))
    index = book_refs.index(reference)
    selected = []
    if index:
        selected.append((book_refs[index - 1], "previous"))
    selected.append((reference, "current"))
    if index + 1 < len(book_refs):
        selected.append((book_refs[index + 1], "next"))
    return [_verse_record(ref, role) for ref, role in selected]


@lru_cache(maxsize=1)
def _corpus_index() -> dict[int, tuple[dict, ...]]:
    anchors, verse_status = _mapping()
    index: dict[int, list[dict]] = {}
    for book in NT:
        structural_paths = _structural_paths(book)
        for reference in load_robinson_book(book):
            _, chapter, verse = _reference_parts(reference)
            for row in load_reconciled_verse(book, chapter, verse)["trTokens"]:
                for strong in row["morphology"]["strongs"]:
                    terminal_id = anchors.get(row["tokenId"])
                    index.setdefault(strong, []).append({
                        "reference": reference,
                        "trTokenId": row["tokenId"],
                        "sourceTokenId": source_token_id(book, chapter, verse, row["ordinal"]),
                        "surface": row["surfaceGreek"],
                        "surfaceBeta": row["surfaceBeta"],
                        "morph": row["morphology"]["rawTag"],
                        "maculaTerminalId": terminal_id,
                        "structureStatus": "triple-agreement-anchor" if terminal_id else "hold-no-exact-anchor",
                        "structuralPath": list(structural_paths.get(terminal_id, ())) if terminal_id else [],
                        "verseMappingStatus": verse_status.get(reference),
                    })
    return {strong: tuple(rows) for strong, rows in index.items()}


def corpus_usage(strong: int, current_reference: str) -> list[dict]:
    rows = [row for row in _corpus_index().get(int(strong), ()) if row.get("structuralPath")]
    rows.sort(key=lambda row: (row["reference"] != current_reference, row["reference"], row["trTokenId"]))
    return [dict(row) for row in rows[:CORPUS_LIMIT]]


def syntax_for_verse(book: Book, chapter: int, verse: int, expected_token_ids: list[str]) -> dict:
    """Project the stored comparison plus its explicit TR-native fallback."""
    path = ROOT / "nt-syntax" / "candidates" / f"{book.utr_stem}.{chapter}.macula.json"
    reference = f"{next(code for code, item in BOOK_BY_TR_CODE.items() if item == book)}.{chapter}.{verse}"
    if not path.is_file():
        return {"status": "HOLD_NO_CHAPTER_CANDIDATE", "reference": reference, "roots": [], "missingTrTokenIds": expected_token_ids}
    candidate = json.loads(path.read_text(encoding="utf-8"))
    validate_candidate(candidate)
    ledger = json.loads(MAPPING.read_text(encoding="utf-8"))
    row = next(item for item in ledger["verses"] if item["reference"] == reference)
    fallback = next(
        (
            item for item in candidate.get("trAuthorityFallbacks") or []
            if item.get("reference") == reference
        ),
        None,
    )
    fallback_tokens = set((fallback or {}).get("trTokenIds") or [])
    retired_terminals = set((fallback or {}).get("removedMaculaTerminalIds") or [])
    terminal_reference = {
        terminal_id: item["reference"]
        for item in ledger["verses"]
        for terminal_id in (
            [mapping["maculaTerminalId"] for mapping in item.get("mapping") or []]
            + list(item.get("unmatchedMaculaTerminalIds") or [])
        )
    }
    seen: list[str] = []
    holds: list[str] = []

    def prune(node: dict) -> dict | None:
        kind = node.get("kind")
        if kind in {"word", "tr-word"}:
            token_id = node.get("trTokenId")
            if not token_id or not token_id.startswith(reference + "."):
                return None
            seen.append(token_id)
            return {
                key: node[key]
                for key in (
                    "kind", "status", "trTokenId", "maculaTerminalId",
                    "decisionId", "adaptationRuleId",
                )
                if key in node
            }
        if kind == "reference-word":
            terminal_id = node.get("maculaTerminalId")
            if terminal_reference.get(terminal_id) != reference:
                return None
            if terminal_id in retired_terminals:
                return None
            holds.append(terminal_id)
            return {"kind": kind, "status": node["status"], "maculaTerminalId": terminal_id}
        children = [projected for child in node.get("children") or [] if (projected := prune(child)) is not None]
        if not children:
            return None
        return {
            key: node[key]
            for key in (
                "candidateNodeId", "kind", "status", "category", "rule",
                "function", "clauseType", "decisionIds", "adaptationRuleIds",
            )
            if key in node
        } | {"children": children}

    roots = [projected for sentence in candidate["sentences"] for root in sentence["roots"] if (projected := prune(root)) is not None]
    ordered_fallback_tokens = [
        token_id for token_id in expected_token_ids if token_id in fallback_tokens
    ]
    if ordered_fallback_tokens:
        roots.append({
            "candidateNodeId": f"{reference}.tr-fallback",
            "kind": "group",
            "status": "tr-authority-adapted",
            "adaptationRuleIds": [TR_AUTHORITY_FALLBACK_RULE],
            "children": [
                {
                    "kind": "tr-word",
                    "status": "tr-authority-adapted",
                    "trTokenId": token_id,
                    "adaptationRuleId": TR_AUTHORITY_FALLBACK_RULE,
                }
                for token_id in ordered_fallback_tokens
            ],
        })
        seen.extend(ordered_fallback_tokens)
    token_paths: dict[str, list[dict]] = {}

    def collect_paths(node: dict, ancestors: list[dict]) -> None:
        if node.get("kind") in {"word", "tr-word"}:
            token_paths[node["trTokenId"]] = list(ancestors)
            return
        descriptor = {
            key: node[key]
            for key in ("candidateNodeId", "category", "rule", "function", "clauseType", "status")
            if key in node
        }
        next_ancestors = ancestors + ([descriptor] if descriptor else [])
        for child in node.get("children") or []:
            collect_paths(child, next_ancestors)

    for root in roots:
        collect_paths(root, [])
    missing = [token_id for token_id in expected_token_ids if token_id not in seen]
    duplicate = len(seen) != len(set(seen))
    status = "READY_TR_STRUCTURE" if not missing and not holds and not duplicate else "HOLD_STRUCTURE"
    return {
        "status": status,
        "reference": reference,
        "candidatePath": str(path.relative_to(ROOT)),
        "roots": roots,
        "missingTrTokenIds": missing,
        "unmatchedMaculaTerminalIds": holds,
        "duplicateTrToken": duplicate,
        "mappingStatus": row["status"],
        "trAuthorityFallback": fallback,
        "tokenStructuralPaths": token_paths,
    }
