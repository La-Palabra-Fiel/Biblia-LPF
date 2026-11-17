"""Closed loader for named-human Spanish lexical realization policy."""

from __future__ import annotations

import copy
import json
from functools import lru_cache
from pathlib import Path

from books import ROOT


POLICY_PATH = ROOT / "translation" / "LEXICAL_POLICY.json"
SCHEMA = "lpf-lexical-policy-v1"
ALLOWED_ENTRY_KEYS = {
    "id", "status", "testament", "match", "instruction", "spanishOptions",
    "avoid", "referenceRules", "review",
}
ALLOWED_MATCH_KEYS = {"strongsAny", "orderedStrongsSequences"}
ALLOWED_REVIEW_KEYS = {"title", "researchNote", "summary"}
ALLOWED_OPTION_KEYS = {"form", "when"}
ALLOWED_REFERENCE_RULE_KEYS = {
    "references", "strength", "preferred", "avoid", "participantOptions",
    "reason", "instruction",
}
ALLOWED_STATUSES = {"binding", "binding-options", "approved-options"}


def _token_strongs(token: dict) -> list[str]:
    values = token.get("strongsAll") or []
    if not values and token.get("strongs"):
        values = [token["strongs"]]
    return [str(value) for value in values if value]


def _has_sequence(tokens: list[dict], wanted: list[str]) -> bool:
    if not wanted:
        return False
    primary = [(_token_strongs(token) or [""])[0] for token in tokens]
    width = len(wanted)
    return any(primary[index:index + width] == wanted for index in range(len(primary) - width + 1))


@lru_cache(maxsize=1)
def load_policy() -> dict:
    payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    if payload.get("schema") != SCHEMA:
        raise ValueError("unexpected lexical policy schema")
    if payload.get("authority") != "named-human-editorial-policy":
        raise ValueError("lexical policy lacks named-human editorial authority")
    if not payload.get("version") or not payload.get("evidenceBoundary"):
        raise ValueError("lexical policy is missing its version or evidence boundary")
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise ValueError("lexical policy entries must be a list")
    ids = set()
    for entry in entries:
        unknown = set(entry) - ALLOWED_ENTRY_KEYS
        if unknown:
            raise ValueError(f"unknown lexical policy fields: {sorted(unknown)}")
        entry_id = entry.get("id")
        if not entry_id or entry_id in ids:
            raise ValueError("lexical policy IDs must be present and unique")
        ids.add(entry_id)
        if entry.get("testament") not in {"ot", "nt"}:
            raise ValueError(f"invalid lexical policy testament: {entry_id}")
        if entry.get("status") not in ALLOWED_STATUSES:
            raise ValueError(f"invalid lexical policy status: {entry_id}")
        match = entry.get("match") or {}
        if not match or set(match) - ALLOWED_MATCH_KEYS:
            raise ValueError(f"invalid lexical policy matcher: {entry_id}")
        options = entry.get("spanishOptions") or []
        if not entry.get("instruction") or not options:
            raise ValueError(f"lexical policy entry lacks options: {entry_id}")
        for option in options:
            if set(option) != ALLOWED_OPTION_KEYS or not all(option.values()):
                raise ValueError(f"invalid lexical policy option: {entry_id}")
        for rule in entry.get("referenceRules") or []:
            if not rule.get("references") or set(rule) - ALLOWED_REFERENCE_RULE_KEYS:
                raise ValueError(f"invalid lexical policy reference rule: {entry_id}")
        review = entry.get("review") or {}
        if set(review) != ALLOWED_REVIEW_KEYS:
            raise ValueError(f"lexical policy review metadata is incomplete: {entry_id}")
        note = ROOT / review["researchNote"].split("#", 1)[0]
        if not note.is_file():
            raise ValueError(f"lexical policy research note is missing: {entry_id}")
    return payload


def _matches(entry: dict, testament: str, tokens: list[dict]) -> bool:
    if entry["testament"] != testament:
        return False
    matcher = entry["match"]
    token_strongs = {value for token in tokens for value in _token_strongs(token)}
    if set(matcher.get("strongsAny") or []) & token_strongs:
        return True
    return any(
        _has_sequence(tokens, sequence)
        for sequence in matcher.get("orderedStrongsSequences") or []
    )


def policies_for_verse(testament: str, reference_key: str, tokens: list[dict]) -> tuple[list[dict], list[dict]]:
    policy = load_policy()
    model_entries = []
    review_entries = []
    for entry in policy["entries"]:
        if not _matches(entry, testament, tokens):
            continue
        active_rules = [
            {key: value for key, value in rule.items() if key != "references"}
            for rule in entry.get("referenceRules") or []
            if reference_key in rule.get("references", [])
        ]
        model_entries.append({
            "id": entry["id"],
            "status": entry["status"],
            "authority": policy["authority"],
            "evidenceBoundary": policy["evidenceBoundary"],
            "instruction": entry["instruction"],
            "spanishOptions": copy.deepcopy(entry["spanishOptions"]),
            "avoid": copy.deepcopy(entry.get("avoid") or []),
            "activeReferenceRules": copy.deepcopy(active_rules),
        })
        review_entries.append({
            "id": entry["id"],
            "status": entry["status"],
            **entry["review"],
        })
    return model_entries, review_entries


def policy_version() -> str:
    return str(load_policy()["version"])
