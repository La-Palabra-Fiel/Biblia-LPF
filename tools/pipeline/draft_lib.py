"""Source-faithful GPT verse draft from the canonical evidence packet.

Does not write translation Markdown, alignment, or STATUS.md.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

from books import ROOT, get_book
from source_packet import dump_prompt, packet_for_prompt
from usage_lib import extract_usage

PROMPT_PATH = Path(__file__).resolve().parent / "draft_prompt.md"
DRAFT_SCHEMA = "lbf-gpt-draft-v1"
DRAFT_MAX_COMPLETION_TOKENS = 4000


class OpenAIResponseError(RuntimeError):
    """A billed response that could not be used as a pipeline artifact."""

    def __init__(self, message: str, usage: dict):
        super().__init__(message)
        self.usage = usage


def load_system() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8").strip()


def draft_path(book_slug: str, chapter: int, verse: int, label: str = "gpt56") -> Path:
    book = get_book(book_slug)
    safe = re.sub(r"[^a-z0-9._-]+", "-", label.lower()).strip("-") or "gpt56"
    return (
        ROOT
        / "pipeline"
        / book.testament
        / book.slug
        / f"{book.slug}-{chapter}-{verse}.draft-{safe}.json"
    )


def request_path(book_slug: str, chapter: int, verse: int, label: str = "gpt56") -> Path:
    book = get_book(book_slug)
    safe = re.sub(r"[^a-z0-9._-]+", "-", label.lower()).strip("-") or "gpt56"
    return (
        ROOT
        / "pipeline"
        / book.testament
        / book.slug
        / f"{book.slug}-{chapter}-{verse}.draft-{safe}.request.json"
    )


def build_user_prompt(packet: dict) -> str:
    return (
        "Draft this verse using ONLY the packet. JSON only.\n\n"
        + dump_prompt({"packet": packet_for_prompt(packet)})
    )


def parse_json_object(text: str) -> dict:
    raw = (text or "").strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start >= 0 and end > start:
            return json.loads(raw[start : end + 1])
        raise


def allowed_token_ids(packet: dict) -> set[str]:
    return {
        str(token.get("sourceTokenId") or "")
        for token in packet.get("tokens") or []
        if token.get("sourceTokenId")
    }


def normalize_draft(raw: dict, packet: dict, label: str) -> dict:
    allowed = allowed_token_ids(packet)
    units = []
    dropped = 0
    for item in raw.get("units") or []:
        ids = [tid for tid in (item.get("sourceTokenIds") or []) if tid in allowed]
        es = str(item.get("es") or "").strip()
        if not es:
            continue
        if not ids:
            dropped += 1
            continue
        units.append({"es": es, "sourceTokenIds": ids})
    added = [str(x).strip() for x in (raw.get("addedConcepts") or []) if str(x).strip()]
    uncertainties = []
    for item in raw.get("uncertainties") or []:
        if isinstance(item, dict):
            ids = [tid for tid in (item.get("sourceTokenIds") or []) if tid in allowed]
            issue = str(item.get("issue") or "").strip()
            if issue:
                uncertainties.append({"sourceTokenIds": ids, "issue": issue})
            continue
        issue = str(item).strip()
        if issue:
            uncertainties.append({"sourceTokenIds": [], "issue": issue})
    evidence_decisions = []
    for item in raw.get("evidenceDecisions") or []:
        ids = [tid for tid in (item.get("sourceTokenIds") or []) if tid in allowed]
        issue = str(item.get("issue") or "").strip()
        rationale = str(item.get("rationale") or "").strip()
        level = str(item.get("evidenceLevel") or "").strip()
        alternatives = [str(x).strip() for x in (item.get("alternatives") or []) if str(x).strip()]
        if ids and issue and rationale:
            evidence_decisions.append({"sourceTokenIds": ids, "issue": issue, "evidenceLevel": level, "rationale": rationale, "alternatives": alternatives})
    return {
        "schema": DRAFT_SCHEMA,
        "drafter": "Cursor Auto" if label == "auto" else "GPT-5.6",
        "model": os.environ.get("LBF_GPT_MODEL", "gpt-5.1"),
        "label": label,
        "book": packet["book"],
        "reference": packet["reference"],
        "chapter": packet["chapter"],
        "verse": packet["verse"],
        "spanish": str(raw.get("spanish") or "").strip(),
        "units": units,
        "uncertainties": uncertainties,
        "evidenceDecisions": evidence_decisions,
        "addedConcepts": added,
        "droppedUncitedUnits": dropped,
    }


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def call_openai(
    system: str,
    user: str,
    *,
    max_completion_tokens: int | None = None,
) -> tuple[dict, dict]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("no OPENAI_API_KEY")
    model = os.environ.get("LBF_GPT_MODEL", "gpt-5.1")
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "response_format": {"type": "json_object"},
    }
    if max_completion_tokens is not None:
        body["max_completion_tokens"] = int(max_completion_tokens)
    effort = (os.environ.get("LBF_GPT_REASONING") or "medium").strip()
    if effort:
        body["reasoning_effort"] = effort
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(exc.read().decode("utf-8")) from exc
    usage = extract_usage("openai", model, payload)
    choice = (payload.get("choices") or [{}])[0]
    text = (choice.get("message") or {}).get("content") or ""
    if not text.strip():
        finish_reason = choice.get("finish_reason") or "unknown"
        raise OpenAIResponseError(
            f"GPT returned no usable JSON (finish reason: {finish_reason}). The billed call was recorded; no automatic retry was made.",
            usage,
        )
    try:
        parsed = parse_json_object(text)
    except (json.JSONDecodeError, ValueError) as exc:
        finish_reason = choice.get("finish_reason") or "unknown"
        raise OpenAIResponseError(
            f"GPT returned invalid JSON (finish reason: {finish_reason}). The billed call was recorded; no automatic retry was made.",
            usage,
        ) from exc
    return parsed, usage
