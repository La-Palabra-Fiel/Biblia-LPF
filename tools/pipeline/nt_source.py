"""Canonical TR1894 tokens with Robinson morphology and Scrivener checking.

The pinned Robinson UTR files are the working TR1894 source named by
SOURCE_POLICY.md.  Their beta-code surface owns the token boundary and their
Robinson record supplies morphology.  The independent Scrivener SCV files
must reproduce the same verse sequence.  A mismatch is returned as HOLD; this
module never repairs or silently chooses a reading.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from books import NT, ROOT, Book

TR_ROOT = ROOT / "source" / "greek" / "TR1894"
TR_TEXT = TR_ROOT / "tr1894.txt"
ROBINSON_ROOT = TR_ROOT / "robinson-parsed"
SCRIVENER_ROOT = TR_ROOT / "scrivener-textonly"
ROBINSON_COMMIT = "7fd4d02c3e5adebd379ebfbc824040820dde10fc"
SCRIVENER_COMMIT = "6049a43b135ed870f843b83eb6a04764fc796678"
TOKENIZATION_POLICY = "robinson-utr-beta-tokens-v1"
RECONCILIATION_POLICY = "robinson-utr-scrivener-scv-whole-verse-v1"
MANIFEST_PATH = TR_ROOT / "MANIFEST.json"
LEDGER_PATH = TR_ROOT / "tr1894-robinson-reconciliation.json"
REVIEW_PATH = TR_ROOT / "REVIEW.md"
ADJUDICATIONS_PATH = TR_ROOT / "ADJUDICATIONS.json"

TR_CODE_BY_STEM = {
    "MT": "MAT", "MR": "MRK", "LU": "LUK", "JOH": "JHN", "AC": "ACT",
    "RO": "ROM", "1CO": "1CO", "2CO": "2CO", "GA": "GAL", "EPH": "EPH",
    "PHP": "PHP", "COL": "COL", "1TH": "1TH", "2TH": "2TH", "1TI": "1TI",
    "2TI": "2TI", "TIT": "TIT", "PHM": "PHM", "HEB": "HEB", "JAS": "JAS",
    "1PE": "1PE", "2PE": "2PE", "1JO": "1JN", "2JO": "2JN", "3JO": "3JN",
    "JUDE": "JUD", "RE": "REV",
}
BOOK_BY_TR_CODE = {TR_CODE_BY_STEM[book.utr_stem]: book for book in NT}

VERSE_START = re.compile(r"^(\d+):(\d+)\s+(.*)$")
UTR_TOKEN = re.compile(r"([^{}]*?)\{([^}]+)\}")
TRAILING_PUNCTUATION = re.compile(r"([,.;·:!?]+)$")

GREEK_TO_BETA = {
    "α": "a", "β": "b", "γ": "g", "δ": "d", "ε": "e", "ζ": "z",
    "η": "h", "θ": "q", "ι": "i", "κ": "k", "λ": "l", "μ": "m",
    "ν": "n", "ξ": "x", "ο": "o", "π": "p", "ρ": "r", "σ": "s",
    "ς": "s", "τ": "t", "υ": "u", "φ": "f", "χ": "c", "ψ": "y",
    "ω": "w",
}


@dataclass(frozen=True)
class RobinsonToken:
    ordinal: int
    surface_beta: str
    strongs: tuple[int, ...]
    raw_tag: str


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_beta(value: str) -> str:
    """Normalize beta-code spelling without changing or selecting a reading."""
    return "".join(
        "s" if char == "v" else char
        for char in value.lower()
        if "a" <= char <= "z"
    )


def _canonical_scrivener_beta(value: str) -> str:
    """Convert SCV's theta/psi letters to the UTR beta-code convention."""
    translated = value.lower().translate(str.maketrans({"y": "q", "q": "y"}))
    return _canonical_beta(translated)


def greek_to_canonical_beta(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.lower())
    return "".join(
        GREEK_TO_BETA[char]
        for char in decomposed
        if char in GREEK_TO_BETA
    )


def tokenize_tr_verse(reference: str, text: str) -> list[dict]:
    """Tokenize the legacy Unicode display text reversibly (not authority)."""
    pieces = re.findall(r"\S+\s*", text)
    tokens: list[dict] = []
    for ordinal, piece in enumerate(pieces, start=1):
        whitespace = re.search(r"\s*$", piece).group(0)
        compact = piece[: len(piece) - len(whitespace)] if whitespace else piece
        punctuation_match = TRAILING_PUNCTUATION.search(compact)
        punctuation = punctuation_match.group(1) if punctuation_match else ""
        surface = compact[: -len(punctuation)] if punctuation else compact
        if not surface:
            raise ValueError(f"{reference}: punctuation-only source token")
        tokens.append({
            "tokenId": f"{reference}.w{ordinal:03d}",
            "reference": reference,
            "ordinal": ordinal,
            "surface": surface,
            "after": punctuation + whitespace,
            "sourceLocator": f"source/greek/TR1894/tr1894.txt:{reference}:{ordinal}",
        })
    reconstructed = "".join(token["surface"] + token["after"] for token in tokens)
    if reconstructed != text:
        raise ValueError(f"{reference}: TR tokenization is not reversible")
    return tokens


def _parse_utr_body(body: str) -> list[RobinsonToken]:
    tokens: list[RobinsonToken] = []
    for chunk, raw_tag in UTR_TOKEN.findall(body):
        fields = chunk.replace("|", " ").split()
        surfaces = [
            field.strip("[]")
            for field in fields
            if not field.isdigit() and not re.fullmatch(r"\(\d+:\d+\)", field)
        ]
        # Robinson UTR may append a numeric parsing code after the lexical
        # Strong number (G5627-G5799).  The raw Robinson tag below is the
        # morphology authority; parsing and synonym codes are not lexemes and
        # must never leak into lexical evidence as extra Strong identifiers.
        strongs = tuple(
            number
            for field in fields
            if field.isdigit() and (number := int(field)) > 0
            if not 5627 <= number <= 5893
        )
        if not surfaces:
            continue
        tokens.append(RobinsonToken(len(tokens) + 1, surfaces[0], strongs, raw_tag))
    return tokens


def beta_to_unicode(value: str) -> str:
    letters = {
        "a": "α", "b": "β", "g": "γ", "d": "δ", "e": "ε", "z": "ζ",
        "h": "η", "q": "θ", "i": "ι", "k": "κ", "l": "λ", "m": "μ",
        "n": "ν", "c": "χ", "o": "ο", "p": "π", "r": "ρ", "s": "σ",
        "v": "ς", "t": "τ", "u": "υ", "f": "φ", "x": "ξ", "y": "ψ",
        "w": "ω",
    }
    output = []
    for index, char in enumerate(value.lower()):
        if char == "s":
            next_char = value[index + 1].lower() if index + 1 < len(value) else ""
            output.append("σ" if next_char in letters else "ς")
        else:
            output.append(letters.get(char, char))
    return "".join(output)


def scv_beta_to_unicode(value: str) -> str:
    """Render SCV beta code after converting its theta/psi convention."""
    return beta_to_unicode(value.lower().translate(str.maketrans({"y": "q", "q": "y"})))


@lru_cache(maxsize=None)
def load_robinson_book(book: Book) -> dict[str, list[RobinsonToken]]:
    path = book.utr_path
    if not path.is_file():
        raise FileNotFoundError(f"Robinson source missing: {path}")
    tr_code = TR_CODE_BY_STEM[book.utr_stem]
    records: dict[str, list[str]] = {}
    current: str | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        match = VERSE_START.match(line)
        if match:
            current = f"{tr_code}.{int(match.group(1))}.{int(match.group(2))}"
            if current in records:
                raise ValueError(f"duplicate Robinson verse {current}")
            records[current] = [match.group(3)]
        elif current is not None and line.strip():
            records[current].append(line.strip())
    return {reference: _parse_utr_body(" ".join(lines)) for reference, lines in records.items()}


@lru_cache(maxsize=None)
def load_scrivener_book(book: Book) -> dict[str, list[str]]:
    path = SCRIVENER_ROOT / f"{book.utr_stem}.SCV"
    if not path.is_file():
        raise FileNotFoundError(f"Scrivener check source missing: {path}")
    tr_code = TR_CODE_BY_STEM[book.utr_stem]
    records: dict[str, list[str]] = {}
    current: str | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\s*(\d+):(\d+)\s+(.*)$", line)
        if match:
            current = f"{tr_code}.{int(match.group(1))}.{int(match.group(2))}"
            if current in records:
                raise ValueError(f"duplicate Scrivener verse {current}")
            records[current] = [match.group(3)]
        elif current is not None and line.strip():
            records[current].append(line.strip())
    output: dict[str, list[str]] = {}
    for reference, lines in records.items():
        body = re.sub(r"\[[^]]*\]", " ", " ".join(lines))
        output[reference] = [field for field in body.split() if field]
    return output


def _unique_subsequence_positions(needle: list[str], haystack: list[str]) -> list[int] | None:
    """Return the only ordered embedding, or None when absent/ambiguous."""
    @lru_cache(maxsize=None)
    def count(i: int, j: int) -> int:
        if i == len(needle):
            return 1
        if j == len(haystack):
            return 0
        total = count(i, j + 1)
        if needle[i] == haystack[j]:
            total += count(i + 1, j + 1)
        return min(total, 2)

    if count(0, 0) != 1:
        return None
    positions: list[int] = []
    i = j = 0
    while i < len(needle):
        skip_count = count(i, j + 1) if j < len(haystack) else 0
        take_count = (
            count(i + 1, j + 1)
            if j < len(haystack) and needle[i] == haystack[j]
            else 0
        )
        if take_count == 1 and skip_count == 0:
            positions.append(j)
            i += 1
            j += 1
        else:
            j += 1
    return positions


def _equivalent_morph_subsequence_positions(
    needle: list[str], haystack: list[str], robinson: list[RobinsonToken]
) -> list[int] | None:
    """Choose the earliest embedding only when every ambiguity has same morph."""
    possible: list[list[int]] = []

    def is_subsequence(left: list[str], right: list[str]) -> bool:
        iterator = iter(right)
        return all(any(candidate == item for candidate in iterator) for item in left)

    for index, value in enumerate(needle):
        positions = [
            source_index
            for source_index, source_value in enumerate(haystack)
            if value == source_value
            and is_subsequence(needle[:index], haystack[:source_index])
            and is_subsequence(needle[index + 1 :], haystack[source_index + 1 :])
        ]
        if not positions:
            return None
        signatures = {
            (robinson[position].raw_tag, robinson[position].strongs)
            for position in positions
        }
        if len(signatures) != 1:
            return None
        possible.append(positions)

    selected: list[int] = []
    cursor = 0
    for positions in possible:
        choice = next((position for position in positions if position >= cursor), None)
        if choice is None:
            return None
        selected.append(choice)
        cursor = choice + 1
    return selected


def reconcile_verse(reference: str, scrivener: list[str], robinson: list[RobinsonToken]) -> dict:
    tr_tokens = []
    for token in robinson:
        tr_tokens.append({
            "tokenId": f"{reference}.w{token.ordinal:03d}",
            "reference": reference,
            "ordinal": token.ordinal,
            "surfaceBeta": token.surface_beta,
            "surfaceGreek": beta_to_unicode(token.surface_beta),
            "sourceLocator": (
                f"source/greek/TR1894/robinson-parsed/"
                f"{BOOK_BY_TR_CODE[reference.split('.')[0]].utr_stem}.UTR:{reference}:{token.ordinal}"
            ),
            "morphology": {
                "provider": "Robinson",
                "providerRevision": ROBINSON_COMMIT,
                "sourceOrdinal": token.ordinal,
                "sourceSurfaceBeta": token.surface_beta,
                "strongs": list(token.strongs),
                "rawTag": token.raw_tag,
            },
        })
    tr_normalized = [_canonical_beta(token.surface_beta) for token in robinson]
    scrivener_normalized = [_canonical_scrivener_beta(token) for token in scrivener]
    robinson_normalized = [_canonical_beta(token.surface_beta) for token in robinson]
    exact = bool(tr_tokens) and scrivener_normalized == robinson_normalized
    proposed_positions = (
        None
        if exact
        else _unique_subsequence_positions(scrivener_normalized, robinson_normalized)
    )
    policy_positions = (
        None
        if exact or proposed_positions is not None
        else _equivalent_morph_subsequence_positions(
            scrivener_normalized, robinson_normalized, robinson
        )
    )
    status = (
        "exact"
        if exact
        else "review-variant-path"
        if proposed_positions is not None
        else "policy-scv-subsequence"
        if policy_positions is not None
        else "hold"
    )
    if policy_positions is not None:
        selected_tokens = [tr_tokens[position] for position in policy_positions]
        for new_ordinal, (scv_surface, token) in enumerate(
            zip(scrivener, selected_tokens, strict=True), start=1
        ):
            token["upstreamTokenId"] = token["tokenId"]
            token["tokenId"] = f"{reference}.w{new_ordinal:03d}"
            token["ordinal"] = new_ordinal
            token["upstreamSurfaceBeta"] = token["surfaceBeta"]
            token["surfaceBeta"] = scv_surface
            token["surfaceGreek"] = scv_beta_to_unicode(scv_surface)
            token["morphology"]["reconciliation"] = "policy-scv-authoritative-subsequence"
        tr_tokens = selected_tokens
    paired_differences = None
    if status == "hold" and len(scrivener) == len(robinson):
        paired_differences = [
            {
                "ordinal": index,
                "scrivenerBeta": scv,
                "robinsonBeta": utr.surface_beta,
            }
            for index, (scv, utr) in enumerate(zip(scrivener, robinson, strict=True), start=1)
            if _canonical_scrivener_beta(scv) != _canonical_beta(utr.surface_beta)
        ]
    if exact:
        for scv_surface, token in zip(scrivener, tr_tokens, strict=True):
            token["upstreamSurfaceBeta"] = token["surfaceBeta"]
            token["surfaceBeta"] = scv_surface
            token["surfaceGreek"] = scv_beta_to_unicode(scv_surface)
            token["morphology"]["reconciliation"] = "scrivener-scv-whole-verse-exact"
    return {
        "reference": reference,
        "status": status,
        "reason": (
            None
            if exact
            else "SCV has one ordered path through UTR variant tokens; human approval required"
            if proposed_positions is not None
            else None
            if policy_positions is not None
            else "Robinson UTR and Scrivener SCV normalized token sequences differ"
        ),
        "trTokens": tr_tokens,
        "scrivenerTokens": scrivener if not exact else None,
        "robinsonTokens": [
            {
                "ordinal": token.ordinal,
                "surfaceBeta": token.surface_beta,
                "strongs": list(token.strongs),
                "rawTag": token.raw_tag,
            }
            for token in robinson
        ] if not exact else None,
        "proposedRobinsonOrdinals": (
            [position + 1 for position in proposed_positions]
            if proposed_positions is not None
            else None
        ),
        "omittedRobinsonTokens": (
            [
                {
                    "ordinal": token.ordinal,
                    "surfaceBeta": token.surface_beta,
                    "strongs": list(token.strongs),
                    "rawTag": token.raw_tag,
                }
                for index, token in enumerate(robinson)
                if index not in set(proposed_positions)
            ]
            if proposed_positions is not None
            else None
        ),
        "pairedDifferences": paired_differences,
        "policySelectedRobinsonOrdinals": (
            [position + 1 for position in policy_positions]
            if policy_positions is not None
            else None
        ),
    }


@lru_cache(maxsize=1)
def load_adjudication_document() -> dict:
    data = json.loads(ADJUDICATIONS_PATH.read_text(encoding="utf-8"))
    if data.get("schema") != "tr1894-robinson-adjudications-v1":
        raise ValueError("noncanonical TR1894 + Robinson adjudication file")
    return data


@lru_cache(maxsize=1)
def load_adjudications() -> dict[str, dict]:
    data = load_adjudication_document()
    decisions: dict[str, dict] = {}
    for decision in data.get("decisions") or []:
        reference = decision.get("reference")
        if not reference or reference in decisions:
            raise ValueError("adjudication references must be present and unique")
        if (
            decision.get("decision") not in {
                "accept-unique-variant-path",
                "accept-scv-surface-robinson-morphology",
                "accept-scv-subsequence-morphology",
                "accept-scv-token-merge-robinson-morphology",
            }
            or not decision.get("reviewer")
            or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(decision.get("date") or ""))
        ):
            raise ValueError(f"{reference}: invalid human adjudication")
        decisions[reference] = decision
    return decisions


@lru_cache(maxsize=1)
def load_boundary_adjudications() -> dict[str, dict]:
    by_reference: dict[str, dict] = {}
    for decision in load_adjudication_document().get("boundaryDecisions") or []:
        references = decision.get("references")
        if (
            decision.get("decision") != "accept-scv-verse-boundary"
            or not isinstance(references, list)
            or len(references) < 2
            or not decision.get("reviewer")
            or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(decision.get("date") or ""))
        ):
            raise ValueError("invalid verse-boundary adjudication")
        for reference in references:
            if reference in by_reference:
                raise ValueError(f"duplicate verse-boundary adjudication for {reference}")
            by_reference[reference] = decision
    return by_reference


def reconcile_boundary_group(book: Book, decision: dict) -> dict[str, dict]:
    references = decision["references"]
    robinson_by_ref = load_robinson_book(book)
    scrivener_by_ref = load_scrivener_book(book)
    source_rows = [
        (reference, token)
        for reference in references
        for token in robinson_by_ref[reference]
    ]
    scv_rows = [
        (reference, surface)
        for reference in references
        for surface in scrivener_by_ref[reference]
    ]
    if [
        _canonical_beta(token.surface_beta) for _, token in source_rows
    ] != [
        _canonical_scrivener_beta(surface) for _, surface in scv_rows
    ]:
        raise ValueError("approved SCV verse-boundary group no longer reconstructs UTR")

    results: dict[str, dict] = {}
    offset = 0
    for reference in references:
        surfaces = scrivener_by_ref[reference]
        selected = source_rows[offset : offset + len(surfaces)]
        offset += len(surfaces)
        tokens = []
        for ordinal, (scv_surface, (source_reference, source_token)) in enumerate(
            zip(surfaces, selected, strict=True), start=1
        ):
            tokens.append({
                "tokenId": f"{reference}.w{ordinal:03d}",
                "reference": reference,
                "ordinal": ordinal,
                "surfaceBeta": scv_surface,
                "surfaceGreek": scv_beta_to_unicode(scv_surface),
                "sourceLocator": (
                    f"source/greek/TR1894/scrivener-textonly/{book.utr_stem}.SCV:"
                    f"{reference}:{ordinal}"
                ),
                "morphology": {
                    "provider": "Robinson",
                    "providerRevision": ROBINSON_COMMIT,
                    "sourceReference": source_reference,
                    "sourceOrdinal": source_token.ordinal,
                    "sourceSurfaceBeta": source_token.surface_beta,
                    "strongs": list(source_token.strongs),
                    "rawTag": source_token.raw_tag,
                    "reconciliation": "human-approved-scv-verse-boundary",
                },
            })
        results[reference] = {
            "reference": reference,
            "status": "human-approved-verse-boundary",
            "reason": None,
            "trTokens": tokens,
            "adjudication": decision,
        }
    if offset != len(source_rows):
        raise ValueError("approved SCV verse-boundary group leaves UTR tokens unbound")
    return results


def apply_adjudication(result: dict) -> dict:
    decision = load_adjudications().get(result["reference"])
    if decision is None:
        return result
    if decision["decision"] == "accept-scv-token-merge-robinson-morphology":
        if result["status"] != "hold":
            raise ValueError(f"{result['reference']}: token-merge adjudication no longer matches HOLD")
        merge = decision.get("merge") or {}
        scv_ordinal = merge.get("scvOrdinal")
        source_ordinals = merge.get("sourceOrdinals") or []
        scv_tokens = result.get("scrivenerTokens") or []
        source_tokens = result["trTokens"]
        if (
            not isinstance(scv_ordinal, int)
            or not source_ordinals
            or len(source_tokens) - len(source_ordinals) + 1 != len(scv_tokens)
            or source_ordinals != list(range(source_ordinals[0], source_ordinals[-1] + 1))
        ):
            raise ValueError(f"{result['reference']}: invalid approved token merge")
        selected: list[dict] = []
        source_index = 0
        for ordinal, scv_surface in enumerate(scv_tokens, start=1):
            if ordinal == scv_ordinal:
                consumed = source_tokens[source_index : source_index + len(source_ordinals)]
                if [token["ordinal"] for token in consumed] != source_ordinals:
                    raise ValueError(f"{result['reference']}: approved merge source positions changed")
                token = {
                    "tokenId": f"{result['reference']}.w{ordinal:03d}",
                    "reference": result["reference"],
                    "ordinal": ordinal,
                    "surfaceBeta": scv_surface,
                    "surfaceGreek": merge["surfaceGreek"],
                    "sourceLocator": f"human-adjudication:{result['reference']}:{ordinal}",
                    "morphology": {
                        "provider": "Robinson-corpus",
                        "providerRevision": ROBINSON_COMMIT,
                        "sourceReferences": merge["morphologyEvidenceReferences"],
                        "sourceOrdinals": source_ordinals,
                        "sourceSurfaceBeta": "+".join(token["surfaceBeta"] for token in consumed),
                        "strongs": merge["strongs"],
                        "rawTag": merge["rawTag"],
                        "reconciliation": "human-approved-scv-token-merge",
                    },
                }
                selected.append(token)
                source_index += len(source_ordinals)
                continue
            token = source_tokens[source_index]
            if _canonical_beta(token["surfaceBeta"]) != _canonical_scrivener_beta(scv_surface):
                raise ValueError(f"{result['reference']}: non-merged token path changed")
            token["tokenId"] = f"{result['reference']}.w{ordinal:03d}"
            token["ordinal"] = ordinal
            token["surfaceBeta"] = scv_surface
            token["surfaceGreek"] = scv_beta_to_unicode(scv_surface)
            token["morphology"]["reconciliation"] = "human-approved-around-scv-token-merge"
            selected.append(token)
            source_index += 1
        if source_index != len(source_tokens):
            raise ValueError(f"{result['reference']}: approved token merge leaves source tokens")
        return {
            **result,
            "status": "human-approved-morphology-merge",
            "reason": None,
            "trTokens": selected,
            "adjudication": decision,
        }
    if decision["decision"] == "accept-scv-subsequence-morphology":
        if result["status"] != "hold":
            raise ValueError(f"{result['reference']}: morphology adjudication no longer matches HOLD")
        selected_ordinals = decision.get("selectedRobinsonOrdinals") or []
        selected = [
            result["trTokens"][ordinal - 1]
            for ordinal in selected_ordinals
            if isinstance(ordinal, int) and 1 <= ordinal <= len(result["trTokens"])
        ]
        scv_tokens = result.get("scrivenerTokens") or []
        approved_surface_pairs = {
            row["scvOrdinal"]: row
            for row in (decision.get("surfacePairs") or [])
        }
        surface_matches = True
        for ordinal, (token, scv_surface) in enumerate(
            zip(selected, scv_tokens), start=1
        ):
            if _canonical_beta(token["surfaceBeta"]) == _canonical_scrivener_beta(scv_surface):
                continue
            approved = approved_surface_pairs.get(ordinal)
            if not approved or (
                approved.get("scv") != scv_surface
                or approved.get("utr") != token["surfaceBeta"]
            ):
                surface_matches = False
                break
        if (
            len(selected) != len(selected_ordinals)
            or len(selected) != len(scv_tokens)
            or not surface_matches
        ):
            raise ValueError(f"{result['reference']}: approved morphology path changed")
        for new_ordinal, (scv_surface, token) in enumerate(
            zip(scv_tokens, selected, strict=True), start=1
        ):
            token["upstreamTokenId"] = token["tokenId"]
            token["tokenId"] = f"{result['reference']}.w{new_ordinal:03d}"
            token["ordinal"] = new_ordinal
            token["upstreamSurfaceBeta"] = token["surfaceBeta"]
            token["surfaceBeta"] = scv_surface
            approved_surface = approved_surface_pairs.get(new_ordinal) or {}
            token["surfaceGreek"] = approved_surface.get(
                "surfaceGreek", scv_beta_to_unicode(scv_surface)
            )
            token["morphology"]["reconciliation"] = "human-approved-scv-morphology-path"
        return {
            **result,
            "status": "human-approved-morphology-path",
            "reason": None,
            "trTokens": selected,
            "adjudication": decision,
        }
    if decision["decision"] == "accept-scv-surface-robinson-morphology":
        differences = result.get("pairedDifferences")
        if result["status"] != "hold" or not differences:
            raise ValueError(f"{result['reference']}: SCV surface adjudication no longer matches")
        scv_tokens = result["scrivenerTokens"]
        if len(scv_tokens) != len(result["trTokens"]):
            raise ValueError(f"{result['reference']}: SCV surface adjudication is not one-to-one")
        expected_pairs = decision.get("surfacePairs")
        actual_pairs = [
            {
                "ordinal": row["ordinal"],
                "scv": row["scrivenerBeta"],
                "utr": row["robinsonBeta"],
            }
            for row in differences
        ]
        expected_core = [
            {key: row.get(key) for key in ("ordinal", "scv", "utr")}
            for row in (expected_pairs or [])
        ]
        if expected_core != actual_pairs:
            raise ValueError(f"{result['reference']}: approved SCV/UTR forms changed")
        greek_overrides = {
            row["ordinal"]: row["surfaceGreek"]
            for row in (expected_pairs or [])
            if row.get("surfaceGreek")
        }
        approved_tokens = result["trTokens"]
        for scv_surface, token in zip(scv_tokens, approved_tokens, strict=True):
            token["upstreamSurfaceBeta"] = token["surfaceBeta"]
            token["surfaceBeta"] = scv_surface
            token["surfaceGreek"] = greek_overrides.get(
                token["ordinal"], scv_beta_to_unicode(scv_surface)
            )
            token["textSourceLocator"] = (
                f"source/greek/TR1894/scrivener-textonly/"
                f"{BOOK_BY_TR_CODE[result['reference'].split('.')[0]].utr_stem}.SCV:"
                f"{result['reference']}:{token['ordinal']}"
            )
            token["morphology"]["reconciliation"] = "human-approved-scv-surface"
        return {
            **result,
            "status": "human-approved-scv-surface",
            "reason": None,
            "trTokens": approved_tokens,
            "adjudication": decision,
        }
    if result["status"] != "review-variant-path":
        raise ValueError(f"{result['reference']}: adjudication no longer matches a unique variant path")
    selected = set(result["proposedRobinsonOrdinals"])
    approved_tokens = [
        token for token in result["trTokens"] if token["ordinal"] in selected
    ]
    scv_tokens = result.get("scrivenerTokens") or []
    if len(scv_tokens) != len(approved_tokens):
        raise ValueError(f"{result['reference']}: approved variant path no longer matches SCV")
    for new_ordinal, (scv_surface, token) in enumerate(
        zip(scv_tokens, approved_tokens, strict=True), start=1
    ):
        token["upstreamTokenId"] = token["tokenId"]
        token["tokenId"] = f"{result['reference']}.w{new_ordinal:03d}"
        token["ordinal"] = new_ordinal
        token["upstreamSurfaceBeta"] = token["surfaceBeta"]
        token["surfaceBeta"] = scv_surface
        token["surfaceGreek"] = scv_beta_to_unicode(scv_surface)
        token["morphology"]["reconciliation"] = "human-approved-unique-variant-path"
    return {
        **result,
        "status": "human-approved-variant-path",
        "reason": None,
        "trTokens": approved_tokens,
        "adjudication": decision,
    }


def load_reconciled_verse(book: Book, chapter: int, verse: int) -> dict:
    tr_code = TR_CODE_BY_STEM[book.utr_stem]
    reference = f"{tr_code}.{chapter}.{verse}"
    boundary = load_boundary_adjudications().get(reference)
    if boundary is not None:
        return reconcile_boundary_group(book, boundary)[reference]
    robinson = load_robinson_book(book)
    scrivener = load_scrivener_book(book)
    if reference not in robinson:
        raise KeyError(f"{reference} not in Robinson morphology")
    if reference not in scrivener:
        raise KeyError(f"{reference} not in Scrivener text check")
    return apply_adjudication(
        reconcile_verse(reference, scrivener[reference], robinson[reference])
    )


@lru_cache(maxsize=1)
def validate_manifest() -> dict:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if manifest.get("schema") != "tr1894-robinson-source-manifest-v1":
        raise ValueError("noncanonical TR1894 + Robinson manifest")
    generator = manifest.get("generator") or {}
    generator_path = ROOT / str(generator.get("path") or "")
    if (
        generator.get("version") != 1
        or generator.get("command") != "python3 tools/build_nt_source.py"
        or not generator_path.is_file()
        or sha256(generator_path) != generator.get("sha256")
    ):
        raise ValueError("TR1894 + Robinson manifest generator is stale")
    morphology = manifest.get("morphology") or {}
    verification = manifest.get("textVerification") or {}
    if morphology.get("revision") != ROBINSON_COMMIT:
        raise ValueError("Robinson manifest revision is not pinned policy revision")
    if verification.get("revision") != SCRIVENER_COMMIT:
        raise ValueError("Scrivener manifest revision is not pinned policy revision")
    for group in (morphology, verification):
        for record in group.get("files") or []:
            path = ROOT / record["path"]
            if not path.is_file() or sha256(path) != record.get("sha256"):
                raise ValueError(f"source manifest checksum mismatch: {record['path']}")
    reconciliation = manifest.get("reconciliation") or {}
    if (
        reconciliation.get("path") != str(LEDGER_PATH.relative_to(ROOT))
        or reconciliation.get("policy") != RECONCILIATION_POLICY
        or sha256(LEDGER_PATH) != reconciliation.get("sha256")
    ):
        raise ValueError("TR1894 + Robinson reconciliation ledger is stale")
    review = manifest.get("humanReviewQueue") or {}
    if (
        review.get("path") != str(REVIEW_PATH.relative_to(ROOT))
        or not REVIEW_PATH.is_file()
        or sha256(REVIEW_PATH) != review.get("sha256")
    ):
        raise ValueError("TR1894 + Robinson review queue is stale")
    adjudications = manifest.get("humanAdjudications") or {}
    if (
        adjudications.get("path") != str(ADJUDICATIONS_PATH.relative_to(ROOT))
        or not ADJUDICATIONS_PATH.is_file()
        or sha256(ADJUDICATIONS_PATH) != adjudications.get("sha256")
    ):
        raise ValueError("TR1894 + Robinson adjudications are stale")
    load_adjudications()
    load_boundary_adjudications()
    return manifest

