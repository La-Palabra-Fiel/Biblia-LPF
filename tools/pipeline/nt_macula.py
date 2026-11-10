"""Closed-list MACULA Greek structural source and TR1894 mapping gate."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import unicodedata
import xml.etree.ElementTree as ET
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
    exact_groups = hold_groups = human_groups = 0
    mapped_words = human_words = unmatched_words = 0

    def walk(node: dict) -> tuple[bool, bool, set[str]]:
        nonlocal exact_groups, hold_groups, human_groups
        nonlocal mapped_words, human_words, unmatched_words
        kind = node.get("kind")
        if kind == "word":
            mapped_words += 1
            token_id = node.get("trTokenId")
            if not token_id:
                raise ValueError("mapped candidate word lacks TR token identity")
            mapped_ids.append(token_id)
            return True, True, set()
        if kind == "tr-word":
            human_words += 1
            token_id = node.get("trTokenId")
            decision_id = node.get("decisionId")
            if (
                node.get("status") != "human-adjudicated-tr"
                or not token_id
                or not decision_id
                or node.get("maculaTerminalId")
            ):
                raise ValueError("native TR candidate word lacks adjudication provenance")
            mapped_ids.append(token_id)
            return True, False, {decision_id}
        if kind == "reference-word":
            unmatched_words += 1
            if node.get("status") != "hold-token-disagreement" or node.get("trTokenId"):
                raise ValueError("unmatched MACULA terminal is not isolated as HOLD")
            return False, False, set()
        if kind != "group" or not node.get("children"):
            raise ValueError("candidate structural group is empty or malformed")
        child_results = [walk(child) for child in node["children"]]
        children_resolved = all(row[0] for row in child_results)
        children_exact = all(row[1] for row in child_results)
        child_decisions = set().union(*(row[2] for row in child_results))
        if node.get("status") == "exact-candidate":
            exact_groups += 1
            if not children_resolved or not children_exact:
                raise ValueError("exact structural candidate contains a HOLD child")
            return True, True, set()
        if node.get("status") == "human-adjudicated-tr":
            human_groups += 1
            decisions = set(node.get("decisionIds") or [])
            if not children_resolved or not decisions or decisions != child_decisions:
                raise ValueError("human-adjudicated TR group lacks complete decision provenance")
            return True, False, decisions
        if node.get("status") != "hold-token-disagreement":
            raise ValueError("candidate group has an unknown review status")
        hold_groups += 1
        return False, False, child_decisions

    for sentence in candidate.get("sentences") or []:
        for root in sentence.get("roots") or []:
            walk(root)
    if len(mapped_ids) != len(set(mapped_ids)):
        raise ValueError("a TR token appears more than once in the MACULA candidate")
    if set(mapped_ids) & set(candidate.get("trOnlyTokenIds") or []):
        raise ValueError("a TR-only token also appears as a mapped MACULA anchor")
    expected = candidate.get("summary") or {}
    actual = {
        "exactGroups": exact_groups,
        "holdGroups": hold_groups,
        "humanAdjudicatedGroups": human_groups,
        "mappedWords": mapped_words,
        "humanAdjudicatedWords": human_words,
        "unmatchedMaculaWords": unmatched_words,
        "trOnlyTokens": len(candidate.get("trOnlyTokenIds") or []),
    }
    if any(expected.get(key) != value for key, value in actual.items()):
        raise ValueError(f"candidate summary differs from tree counts: {actual}")


def apply_structure_adjudications(candidate: dict, adjudications: dict) -> dict:
    """Overlay explicit human TR-native branches without inventing MACULA links."""
    if adjudications.get("schema") != STRUCTURE_ADJUDICATION_SCHEMA:
        raise ValueError("noncanonical NT structure adjudication schema")
    nodes: dict[str, dict] = {}
    reference_words: dict[str, dict] = {}

    def index(node: dict) -> None:
        node_id = node.get("candidateNodeId")
        if node_id:
            if node_id in nodes:
                raise ValueError(f"duplicate candidate node id: {node_id}")
            nodes[node_id] = node
        terminal_id = node.get("maculaTerminalId")
        if node.get("kind") == "reference-word" and terminal_id:
            if terminal_id in reference_words:
                raise ValueError(f"duplicate unmatched MACULA terminal id: {terminal_id}")
            reference_words[terminal_id] = node
        for child in node.get("children") or []:
            index(child)

    for sentence in candidate.get("sentences") or []:
        for root in sentence.get("roots") or []:
            index(root)

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
        common_valid = (
            bool(decision_id)
            and bool(decision.get("reviewer"))
            and bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(decision.get("date") or "")))
            and bool(token_ids)
            and len(token_ids) == len(set(token_ids))
            and all(token_id.startswith(f"{decision.get('reference')}.") for token_id in token_ids)
        )
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

    def propagate(node: dict) -> tuple[bool, set[str]]:
        if node.get("kind") == "reference-word":
            return False, set()
        if node.get("kind") == "tr-word":
            return True, {node["decisionId"]}
        if node.get("kind") == "word":
            return True, set()
        child_rows = [propagate(child) for child in node.get("children") or []]
        resolved = all(row[0] for row in child_rows)
        decisions = set().union(*(row[1] for row in child_rows))
        if node.get("status") == "hold-token-disagreement" and resolved and decisions:
            node["status"] = "human-adjudicated-tr"
            node["decisionIds"] = sorted(decisions)
        return resolved, decisions

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

    counts = {
        "exactGroups": 0,
        "holdGroups": 0,
        "humanAdjudicatedGroups": 0,
        "mappedWords": 0,
        "humanAdjudicatedWords": 0,
        "unmatchedMaculaWords": 0,
    }

    def recount(node: dict) -> None:
        kind = node.get("kind")
        if kind == "word":
            counts["mappedWords"] += 1
        elif kind == "tr-word":
            counts["humanAdjudicatedWords"] += 1
        elif kind == "reference-word":
            counts["unmatchedMaculaWords"] += 1
        elif kind == "group":
            key = {
                "exact-candidate": "exactGroups",
                "hold-token-disagreement": "holdGroups",
                "human-adjudicated-tr": "humanAdjudicatedGroups",
            }[node["status"]]
            counts[key] += 1
        for child in node.get("children") or []:
            recount(child)

    for sentence in candidate.get("sentences") or []:
        for root in sentence.get("roots") or []:
            recount(root)
    candidate["summary"] = {**counts, "trOnlyTokens": len(candidate["trOnlyTokenIds"])}
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

