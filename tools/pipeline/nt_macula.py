"""Closed-list MACULA Greek structural source and TR1894 mapping gate."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import subprocess
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from books import NT, ROOT, Book
from nt_source import (
    BOOK_BY_TR_CODE,
    TR_CODE_BY_STEM,
    beta_to_unicode,
    load_reconciled_verse,
    scv_beta_to_unicode,
)

MACULA_ROOT = ROOT / "source" / "greek" / "macula-greek"
MACULA_COMMIT = "8423afe47b9e8f24b7772e808af45c7159a6fe7e"
MACULA_LICENSE = "CC BY 4.0"
MACULA_ATTRIBUTION = (
    "MACULA Greek Linguistic Datasets, available at "
    "https://github.com/Clear-Bible/macula-greek/"
)
MAPPING_POLICY = "tr1894-robinson-macula-token-agreement-v2"
STRUCTURE_ADJUDICATION_SCHEMA = "tr1894-native-structure-adjudications-v1"
TR_AUTHORITY_ADAPTATION_RULE = "tr-authority-isolated-one-to-one-v1"
APPROVED_ROBINSON_BINDING_RULE = "tr-authority-approved-robinson-binding-v1"
MACULA_ONLY_PROMOTE_CHILD_RULE = "tr-authority-macula-only-promote-child-v1"
FLAT_PERMUTATION_RULE = "tr-authority-flat-permutation-v1"
TR_AUTHORITY_FALLBACK_RULE = "tr-authority-fallback-v1"
TR_AUTHORITY_ADAPTATION_RULES = {
    TR_AUTHORITY_ADAPTATION_RULE,
    APPROVED_ROBINSON_BINDING_RULE,
    MACULA_ONLY_PROMOTE_CHILD_RULE,
    FLAT_PERMUTATION_RULE,
    TR_AUTHORITY_FALLBACK_RULE,
}

LOWFAT_FILENAMES = {
    book.utr_stem: f"{index:02d}-{name}.xml"
    for index, (book, name) in enumerate(zip(NT, (
        "matthew", "mark", "luke", "john", "acts", "romans",
        "1corinthians", "2corinthians", "galatians", "ephesians",
        "philippians", "colossians", "1thessalonians", "2thessalonians",
        "1timothy", "2timothy", "titus", "philemon", "hebrews", "james",
        "1peter", "2peter", "1john", "2john", "3john", "jude", "revelation",
    ), strict=True), start=1)
}

FORBIDDEN_OUTPUT_FIELDS = {
    "gloss", "english", "chinese", "lemma", "morph", "strong", "domain",
    "ln", "frame", "referent", "subjref", "participant", "sense", "synonym",
    "semantic_role", "semanticrole",
}
ALLOWED_GROUP_ATTRIBUTES = {
    "class", "rule", "role", "type", "predication", "head",
}


@dataclass(frozen=True)
class MaculaWord:
    reference: str
    ordinal: int
    xml_id: str
    surface: str


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_checkout() -> None:
    actual = subprocess.run(
        ["git", "-C", str(MACULA_ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if actual != MACULA_COMMIT:
        raise ValueError(f"MACULA Greek checkout is {actual}, expected {MACULA_COMMIT}")
    license_text = (MACULA_ROOT / "LICENSE.md").read_text(encoding="utf-8")
    if "CC BY 4.0" not in license_text or MACULA_ATTRIBUTION not in license_text:
        raise ValueError("MACULA Greek license or required attribution is missing")


def lowfat_path(book: Book) -> Path:
    return MACULA_ROOT / "Nestle1904" / "lowfat" / LOWFAT_FILENAMES[book.utr_stem]


def normalized_greek(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.lower())
    return "".join(
        char for char in decomposed
        if not unicodedata.combining(char) and ("\u0370" <= char <= "\u03ff" or "\u1f00" <= char <= "\u1fff")
    ).replace("ς", "σ")


def scv_beta_key(value: str) -> str:
    return normalized_greek(scv_beta_to_unicode(value))


def robinson_token_key(token: dict) -> str | None:
    """Return a key only for one Robinson token with the same SCV surface.

    Human adjudication may legitimately bind Robinson morphology to a different
    SCV spelling or merge more than one Robinson token.  Those bindings remain
    valid in the text/morphology layer, but they are not three-source terminal
    agreement and therefore cannot anchor MACULA structure.
    """
    morphology = token.get("morphology") or {}
    if not isinstance(morphology.get("sourceOrdinal"), int):
        return None
    source_surface = morphology.get("sourceSurfaceBeta")
    if not isinstance(source_surface, str) or not source_surface:
        return None
    key = normalized_greek(beta_to_unicode(source_surface))
    return key if key == scv_beta_key(token["surfaceBeta"]) else None


def parse_macula_reference(value: str) -> tuple[str, int, int, int]:
    match = re.fullmatch(r"([A-Z0-9]+)\s+(\d+):(\d+)!(\d+)", value)
    if not match:
        raise ValueError(f"invalid MACULA Greek word reference: {value!r}")
    return match.group(1), int(match.group(2)), int(match.group(3)), int(match.group(4))


def stable_lcs_pairs(left: list[str], right: list[str]) -> list[tuple[int, int]]:
    """Return only token pairs forced by every optimal order-preserving match."""
    rows, columns = len(left), len(right)
    suffix = [[0] * (columns + 1) for _ in range(rows + 1)]
    for i in range(rows - 1, -1, -1):
        for j in range(columns - 1, -1, -1):
            suffix[i][j] = (
                suffix[i + 1][j + 1] + 1
                if left[i] == right[j]
                else max(suffix[i + 1][j], suffix[i][j + 1])
            )
    prefix = [[0] * (columns + 1) for _ in range(rows + 1)]
    for i in range(rows):
        for j in range(columns):
            prefix[i + 1][j + 1] = (
                prefix[i][j] + 1
                if left[i] == right[j]
                else max(prefix[i][j + 1], prefix[i + 1][j])
            )
    optimum = suffix[0][0]
    candidates = [
        (i, j)
        for i in range(rows)
        for j in range(columns)
        if left[i] == right[j]
        and prefix[i][j] + 1 + suffix[i + 1][j + 1] == optimum
    ]
    left_options: dict[int, set[int]] = {}
    right_options: dict[int, set[int]] = {}
    for i, j in candidates:
        left_options.setdefault(i, set()).add(j)
        right_options.setdefault(j, set()).add(i)
    unique = [
        (i, j)
        for i, j in candidates
        if len(left_options[i]) == 1 and len(right_options[j]) == 1
    ]
    return [
        (i, j)
        for i, j in unique
        if all(
            other_i == i
            or (other_i < i and other_j < j)
            or (other_i > i and other_j > j)
            for other_i, other_j in unique
        )
    ]


@lru_cache(maxsize=None)
def load_macula_words(book: Book) -> dict[str, list[MaculaWord]]:
    path = lowfat_path(book)
    if not path.is_file():
        raise FileNotFoundError(f"MACULA Greek lowfat file missing: {path}")
    expected_code = TR_CODE_BY_STEM[book.utr_stem]
    words: dict[str, list[MaculaWord]] = {}
    for _, element in ET.iterparse(path, events=("end",)):
        if element.tag.rsplit("}", 1)[-1] != "w":
            continue
        code, chapter, verse, ordinal = parse_macula_reference(element.get("ref") or "")
        if code != expected_code:
            raise ValueError(f"{path.name}: unexpected book code {code}")
        reference = f"{code}.{chapter}.{verse}"
        word = MaculaWord(
            reference=reference,
            ordinal=ordinal,
            xml_id=element.get("{http://www.w3.org/XML/1998/namespace}id") or "",
            surface="".join(element.itertext()).strip(),
        )
        if not word.xml_id or not word.surface:
            raise ValueError(f"{reference}!{ordinal}: incomplete MACULA terminal")
        words.setdefault(reference, []).append(word)
        element.clear()
    for reference, rows in words.items():
        rows.sort(key=lambda row: row.ordinal)
        if [row.ordinal for row in rows] != list(range(1, len(rows) + 1)):
            raise ValueError(f"{reference}: nonconsecutive MACULA word ordinals")
    return words


def map_verse(book: Book, chapter: int, verse: int, macula_words: list[MaculaWord]) -> dict:
    source = load_reconciled_verse(book, chapter, verse)
    tr_tokens = source["trTokens"]
    tr_keys = [scv_beta_key(token["surfaceBeta"]) for token in tr_tokens]
    robinson_keys = [robinson_token_key(token) for token in tr_tokens]
    macula_keys = [normalized_greek(word.surface) for word in macula_words]
    triple_exact = (
        all(key is not None for key in robinson_keys)
        and tr_keys == robinson_keys
        and tr_keys == macula_keys
    )
    if triple_exact:
        pairs = list(zip(range(len(tr_tokens)), range(len(macula_words)), strict=True))
    else:
        eligible_tr_indexes = [
            index for index, key in enumerate(robinson_keys) if key is not None
        ]
        eligible_tr_keys = [tr_keys[index] for index in eligible_tr_indexes]
        pairs = [
            (eligible_tr_indexes[left], right)
            for left, right in stable_lcs_pairs(eligible_tr_keys, macula_keys)
        ]
    mapped_tr = {left for left, _ in pairs}
    mapped_macula = {right for _, right in pairs}
    nonagreeing_robinson = {
        index for index, key in enumerate(robinson_keys) if key is None
    }
    return {
        "reference": f"{TR_CODE_BY_STEM[book.utr_stem]}.{chapter}.{verse}",
        "status": "exact" if triple_exact else "hold-token-disagreement",
        "trTokenCount": len(tr_tokens),
        "maculaTokenCount": len(macula_words),
        "mapping": [
            {
                "trTokenId": tr_tokens[left]["tokenId"],
                "maculaTerminalId": macula_words[right].xml_id,
                "basis": "scv-robinson-macula-normalized-surface-order",
            }
            for left, right in pairs
        ],
        "mappedTrTokenCount": len(mapped_tr),
        "unmatchedTrTokenIds": [
            token["tokenId"] for index, token in enumerate(tr_tokens) if index not in mapped_tr
        ],
        "unmatchedMaculaTerminalIds": [
            word.xml_id for index, word in enumerate(macula_words) if index not in mapped_macula
        ],
        "nonAgreeingRobinsonTokenIds": [
            token["tokenId"]
            for index, token in enumerate(tr_tokens)
            if index in nonagreeing_robinson
        ],
        "trSurfaceBeta": [token["surfaceBeta"] for token in tr_tokens] if not triple_exact else None,
        "maculaSurface": [word.surface for word in macula_words] if not triple_exact else None,
    }


def validate_mapping_ledger(ledger: dict) -> None:
    """Prove every persisted terminal link has three-source token agreement."""
    if ledger.get("schema") != "tr1894-macula-structure-mapping-v2":
        raise ValueError("noncanonical MACULA mapping schema")
    if ledger.get("policy") != MAPPING_POLICY:
        raise ValueError("noncanonical MACULA token-agreement policy")
    for row in ledger.get("verses") or []:
        code, chapter_text, verse_text = row["reference"].split(".")
        book = BOOK_BY_TR_CODE[code]
        chapter, verse = int(chapter_text), int(verse_text)
        tr_tokens = load_reconciled_verse(book, chapter, verse)["trTokens"]
        macula_words = load_macula_words(book).get(row["reference"], [])
        tr_by_id = {token["tokenId"]: (index, token) for index, token in enumerate(tr_tokens)}
        macula_by_id = {word.xml_id: (index, word) for index, word in enumerate(macula_words)}
        pairs = []
        for item in row.get("mapping") or []:
            if item.get("basis") != "scv-robinson-macula-normalized-surface-order":
                raise ValueError(f"{row['reference']}: unproved terminal mapping basis")
            tr_index, token = tr_by_id[item["trTokenId"]]
            macula_index, word = macula_by_id[item["maculaTerminalId"]]
            robinson_key = robinson_token_key(token)
            if (
                robinson_key is None
                or scv_beta_key(token["surfaceBeta"]) != robinson_key
                or normalized_greek(word.surface) != robinson_key
            ):
                raise ValueError(f"{row['reference']}: terminal lacks three-source agreement")
            pairs.append((tr_index, macula_index))
        tr_positions = [left for left, _ in pairs]
        macula_positions = [right for _, right in pairs]
        if (
            len(tr_positions) != len(set(tr_positions))
            or len(macula_positions) != len(set(macula_positions))
            or tr_positions != sorted(tr_positions)
            or macula_positions != sorted(macula_positions)
        ):
            raise ValueError(f"{row['reference']}: terminal mapping is duplicate or out of order")
        mapped_tr = {left for left, _ in pairs}
        mapped_macula = {right for _, right in pairs}
        expected_unmatched_tr = {
            token["tokenId"] for index, token in enumerate(tr_tokens) if index not in mapped_tr
        }
        expected_unmatched_macula = {
            word.xml_id for index, word in enumerate(macula_words) if index not in mapped_macula
        }
        expected_robinson_disagreement = {
            token["tokenId"] for token in tr_tokens if robinson_token_key(token) is None
        }
        if (
            row.get("mappedTrTokenCount") != len(pairs)
            or set(row.get("unmatchedTrTokenIds") or []) != expected_unmatched_tr
            or set(row.get("unmatchedMaculaTerminalIds") or []) != expected_unmatched_macula
            or set(row.get("nonAgreeingRobinsonTokenIds") or []) != expected_robinson_disagreement
        ):
            raise ValueError(f"{row['reference']}: mapping partitions do not reconstruct inputs")
        if row.get("status") == "exact" and (
            len(pairs) != len(tr_tokens)
            or len(pairs) != len(macula_words)
            or expected_robinson_disagreement
        ):
            raise ValueError(f"{row['reference']}: exact status lacks complete triple agreement")
def assert_allowed_projection(value: object) -> None:
    """Reject forbidden MACULA payload fields recursively in projected output."""
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in FORBIDDEN_OUTPUT_FIELDS:
                raise ValueError(f"forbidden MACULA Greek field in projection: {key}")
            assert_allowed_projection(child)
    elif isinstance(value, list):
        for child in value:
            assert_allowed_projection(child)


def validate_candidate(candidate: dict) -> None:
    assert_allowed_projection(candidate)
    if candidate.get("schema") != "tr1894-macula-structure-candidate-v1":
        raise ValueError("noncanonical MACULA structure candidate schema")
    mapped_ids: list[str] = []
    exact_groups = hold_groups = human_groups = adapted_groups = 0
    mapped_words = human_words = adapted_words = unmatched_words = 0
    unmatched_terminal_ids: set[str] = set()

    def walk(node: dict) -> tuple[bool, bool, set[str], set[str]]:
        nonlocal exact_groups, hold_groups, human_groups, adapted_groups
        nonlocal mapped_words, human_words, adapted_words, unmatched_words
        kind = node.get("kind")
        if kind == "word":
            mapped_words += 1
            token_id = node.get("trTokenId")
            if not token_id:
                raise ValueError("mapped candidate word lacks TR token identity")
            mapped_ids.append(token_id)
            return True, True, set(), set()
        if kind == "tr-word":
            token_id = node.get("trTokenId")
            decision_id = node.get("decisionId")
            adaptation_id = node.get("adaptationRuleId")
            if node.get("status") == "human-adjudicated-tr":
                human_words += 1
                if not token_id or not decision_id or adaptation_id or node.get("maculaTerminalId"):
                    raise ValueError("native TR candidate word lacks adjudication provenance")
            elif node.get("status") == "tr-authority-adapted":
                adapted_words += 1
                if not token_id or decision_id or adaptation_id not in TR_AUTHORITY_ADAPTATION_RULES or node.get("maculaTerminalId"):
                    raise ValueError("TR-authority adapted word lacks deterministic provenance")
            else:
                raise ValueError("native TR candidate word has an unknown status")
            mapped_ids.append(token_id)
            return (
                True,
                False,
                {decision_id} if decision_id else set(),
                {adaptation_id} if adaptation_id else set(),
            )
        if kind == "reference-word":
            unmatched_words += 1
            unmatched_terminal_ids.add(node.get("maculaTerminalId"))
            if node.get("status") != "hold-token-disagreement" or node.get("trTokenId"):
                raise ValueError("unmatched MACULA terminal is not isolated as HOLD")
            return False, False, set(), set()
        if kind != "group" or not node.get("children"):
            raise ValueError("candidate structural group is empty or malformed")
        child_results = [walk(child) for child in node["children"]]
        children_resolved = all(row[0] for row in child_results)
        children_exact = all(row[1] for row in child_results)
        child_decisions = set().union(*(row[2] for row in child_results))
        child_adaptations = set().union(*(row[3] for row in child_results))
        if node.get("status") == "exact-candidate":
            exact_groups += 1
            if not children_resolved or not children_exact:
                raise ValueError("exact structural candidate contains a HOLD child")
            return True, True, set(), set()
        if node.get("status") == "human-adjudicated-tr":
            human_groups += 1
            decisions = set(node.get("decisionIds") or [])
            local_decisions = set(node.get("localDecisionIds") or [])
            if not children_resolved or not decisions or decisions != child_decisions | local_decisions:
                raise ValueError(
                    f"human-adjudicated TR group lacks complete decision provenance: "
                    f"{node.get('candidateNodeId')} decisions={sorted(decisions)} "
                    f"children={sorted(child_decisions)} local={sorted(local_decisions)}"
                )
            return True, False, decisions, child_adaptations
        if node.get("status") == "tr-authority-adapted":
            adapted_groups += 1
            adaptations = set(node.get("adaptationRuleIds") or [])
            local_adaptations = set(node.get("localAdaptationRuleIds") or [])
            if (
                not children_resolved
                or adaptations != child_adaptations | local_adaptations
                or not adaptations
                or not adaptations.issubset(TR_AUTHORITY_ADAPTATION_RULES)
            ):
                raise ValueError(
                    "TR-authority adapted group lacks complete deterministic provenance: "
                    f"{node.get('candidateNodeId')} resolved={children_resolved} "
                    f"declared={sorted(adaptations)} children={sorted(child_adaptations)}"
                )
            return True, False, child_decisions, adaptations
        if node.get("status") != "hold-token-disagreement":
            raise ValueError("candidate group has an unknown review status")
        hold_groups += 1
        return False, False, child_decisions, child_adaptations

    for sentence in candidate.get("sentences") or []:
        for root in sentence.get("roots") or []:
            walk(root)
    if len(mapped_ids) != len(set(mapped_ids)):
        raise ValueError("a TR token appears more than once in the MACULA candidate")
    if set(mapped_ids) & set(candidate.get("trOnlyTokenIds") or []):
        raise ValueError("a TR-only token also appears as a mapped MACULA anchor")
    fallbacks = candidate.get("trAuthorityFallbacks")
    if fallbacks is not None:
        fallback_tokens: list[str] = []
        fallback_terminals: list[str] = []
        for row in fallbacks:
            if row.get("ruleId") != TR_AUTHORITY_FALLBACK_RULE:
                raise ValueError("TR fallback has an unknown deterministic rule")
            if not row.get("reference"):
                raise ValueError("TR fallback lacks a verse reference")
            fallback_tokens.extend(row.get("trTokenIds") or [])
            fallback_terminals.extend(row.get("removedMaculaTerminalIds") or [])
        if len(fallback_tokens) != len(set(fallback_tokens)):
            raise ValueError("a TR token appears in more than one fallback")
        if len(fallback_terminals) != len(set(fallback_terminals)):
            raise ValueError("a MACULA terminal appears in more than one fallback")
        fallback_expected_tokens = set(candidate.get("trOnlyTokenIds") or []) | set(
            candidate.get("unplacedMappedTrTokenIds") or []
        )
        if set(fallback_tokens) != fallback_expected_tokens:
            raise ValueError("TR fallbacks do not cover every remaining TR-only token")
        retired_noncanonical = set(
            candidate.get("retiredNoncanonicalMaculaTerminalIds") or []
        )
        if retired_noncanonical & set(fallback_terminals):
            raise ValueError("a MACULA terminal is retired twice")
        if set(fallback_terminals) | retired_noncanonical != unmatched_terminal_ids:
            raise ValueError("TR fallbacks do not retire every remaining MACULA terminal")
    expected = candidate.get("summary") or {}
    actual = {
        "exactGroups": exact_groups,
        "holdGroups": hold_groups,
        "humanAdjudicatedGroups": human_groups,
        "trAuthorityAdaptedGroups": adapted_groups,
        "mappedWords": mapped_words,
        "humanAdjudicatedWords": human_words,
        "trAuthorityAdaptedWords": adapted_words,
        "unmatchedMaculaWords": unmatched_words,
        "trOnlyTokens": len(candidate.get("trOnlyTokenIds") or []),
        "trAuthorityFallbackVerses": len(candidate.get("trAuthorityFallbacks") or []),
        "retiredNoncanonicalMaculaWords": len(
            candidate.get("retiredNoncanonicalMaculaTerminalIds") or []
        ),
        "unplacedMappedTrTokens": len(
            candidate.get("unplacedMappedTrTokenIds") or []
        ),
    }
    if any(expected.get(key, 0) != value for key, value in actual.items()):
        raise ValueError(f"candidate summary differs from tree counts: {actual}")


def refresh_candidate_summary(candidate: dict) -> None:
    counts = {
        "exactGroups": 0,
        "holdGroups": 0,
        "humanAdjudicatedGroups": 0,
        "trAuthorityAdaptedGroups": 0,
        "mappedWords": 0,
        "humanAdjudicatedWords": 0,
        "trAuthorityAdaptedWords": 0,
        "unmatchedMaculaWords": 0,
    }

    def recount(node: dict) -> None:
        kind = node.get("kind")
        if kind == "word":
            counts["mappedWords"] += 1
        elif kind == "tr-word":
            if node.get("status") == "human-adjudicated-tr":
                counts["humanAdjudicatedWords"] += 1
            elif node.get("status") == "tr-authority-adapted":
                counts["trAuthorityAdaptedWords"] += 1
        elif kind == "reference-word":
            counts["unmatchedMaculaWords"] += 1
        elif kind == "group":
            key = {
                "exact-candidate": "exactGroups",
                "hold-token-disagreement": "holdGroups",
                "human-adjudicated-tr": "humanAdjudicatedGroups",
                "tr-authority-adapted": "trAuthorityAdaptedGroups",
            }[node["status"]]
            counts[key] += 1
        for child in node.get("children") or []:
            recount(child)

    for sentence in candidate.get("sentences") or []:
        for root in sentence.get("roots") or []:
            recount(root)
    candidate["summary"] = {
        **counts,
        "trOnlyTokens": len(candidate.get("trOnlyTokenIds") or []),
        "trAuthorityFallbackVerses": len(candidate.get("trAuthorityFallbacks") or []),
        "retiredNoncanonicalMaculaWords": len(
            candidate.get("retiredNoncanonicalMaculaTerminalIds") or []
        ),
        "unplacedMappedTrTokens": len(
            candidate.get("unplacedMappedTrTokenIds") or []
        ),
    }


def apply_tr_authority_fallbacks(candidate: dict, mapping_ledger: dict) -> dict:
    """Record a transparent TR-native fallback for every unresolved verse.

    The comparative MACULA tree remains available for review.  The fallback
    supplies only canonical TR terminals that the comparison could not place
    and retires unmatched MACULA terminals from the evidence view.  It makes
    no claim about their grammatical function or attachment.
    """
    book = next(item for item in NT if item.slug == candidate.get("book"))
    chapter = int(candidate.get("chapter") or 0)
    code = TR_CODE_BY_STEM[book.utr_stem]
    terminal_reference = {
        terminal_id: row["reference"]
        for row in mapping_ledger.get("verses") or []
        if row.get("reference", "").startswith(f"{code}.{chapter}.")
        for terminal_id in row.get("unmatchedMaculaTerminalIds") or []
    }
    mapped_token_ids: set[str] = set()

    def collect_mapped(node: dict) -> None:
        if node.get("kind") in {"word", "tr-word"}:
            mapped_token_ids.add(node["trTokenId"])
        for child in node.get("children") or []:
            collect_mapped(child)

    for sentence in candidate.get("sentences") or []:
        for root in sentence.get("roots") or []:
            collect_mapped(root)
    canonical_token_ids = {
        token["tokenId"]
        for row in mapping_ledger.get("verses") or []
        if row.get("reference", "").startswith(f"{code}.{chapter}.")
        for token in load_reconciled_verse(
            book, chapter, int(row["reference"].rsplit(".", 1)[-1])
        )["trTokens"]
    }
    tr_only = set(candidate.get("trOnlyTokenIds") or [])
    unplaced_mapped = sorted(canonical_token_ids - mapped_token_ids - tr_only)
    candidate["unplacedMappedTrTokenIds"] = unplaced_mapped
    tokens_by_reference: dict[str, list[str]] = {}
    for token_id in [*(candidate.get("trOnlyTokenIds") or []), *unplaced_mapped]:
        reference = token_id.rsplit(".w", 1)[0]
        tokens_by_reference.setdefault(reference, []).append(token_id)
    terminals_by_reference: dict[str, list[str]] = {}
    retired_noncanonical: list[str] = []

    def collect(node: dict) -> None:
        if node.get("kind") == "reference-word":
            terminal_id = node.get("maculaTerminalId")
            reference = terminal_reference.get(terminal_id)
            if not reference:
                retired_noncanonical.append(terminal_id)
            else:
                terminals_by_reference.setdefault(reference, []).append(terminal_id)
        for child in node.get("children") or []:
            collect(child)

    for sentence in candidate.get("sentences") or []:
        for root in sentence.get("roots") or []:
            collect(root)
    references = sorted(
        set(tokens_by_reference) | set(terminals_by_reference),
        key=lambda reference: int(reference.rsplit(".", 1)[-1]),
    )
    candidate["trAuthorityFallbacks"] = [
        {
            "ruleId": TR_AUTHORITY_FALLBACK_RULE,
            "reference": reference,
            "trTokenIds": tokens_by_reference.get(reference, []),
            "removedMaculaTerminalIds": terminals_by_reference.get(reference, []),
            "structuralClaim": "none-beyond-canonical-tr-order",
        }
        for reference in references
    ]
    candidate["retiredNoncanonicalMaculaTerminalIds"] = retired_noncanonical
    refresh_candidate_summary(candidate)
    validate_candidate(candidate)
    return candidate


def apply_tr_authority_adaptations(
    candidate: dict,
    mapping_ledger: dict,
    adjudications: dict,
) -> dict:
    """Replace only isolated one-to-one MACULA gaps with native TR terminals."""
    book = next(item for item in NT if item.slug == candidate.get("book"))
    chapter = int(candidate.get("chapter") or 0)
    code = TR_CODE_BY_STEM[book.utr_stem]
    excluded_tokens = {
        token_id
        for decision in adjudications.get("decisions") or []
        if decision.get("book") == book.slug and decision.get("chapter") == chapter
        for token_id in decision.get("trTokenIds") or []
    }
    excluded_terminals = {
        terminal_id
        for decision in adjudications.get("decisions") or []
        if decision.get("book") == book.slug and decision.get("chapter") == chapter
        for terminal_id in decision.get("replacedMaculaTerminalIds") or []
    }
    excluded_nodes = {
        str(decision.get("targetCandidateNodeId"))
        for decision in adjudications.get("decisions") or []
        if decision.get("book") == book.slug
        and decision.get("chapter") == chapter
        and decision.get("targetCandidateNodeId")
    }
    reference_words: dict[str, dict] = {}
    reference_parents: dict[str, dict] = {}

    def index(node: dict, parent: dict | None = None) -> None:
        if node.get("kind") == "reference-word":
            reference_words[node["maculaTerminalId"]] = node
            if parent is not None:
                reference_parents[node["maculaTerminalId"]] = parent
        for child in node.get("children") or []:
            index(child, node)

    for sentence in candidate.get("sentences") or []:
        for root in sentence.get("roots") or []:
            index(root)

    applied = []
    adapted_tokens: set[str] = set()
    omission_gaps: list[dict] = []
    permutation_gaps: list[dict] = []
    for row in mapping_ledger.get("verses") or []:
        if not row.get("reference", "").startswith(f"{code}.{chapter}."):
            continue
        verse = int(row["reference"].rsplit(".", 1)[-1])
        tr_tokens = load_reconciled_verse(book, chapter, verse)["trTokens"]
        macula_words = load_macula_words(book).get(row["reference"], [])
        tr_positions = {token["tokenId"]: index for index, token in enumerate(tr_tokens)}
        macula_positions = {word.xml_id: index for index, word in enumerate(macula_words)}
        anchors = sorted(
            (
                tr_positions[item["trTokenId"]],
                macula_positions[item["maculaTerminalId"]],
                item["trTokenId"],
                item["maculaTerminalId"],
            )
            for item in row.get("mapping") or []
        )
        boundaries = [(-1, -1, None, None), *anchors, (len(tr_tokens), len(macula_words), None, None)]
        disagreements = set(row.get("nonAgreeingRobinsonTokenIds") or [])
        for left, right in zip(boundaries, boundaries[1:]):
            tr_gap = list(range(left[0] + 1, right[0]))
            macula_gap = list(range(left[1] + 1, right[1]))
            if not tr_gap and len(macula_gap) == 1:
                omission_gaps.append({
                    "reference": row["reference"],
                    "terminalId": macula_words[macula_gap[0]].xml_id,
                    "left": left,
                    "right": right,
                })
                continue
            if len(tr_gap) == len(macula_gap) and len(tr_gap) > 1:
                gap_tokens = [tr_tokens[index] for index in tr_gap]
                gap_words = [macula_words[index] for index in macula_gap]
                approved = all(
                    token["tokenId"] not in disagreements
                    or str((token.get("morphology") or {}).get("reconciliation") or "").startswith("human-approved-")
                    for token in gap_tokens
                )
                if approved and Counter(
                    scv_beta_key(token["surfaceBeta"]) for token in gap_tokens
                ) == Counter(normalized_greek(word.surface) for word in gap_words):
                    permutation_gaps.append({
                        "reference": row["reference"],
                        "trTokenIds": [token["tokenId"] for token in gap_tokens],
                        "terminalIds": [word.xml_id for word in gap_words],
                        "left": left,
                        "right": right,
                    })
                continue
            if len(tr_gap) != 1 or len(macula_gap) != 1:
                continue
            token = tr_tokens[tr_gap[0]]
            terminal = macula_words[macula_gap[0]]
            token_id = token["tokenId"]
            terminal_id = terminal.xml_id
            node = reference_words.get(terminal_id)
            reconciliation = str((token.get("morphology") or {}).get("reconciliation") or "")
            approved_robinson_binding = reconciliation.startswith("human-approved-")
            if (
                (token_id in disagreements and not approved_robinson_binding)
                or token_id in excluded_tokens
                or terminal_id in excluded_terminals
                or token_id not in candidate.get("trOnlyTokenIds", [])
                or not node
            ):
                continue
            rule_id = (
                APPROVED_ROBINSON_BINDING_RULE
                if token_id in disagreements
                else TR_AUTHORITY_ADAPTATION_RULE
            )
            node.clear()
            node.update({
                "kind": "tr-word",
                "status": "tr-authority-adapted",
                "trTokenId": token_id,
                "adaptationRuleId": rule_id,
            })
            adapted_tokens.add(token_id)
            applied.append({
                "ruleId": rule_id,
                "reference": row["reference"],
                "trTokenId": token_id,
                "replacedMaculaTerminalId": terminal_id,
                "leftAnchorTrTokenId": left[2],
                "leftAnchorMaculaTerminalId": left[3],
                "rightAnchorTrTokenId": right[2],
                "rightAnchorMaculaTerminalId": right[3],
            })

    def rebuild_reference_index() -> None:
        reference_words.clear()
        reference_parents.clear()
        for sentence in candidate.get("sentences") or []:
            for root in sentence.get("roots") or []:
                index(root)

    for gap in permutation_gaps:
        rebuild_reference_index()
        token_ids = gap["trTokenIds"]
        terminal_ids = gap["terminalIds"]
        if (
            any(token_id in excluded_tokens for token_id in token_ids)
            or any(terminal_id in excluded_terminals for terminal_id in terminal_ids)
        ):
            continue
        nodes = [reference_words.get(terminal_id) for terminal_id in terminal_ids]
        parents = [reference_parents.get(terminal_id) for terminal_id in terminal_ids]
        parent = parents[0] if parents else None
        if (
            not parent
            or any(node is None for node in nodes)
            or any(item is not parent for item in parents)
            or parent.get("kind") != "group"
            or parent.get("status") != "hold-token-disagreement"
            or parent.get("candidateNodeId") in excluded_nodes
            or len(parent.get("children") or []) != len(terminal_ids)
            or any(child.get("kind") != "reference-word" for child in parent["children"])
            or {child.get("maculaTerminalId") for child in parent["children"]} != set(terminal_ids)
        ):
            continue
        parent["children"] = [
            {
                "kind": "tr-word",
                "status": "tr-authority-adapted",
                "trTokenId": token_id,
                "adaptationRuleId": FLAT_PERMUTATION_RULE,
            }
            for token_id in token_ids
        ]
        parent["status"] = "tr-authority-adapted"
        parent["adaptationRuleIds"] = [FLAT_PERMUTATION_RULE]
        parent["localAdaptationRuleIds"] = [FLAT_PERMUTATION_RULE]
        adapted_tokens.update(token_ids)
        applied.append({
            "ruleId": FLAT_PERMUTATION_RULE,
            "reference": gap["reference"],
            "targetCandidateNodeId": parent["candidateNodeId"],
            "trTokenIds": token_ids,
            "replacedMaculaTerminalIds": terminal_ids,
            "leftAnchorTrTokenId": gap["left"][2],
            "leftAnchorMaculaTerminalId": gap["left"][3],
            "rightAnchorTrTokenId": gap["right"][2],
            "rightAnchorMaculaTerminalId": gap["right"][3],
        })

    for gap in omission_gaps:
        rebuild_reference_index()
        terminal_id = gap["terminalId"]
        node = reference_words.get(terminal_id)
        parent = reference_parents.get(terminal_id)
        if (
            terminal_id in excluded_terminals
            or not node
            or not parent
            or parent.get("kind") != "group"
            or parent.get("status") != "hold-token-disagreement"
            or parent.get("candidateNodeId") in excluded_nodes
            or len(parent.get("children") or []) != 2
        ):
            continue
        other = next((child for child in parent["children"] if child is not node), None)
        if (
            not other
            or other.get("kind") != "group"
            or other.get("candidateNodeId") in excluded_nodes
            or other.get("status") not in {"exact-candidate", "tr-authority-adapted"}
        ):
            continue
        target_id = parent["candidateNodeId"]
        inherited_rules = set(other.get("adaptationRuleIds") or [])
        promoted = {
            key: value
            for key, value in other.items()
            if key not in {
                "candidateNodeId", "status", "adaptationRuleIds",
                "localAdaptationRuleIds",
            }
        }
        parent.clear()
        parent.update({
            "candidateNodeId": target_id,
            **promoted,
            "status": "tr-authority-adapted",
            "adaptationRuleIds": sorted(inherited_rules | {MACULA_ONLY_PROMOTE_CHILD_RULE}),
            "localAdaptationRuleIds": [MACULA_ONLY_PROMOTE_CHILD_RULE],
        })
        applied.append({
            "ruleId": MACULA_ONLY_PROMOTE_CHILD_RULE,
            "reference": gap["reference"],
            "targetCandidateNodeId": target_id,
            "replacedMaculaTerminalId": terminal_id,
            "leftAnchorTrTokenId": gap["left"][2],
            "leftAnchorMaculaTerminalId": gap["left"][3],
            "rightAnchorTrTokenId": gap["right"][2],
            "rightAnchorMaculaTerminalId": gap["right"][3],
        })

    def propagate(node: dict) -> tuple[bool, set[str]]:
        if node.get("kind") == "reference-word":
            return False, set()
        if node.get("kind") == "tr-word":
            rule = node.get("adaptationRuleId")
            return True, ({rule} if rule else set())
        if node.get("kind") == "word":
            return True, set()
        child_rows = [propagate(child) for child in node.get("children") or []]
        resolved = all(row[0] for row in child_rows)
        rules = set(node.get("localAdaptationRuleIds") or []).union(*(row[1] for row in child_rows))
        if node.get("status") == "hold-token-disagreement":
            if resolved and rules:
                node["status"] = "tr-authority-adapted"
                node["adaptationRuleIds"] = sorted(rules)
                return True, rules
            return False, rules
        return resolved, rules

    for sentence in candidate.get("sentences") or []:
        for root in sentence.get("roots") or []:
            propagate(root)
    candidate["trOnlyTokenIds"] = [
        token_id for token_id in candidate.get("trOnlyTokenIds") or []
        if token_id not in adapted_tokens
    ]
    candidate["trAuthorityAdaptations"] = applied
    refresh_candidate_summary(candidate)
    validate_candidate(candidate)
    return candidate


def apply_structure_adjudications(candidate: dict, adjudications: dict) -> dict:
    """Overlay explicit human TR-native branches without inventing MACULA links."""
    if adjudications.get("schema") != STRUCTURE_ADJUDICATION_SCHEMA:
        raise ValueError("noncanonical NT structure adjudication schema")
    nodes: dict[str, dict] = {}
    reference_words: dict[str, dict] = {}
    mapped_words: dict[str, dict] = {}

    def index(node: dict) -> None:
        node_id = node.get("candidateNodeId")
        if node_id:
            if node_id in nodes:
                raise ValueError(f"duplicate candidate node id: {node_id}")
            nodes[node_id] = node
        terminal_id = node.get("maculaTerminalId")
        token_id = node.get("trTokenId")
        if node.get("kind") == "word" and token_id:
            mapped_words[token_id] = node
        if node.get("kind") == "reference-word" and terminal_id:
            if terminal_id in reference_words:
                raise ValueError(f"duplicate unmatched MACULA terminal id: {terminal_id}")
            reference_words[terminal_id] = node
        for child in node.get("children") or []:
            index(child)

    for sentence in candidate.get("sentences") or []:
        for root in sentence.get("roots") or []:
            index(root)
    node_templates = {node_id: copy.deepcopy(node) for node_id, node in nodes.items()}

    def subtree_terminals(node: dict) -> list[str]:
        terminal = node.get("maculaTerminalId")
        return ([terminal] if terminal else []) + [
            item
            for child in node.get("children") or []
            for item in subtree_terminals(child)
        ]

    applied: list[dict] = []
    for decision in adjudications.get("decisions") or []:
        if decision.get("book") != candidate.get("book") or decision.get("chapter") != candidate.get("chapter"):
            continue
        decision_id = decision.get("decisionId")
        decision_type = decision.get("decision")
        target = nodes.get(decision.get("targetCandidateNodeId"))
        token_ids = decision.get("trTokenIds") or []
        terminal_ids = decision.get("replacedMaculaTerminalIds") or []
        native = decision.get("nativeGroup") or {}
        metadata_valid = (
            bool(decision_id)
            and bool(decision.get("reviewer"))
            and bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(decision.get("date") or "")))
        )
        common_valid = metadata_valid and bool(token_ids) and len(token_ids) == len(set(token_ids)) and all(
            token_id.startswith(f"{decision.get('reference')}.") for token_id in token_ids
        )
        if decision_type == "replace-subtree-with-rebound-macula-structure":
            source_template = node_templates.get(decision.get("sourceCandidateNodeId"))
            terminal_to_token = decision.get("terminalToTrTokenIds") or {}

            source_terminals = subtree_terminals(source_template or {})
            target_terminals = subtree_terminals(target or {})
            if (
                not common_valid
                or not target
                or target.get("kind") != "group"
                or target.get("status") != "hold-token-disagreement"
                or not source_template
                or source_template.get("kind") != "group"
                or set(terminal_to_token) != set(source_terminals)
                or len(source_terminals) != len(terminal_to_token)
                or set(terminal_to_token.values()) != set(token_ids)
                or len(terminal_to_token.values()) != len(token_ids)
                or terminal_ids != target_terminals
            ):
                raise ValueError(f"invalid rebound MACULA structure adjudication: {decision_id!r}")
            rebound = copy.deepcopy(source_template)
            target_id = target["candidateNodeId"]
            group_sequence = 0

            def rebind(node: dict, *, root: bool = False) -> None:
                nonlocal group_sequence
                if node.get("kind") == "group":
                    group_sequence += 1
                    node["candidateNodeId"] = (
                        target_id if root else f"{target_id}.native{group_sequence:03d}"
                    )
                    node["status"] = "human-adjudicated-tr"
                    node["decisionIds"] = [decision_id]
                    node["localDecisionIds"] = [decision_id]
                    for child in node.get("children") or []:
                        rebind(child)
                    return
                terminal_id = node.get("maculaTerminalId")
                token_id = terminal_to_token.get(terminal_id)
                if not token_id:
                    raise ValueError(f"{decision_id}: source terminal lacks a TR binding")
                node.clear()
                node.update({
                    "kind": "tr-word",
                    "status": "human-adjudicated-tr",
                    "trTokenId": token_id,
                    "decisionId": decision_id,
                })

            rebind(rebound, root=True)
            target.clear()
            target.update(rebound)
            applied.append({
                "decisionId": decision_id,
                "reference": decision["reference"],
                "reviewer": decision["reviewer"],
                "date": decision["date"],
                "targetCandidateNodeId": target_id,
                "sourceCandidateNodeId": decision["sourceCandidateNodeId"],
                "replacedMaculaTerminalIds": terminal_ids,
                "reason": decision.get("reason"),
            })
            continue
        if decision_type in {
            "rebuild-group-in-tr-order-from-existing-anchors",
            "rebuild-group-in-tr-order-with-native-tr-words",
        }:
            child_specs = decision.get("nativeChildren") or []
            permits_native_words = decision_type == "rebuild-group-in-tr-order-with-native-tr-words"
            if (
                not metadata_valid
                or (not permits_native_words and token_ids)
                or (permits_native_words and not common_valid)
                or not target
                or target.get("kind") != "group"
                or target.get("status") not in (
                    {"hold-token-disagreement", "exact-candidate"}
                    if permits_native_words else {"hold-token-disagreement"}
                )
                or not child_specs
            ):
                raise ValueError(f"invalid native TR order adjudication: {decision_id!r}")

            def leaf_tokens(node: dict) -> list[str]:
                if node.get("kind") == "word":
                    return [node["trTokenId"]]
                return [token for child in node.get("children") or [] for token in leaf_tokens(child)]

            existing_tokens = set(leaf_tokens(target))
            existing_reference_terminals = subtree_terminals(target)
            existing_reference_terminals = [
                terminal_id
                for terminal_id in existing_reference_terminals
                if terminal_id in reference_words
            ]
            if terminal_ids != existing_reference_terminals:
                raise ValueError(f"{decision_id}: replaced MACULA terminals do not match the target")
            children = []
            selected_tokens: list[str] = []
            selected_native_tokens: list[str] = []
            for spec in child_specs:
                native_token_id = spec.get("nativeTrTokenId")
                if native_token_id:
                    if not permits_native_words or native_token_id not in token_ids:
                        raise ValueError(f"{decision_id}: unauthorized native TR child")
                    child = {
                        "kind": "tr-word",
                        "status": "human-adjudicated-tr",
                        "trTokenId": native_token_id,
                        "decisionId": decision_id,
                    }
                    selected_native_tokens.append(native_token_id)
                elif spec.get("trTokenId"):
                    child = mapped_words.get(spec["trTokenId"])
                else:
                    child = nodes.get(spec.get("candidateNodeId"))
                if child is None:
                    raise ValueError(f"{decision_id}: native child no longer exists")
                children.append(child)
                if not native_token_id:
                    selected_tokens.extend(leaf_tokens(child))
            if set(selected_tokens) != existing_tokens or len(selected_tokens) != len(existing_tokens):
                raise ValueError(f"{decision_id}: native children do not preserve the target TR anchors")
            if (
                set(selected_native_tokens) != set(token_ids)
                or len(selected_native_tokens) != len(token_ids)
                or any(token_id not in candidate.get("trOnlyTokenIds", []) for token_id in token_ids)
            ):
                raise ValueError(f"{decision_id}: native TR children do not match the unresolved TR tokens")
            target["children"] = children
            target["status"] = "human-adjudicated-tr"
            target["decisionIds"] = [decision_id]
            target["localDecisionIds"] = [decision_id]
            for field in ("category", "rule", "function", "clauseType"):
                if field in native:
                    target[field] = native[field]
                else:
                    target.pop(field, None)
            applied.append({
                "decisionId": decision_id,
                "reference": decision["reference"],
                "reviewer": decision["reviewer"],
                "date": decision["date"],
                "targetCandidateNodeId": decision["targetCandidateNodeId"],
                "reason": decision.get("reason"),
            })
            continue
        if decision_type == "remove-macula-terminal-and-promote-only-child":
            if (
                not metadata_valid
                or token_ids
                or len(terminal_ids) != 1
                or not target
                or target.get("kind") != "group"
                or target.get("status") != "hold-token-disagreement"
                or len(target.get("children") or []) != 2
            ):
                raise ValueError(f"invalid native TR elision adjudication: {decision_id!r}")
            removed = target["children"][0]
            kept = target["children"][1]
            if (
                removed.get("kind") != "reference-word"
                or removed.get("maculaTerminalId") != terminal_ids[0]
                or kept.get("kind") != "group"
            ):
                raise ValueError(f"{decision_id}: target MACULA elision branch changed")
            target_id = target["candidateNodeId"]
            promoted = {key: value for key, value in kept.items() if key != "candidateNodeId"}
            target.clear()
            target.update({
                "candidateNodeId": target_id,
                **promoted,
                "status": "human-adjudicated-tr",
                "decisionIds": [decision_id],
                "localDecisionIds": [decision_id],
            })
            applied.append({
                "decisionId": decision_id,
                "reference": decision["reference"],
                "reviewer": decision["reviewer"],
                "date": decision["date"],
                "targetCandidateNodeId": target_id,
                "removedMaculaTerminalIds": terminal_ids,
                "reason": decision.get("reason"),
            })
            continue
        if decision_type == "replace-macula-terminal-with-native-tr-word":
            if not common_valid or len(token_ids) != 1 or len(terminal_ids) != 1:
                raise ValueError(f"invalid native TR terminal adjudication: {decision_id!r}")
            terminal = reference_words.get(terminal_ids[0])
            if not terminal or terminal.get("status") != "hold-token-disagreement":
                raise ValueError(f"{decision_id}: target MACULA terminal changed")
            terminal.clear()
            terminal.update({
                "kind": "tr-word",
                "status": "human-adjudicated-tr",
                "trTokenId": token_ids[0],
                "decisionId": decision_id,
            })
            applied.append({
                "decisionId": decision_id,
                "reference": decision["reference"],
                "reviewer": decision["reviewer"],
                "date": decision["date"],
                "replacedMaculaTerminalIds": terminal_ids,
                "reason": decision.get("reason"),
            })
            continue
        if (
            not common_valid
            or not target
            or target.get("kind") != "group"
            or target.get("status") != "hold-token-disagreement"
            or decision_type != "replace-macula-order-with-native-tr-group"
            or len(token_ids) < 2
        ):
            raise ValueError(f"invalid native TR structure adjudication: {decision_id!r}")
        current_terminals = [
            child.get("maculaTerminalId")
            for child in target.get("children") or []
            if child.get("kind") == "reference-word"
        ]
        if current_terminals != terminal_ids or len(current_terminals) != len(target.get("children") or []):
            raise ValueError(f"{decision_id}: target MACULA branch changed")
        target["status"] = "human-adjudicated-tr"
        target["decisionIds"] = [decision_id]
        target["children"] = [
            {
                "kind": "tr-word",
                "status": "human-adjudicated-tr",
                "trTokenId": token_id,
                "decisionId": decision_id,
            }
            for token_id in token_ids
        ]
        for field in ("category", "rule", "function", "clauseType"):
            if native.get(field):
                target[field] = native[field]
            else:
                target.pop(field, None)
        applied.append({
            "decisionId": decision_id,
            "reference": decision["reference"],
            "reviewer": decision["reviewer"],
            "date": decision["date"],
            "targetCandidateNodeId": decision["targetCandidateNodeId"],
            "reason": decision.get("reason"),
        })

    def propagate(node: dict) -> tuple[bool, bool, set[str]]:
        if node.get("kind") == "reference-word":
            return False, False, set()
        if node.get("kind") == "tr-word":
            decision_id = node.get("decisionId")
            return True, False, ({decision_id} if decision_id else set())
        if node.get("kind") == "word":
            return True, True, set()
        child_rows = [propagate(child) for child in node.get("children") or []]
        resolved = all(row[0] for row in child_rows)
        children_exact = all(row[1] for row in child_rows)
        decisions = set(node.get("localDecisionIds") or []).union(*(row[2] for row in child_rows))
        if node.get("status") == "hold-token-disagreement" and resolved:
            if decisions:
                node["status"] = "human-adjudicated-tr"
                node["decisionIds"] = sorted(decisions)
            elif children_exact:
                # MACULA trees may place postpositive particles before their
                # clauses or otherwise use structural rather than surface
                # child order. Once every leaf is an exact triple-agreement
                # anchor, that ordering is not a token disagreement.
                node["status"] = "exact-candidate"
            else:
                return False, False, decisions
        return resolved, node.get("status") == "exact-candidate" and children_exact, decisions

    for sentence in candidate.get("sentences") or []:
        for root in sentence.get("roots") or []:
            propagate(root)
    resolved_token_ids = {
        token_id
        for decision in adjudications.get("decisions") or []
        if decision.get("book") == candidate.get("book") and decision.get("chapter") == candidate.get("chapter")
        for token_id in decision.get("trTokenIds") or []
    }
    candidate["trOnlyTokenIds"] = [
        token_id for token_id in candidate.get("trOnlyTokenIds") or []
        if token_id not in resolved_token_ids
    ]
    candidate["structureAdjudications"] = applied

    refresh_candidate_summary(candidate)
    validate_candidate(candidate)
    return candidate


def project_chapter_candidate(book: Book, chapter: int, mapping_ledger: dict) -> dict:
    """Project an explicitly noncanonical, conservative structural candidate."""
    code = TR_CODE_BY_STEM[book.utr_stem]
    verse_rows = {
        row["reference"]: row
        for row in mapping_ledger.get("verses") or []
        if row["reference"].startswith(f"{code}.{chapter}.")
    }
    terminal_map = {
        item["maculaTerminalId"]: item["trTokenId"]
        for row in verse_rows.values()
        for item in row.get("mapping") or []
    }
    tr_tokens = []
    for reference in sorted(
        verse_rows, key=lambda ref: int(ref.rsplit(".", 1)[-1])
    ):
        verse = int(reference.rsplit(".", 1)[-1])
        tr_tokens.extend(load_reconciled_verse(book, chapter, verse)["trTokens"])
    position = {token["tokenId"]: index for index, token in enumerate(tr_tokens)}
    tr_only = {
        token_id
        for row in verse_rows.values()
        for token_id in row.get("unmatchedTrTokenIds") or []
    }

    tree = ET.parse(lowfat_path(book))
    candidates = []
    node_sequence = 0
    counts = {
        "exactGroups": 0,
        "holdGroups": 0,
        "humanAdjudicatedGroups": 0,
        "mappedWords": 0,
        "humanAdjudicatedWords": 0,
        "unmatchedMaculaWords": 0,
    }

    def convert(element: ET.Element) -> tuple[dict | None, list[str], bool]:
        nonlocal node_sequence
        name = element.tag.rsplit("}", 1)[-1]
        if name == "w":
            _, word_chapter, _, _ = parse_macula_reference(element.get("ref") or "")
            if word_chapter != chapter:
                return None, [], True
            macula_id = element.get("{http://www.w3.org/XML/1998/namespace}id") or ""
            tr_id = terminal_map.get(macula_id)
            if tr_id is None:
                counts["unmatchedMaculaWords"] += 1
                return ({
                    "kind": "reference-word",
                    "status": "hold-token-disagreement",
                    "maculaTerminalId": macula_id,
                }, [], False)
            counts["mappedWords"] += 1
            return ({
                "kind": "word",
                "status": "mapped-anchor",
                "trTokenId": tr_id,
                "maculaTerminalId": macula_id,
            }, [tr_id], True)
        if name != "wg":
            return None, [], True

        child_rows = [convert(child) for child in list(element) if child.tag.rsplit("}", 1)[-1] in {"wg", "w"}]
        children = [row[0] for row in child_rows if row[0] is not None]
        token_ids = [token_id for row in child_rows for token_id in row[1]]
        if not children:
            return None, [], True
        child_exact = all(row[2] for row in child_rows)
        ordered_positions = [position[token_id] for token_id in token_ids if token_id in position]
        ordered = ordered_positions == sorted(set(ordered_positions))
        crosses_tr_only = bool(ordered_positions) and any(
            min(ordered_positions) <= position[token_id] <= max(ordered_positions)
            for token_id in tr_only
            if token_id in position
        )
        exact = bool(children) and child_exact and ordered and not crosses_tr_only
        node_sequence += 1
        node = {
            "candidateNodeId": f"{code}.{chapter}.mc{node_sequence:05d}",
            "kind": "group",
            "status": "exact-candidate" if exact else "hold-token-disagreement",
            "children": children,
        }
        attrs = element.attrib
        if attrs.get("class"):
            node["category"] = attrs["class"]
        if attrs.get("rule"):
            node["rule"] = attrs["rule"]
        if attrs.get("role"):
            node["function"] = attrs["role"]
        if attrs.get("type") or attrs.get("predication"):
            node["clauseType"] = attrs.get("type") or attrs.get("predication")
        counts["exactGroups" if exact else "holdGroups"] += 1
        return node, token_ids, exact

    for sentence_number, sentence in enumerate(tree.getroot().iter("sentence"), start=1):
        roots = []
        for child in list(sentence):
            if child.tag.rsplit("}", 1)[-1] == "wg":
                projected, _, _ = convert(child)
                if projected is not None:
                    roots.append(projected)
        if roots:
            candidates.append({
                "candidateSentenceId": f"{code}.{chapter}.ms{sentence_number:04d}",
                "roots": roots,
            })

    output = {
        "schema": "tr1894-macula-structure-candidate-v1",
        "status": "review-only-not-canonical",
        "book": book.slug,
        "chapter": chapter,
        "provenance": {
            "textAuthority": "Scrivener TR1894",
            "morphologyProvider": "Robinson",
            "referenceDataset": "MACULA Greek Nestle1904 lowfat",
            "referenceRevision": MACULA_COMMIT,
            "mappingPolicy": MAPPING_POLICY,
            "attribution": MACULA_ATTRIBUTION,
        },
        "summary": {**counts, "trOnlyTokens": len(tr_only)},
        "trOnlyTokenIds": sorted(tr_only, key=lambda token_id: position[token_id]),
        "sentences": candidates,
    }
    validate_candidate(output)
    return output

