#!/usr/bin/env python3
"""Rebuild and validate one scoped, noncanonical TR1894/MACULA proposal."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "pipeline"))

from books import get_book  # noqa: E402
from nt_source import load_reconciled_verse  # noqa: E402
from nt_macula import (  # noqa: E402
    TR_CODE_BY_STEM,
    apply_structure_adjudications,
    apply_tr_authority_adaptations,
    apply_tr_authority_fallbacks,
    mapping_sha256,
    project_chapter_candidate,
    validate_candidate,
    validate_mapping_ledger,
)

MAPPING = ROOT / "source" / "greek" / "TR1894" / "macula-structure-mapping.json"
MANIFEST = ROOT / "source" / "greek" / "TR1894" / "MACULA_GREEK_MANIFEST.json"


def walk_nodes(candidate: dict):
    def walk(node: dict):
        yield node
        for child in node.get("children") or []:
            yield from walk(child)

    for sentence in candidate.get("sentences") or []:
        for root in sentence.get("roots") or []:
            yield from walk(root)


def approval_binding_sha256(proposal: dict) -> str:
    attachments = []
    for attachment in proposal.get("attachments") or []:
        bound = dict(attachment)
        bound.pop("reviewStatus", None)
        attachments.append(bound)
    payload = {
        key: proposal[key]
        for key in ("schema", "authority", "scope", "pinnedInputs")
    }
    payload["attachments"] = attachments
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("proposal", type=Path)
    parser.add_argument(
        "--write-candidate",
        type=Path,
        help="Optional disposable output path for inspecting the rebuilt candidate.",
    )
    args = parser.parse_args()

    proposal_path = args.proposal.resolve()
    proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
    if proposal.get("schema") != "tr1894-macula-attachment-proposal-v1":
        raise ValueError("proposal is not TR1894-first attachment data")
    if proposal.get("status") not in {
        "proposal-not-approved", "human-approved-noncanonical"
    }:
        raise ValueError("proposal has an unknown approval state")
    scope = proposal.get("scope") or {}
    book = get_book(scope.get("book") or "")
    chapter = int(scope.get("chapter") or 0)
    verse_start = int(scope.get("verseStart") or 0)
    verse_end = int(scope.get("verseEnd") or 0)
    if book.testament != "nt" or chapter < 1 or not (1 <= verse_start <= verse_end):
        raise ValueError("proposal scope is invalid")

    reference_code = TR_CODE_BY_STEM[book.utr_stem]
    expected_references = {
        f"{reference_code}.{chapter}.{verse}"
        for verse in range(verse_start, verse_end + 1)
    }
    expected_prefixes = tuple(f"{reference}." for reference in expected_references)
    authoritative_tokens = [
        token
        for verse in range(verse_start, verse_end + 1)
        for token in load_reconciled_verse(book, chapter, verse)["trTokens"]
    ]
    authoritative_rows = [
        {"tokenId": token["tokenId"], "surfaceBeta": token["surfaceBeta"]}
        for token in authoritative_tokens
    ]
    authoritative_ids = [row["tokenId"] for row in authoritative_rows]
    authoritative_by_id = {row["tokenId"]: row for row in authoritative_rows}
    if len(authoritative_ids) != len(set(authoritative_ids)):
        raise ValueError("authoritative TR token sequence contains duplicate identities")
    sequence_payload = json.dumps(
        authoritative_rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    sequence_sha256 = hashlib.sha256(sequence_payload).hexdigest()
    sequence_pin = (proposal.get("pinnedInputs") or {}).get(
        "authoritativeTrTokenSequence"
    ) or {}
    if (
        sequence_pin.get("tokenCount") != len(authoritative_rows)
        or sequence_pin.get("fields") != ["tokenId", "surfaceBeta"]
        or sequence_pin.get("sha256") != sequence_sha256
    ):
        raise ValueError("authoritative TR token order or surface changed")
    attachments = proposal.get("attachments") or []
    if not attachments:
        raise ValueError("proposal has no TR1894-first attachments")
    attachment_ids = [row.get("attachmentId") for row in attachments]
    if any(not item for item in attachment_ids) or len(attachment_ids) != len(set(attachment_ids)):
        raise ValueError("attachment IDs are missing or duplicated")
    approval = proposal.get("approval") or {}
    if proposal["status"] == "human-approved-noncanonical":
        if (
            approval.get("status") != "human-approved"
            or not approval.get("approvedBy")
            or not approval.get("date")
            or approval.get("scope") != "all-listed-attachments"
            or approval.get("approvedAttachmentIds") != attachment_ids
            or approval.get("bindingSha256") != approval_binding_sha256(proposal)
            or any(row.get("reviewStatus") != "human-approved" for row in attachments)
        ):
            raise ValueError("human approval is missing, incomplete, or stale")
    for attachment in attachments:
        if (
            attachment.get("reference") not in expected_references
            or not attachment.get("trTokenIds")
            or attachment.get("attachmentType") not in {
                "adapted-macula-syntax", "tr-native-reviewed-structure", "no-macula-syntax"
            }
        ):
            raise ValueError(f"invalid attachment: {attachment.get('attachmentId')}")
        token_ids = attachment["trTokenIds"]
        positions = [authoritative_ids.index(token_id) for token_id in token_ids]
        if positions != sorted(positions):
            raise ValueError(f"attachment is not in authoritative TR order: {attachment['attachmentId']}")
        declared_surfaces = attachment.get("trSurfaceBeta")
        if declared_surfaces is not None and declared_surfaces != [
            authoritative_by_id[token_id]["surfaceBeta"] for token_id in token_ids
        ]:
            raise ValueError(f"attachment changes a TR surface: {attachment['attachmentId']}")

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if mapping_sha256(MAPPING) != manifest.get("mapping", {}).get("sha256"):
        raise ValueError("MACULA Greek mapping ledger is stale")
    mapping = json.loads(MAPPING.read_text(encoding="utf-8"))
    validate_mapping_ledger(mapping)
    for name, path in (("trMaculaMapping", MAPPING), ("maculaManifest", MANIFEST)):
        pin = (proposal.get("pinnedInputs") or {}).get(name) or {}
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if pin.get("path") != path.relative_to(ROOT).as_posix() or pin.get("sha256") != actual:
            raise ValueError(f"pinned input changed: {name}")

    decisions = []
    for attachment in attachments:
        execution = attachment.get("execution")
        if not execution:
            continue
        evidence = attachment.get("maculaEvidence") or {}
        decisions.append({
            "decisionId": attachment["attachmentId"],
            "book": book.slug,
            "chapter": chapter,
            "reference": attachment["reference"],
            "decision": execution["decision"],
            "reviewer": approval.get("approvedBy") or "PROPOSAL-NOT-APPROVED",
            "date": approval.get("date") or "2026-11-24",
            "targetCandidateNodeId": execution.get("targetCandidateNodeId"),
            "replacedMaculaTerminalIds": evidence.get("terminalIds") or [],
            "trTokenIds": (
                attachment["trTokenIds"]
                if execution["decision"] != "rebuild-group-in-tr-order-from-existing-anchors"
                else []
            ),
            "nativeChildren": execution.get("nativeChildren"),
            "nativeGroup": attachment.get("structuralClaim"),
            "reason": attachment.get("reason") or attachment.get("difference"),
        })
    adjudications = {
        "schema": "tr1894-native-structure-adjudications-v1",
        "decisions": decisions,
    }

    candidate = project_chapter_candidate(book, chapter, mapping)
    candidate = apply_tr_authority_adaptations(candidate, mapping, adjudications)
    candidate = apply_structure_adjudications(candidate, adjudications)
    candidate = apply_tr_authority_fallbacks(candidate, mapping)
    validate_candidate(candidate)

    scope_rows = [
        row
        for row in mapping.get("verses") or []
        if row.get("reference") in expected_references
    ]
    expected_terminals = {
        item["maculaTerminalId"]
        for row in scope_rows
        for item in row.get("mapping") or []
    } | {
        terminal_id
        for row in scope_rows
        for terminal_id in row.get("unmatchedMaculaTerminalIds") or []
    }
    expected_tr_tokens = {
        item["trTokenId"]
        for row in scope_rows
        for item in row.get("mapping") or []
    } | {
        token_id
        for row in scope_rows
        for token_id in row.get("unmatchedTrTokenIds") or []
    }
    declared_tokens = {
        token_id for attachment in attachments for token_id in attachment["trTokenIds"]
    }
    unknown_declared_tokens = sorted(declared_tokens - expected_tr_tokens)
    if unknown_declared_tokens:
        raise ValueError(f"attachments name TR tokens outside scope: {unknown_declared_tokens}")

    nodes = list(walk_nodes(candidate))
    token_nodes = [
        node for node in nodes if node.get("kind") in {"word", "tr-word"}
    ]
    if any("surface" in key.lower() for node in token_nodes for key in node):
        raise ValueError("structural candidate must not carry or alter TR token surfaces")
    unresolved_terminals = sorted(
        node.get("maculaTerminalId")
        for node in nodes
        if node.get("kind") == "reference-word"
        and node.get("maculaTerminalId") in expected_terminals
    )
    placed_tokens = {
        node["trTokenId"]
        for node in nodes
        if node.get("kind") in {"word", "tr-word"} and node.get("trTokenId")
    }
    scope_fallbacks = [
        row
        for row in candidate.get("trAuthorityFallbacks") or []
        if row.get("reference") in expected_references
    ]
    fallback_tokens = {
        token_id for row in scope_fallbacks for token_id in row.get("trTokenIds") or []
    }
    candidate_token_occurrences = [
        node["trTokenId"]
        for node in token_nodes
        if node.get("trTokenId") in expected_tr_tokens
    ] + [
        token_id for row in scope_fallbacks for token_id in row.get("trTokenIds") or []
    ]
    coverage_mismatch = {
        token_id: count
        for token_id, count in (Counter(candidate_token_occurrences) - Counter(authoritative_ids)).items()
    } | {
        token_id: -count
        for token_id, count in (Counter(authoritative_ids) - Counter(candidate_token_occurrences)).items()
    }
    declared_fallback_tokens = {
        token_id
        for attachment in attachments
        if attachment["attachmentType"] == "no-macula-syntax"
        for token_id in attachment["trTokenIds"]
    }
    fallback_declaration_mismatch = sorted(fallback_tokens ^ declared_fallback_tokens)
    unplaced_tokens = sorted(expected_tr_tokens - placed_tokens - fallback_tokens)

    result = {
        "status": "PASS" if not unresolved_terminals and not unplaced_tokens and not fallback_declaration_mismatch and not coverage_mismatch else "FAIL",
        "proposal": proposal_path.relative_to(ROOT).as_posix(),
        "scope": scope,
        "approval": approval,
        "attachmentIds": attachment_ids,
        "unresolvedMaculaTerminalIds": unresolved_terminals,
        "unplacedTrTokenIds": unplaced_tokens,
        "authoritativeTrTokenSequence": {
            "tokenCount": len(authoritative_rows),
            "sha256": sequence_sha256,
            "coverageExactlyOnce": not coverage_mismatch,
            "surfacesCarriedOnlyByAuthoritativeSource": True,
        },
        "coverageMismatch": coverage_mismatch,
        "fallbackDeclarationMismatch": fallback_declaration_mismatch,
        "noSyntaxFallbacks": scope_fallbacks,
    }
    if args.write_candidate:
        output = args.write_candidate.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(candidate, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        result["candidate"] = str(output)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
