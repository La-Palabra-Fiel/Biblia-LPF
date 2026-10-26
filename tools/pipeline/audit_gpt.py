#!/usr/bin/env python3
"""Independent GPT source-fidelity audit for one canonical OT candidate.

This writes a request even when no API key is configured. It never rewrites
Spanish, translation Markdown, alignment, or STATUS.md.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import env_load  # noqa: F401
from audit_lib import SYSTEM, audit_path, build_user_prompt, normalize_audit, request_path, write_json
from books import get_book
from draft_lib import OpenAIResponseError, call_openai
from source_packet import build_packet, packet_path, validate_packet, write_packet
from usage_lib import record_call

AUDIT_MAX_COMPLETION_TOKENS = 1800


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("book")
    parser.add_argument("chapter", type=int)
    parser.add_argument("verse", type=int)
    parser.add_argument("--candidate-file", required=True)
    parser.add_argument("--label", default="gpt-draft")
    parser.add_argument("--prompt-only", action="store_true")
    parser.add_argument("--ingest", help="JSON audit response to normalize")
    args = parser.parse_args()

    candidate = json.loads(Path(args.candidate_file).read_text(encoding="utf-8"))
    spanish = str(candidate.get("spanish") or "").strip()
    if not spanish:
        raise SystemExit("--candidate-file must contain nonempty Spanish")
    label = str(candidate.get("label") or args.label)

    book = get_book(args.book)
    stored = packet_path(book, args.chapter, args.verse)
    packet = json.loads(stored.read_text(encoding="utf-8")) if stored.is_file() else build_packet(args.book, args.chapter, args.verse)
    if not stored.is_file():
        write_packet(packet)
    validate_packet(packet)

    user = build_user_prompt(packet, spanish, label)
    request = request_path(args.book, args.chapter, args.verse, f"gpt-{label}")
    write_json(request, {"system": SYSTEM, "user": user, "packetRef": str(stored), "model": os.environ.get("LBF_GPT_MODEL", "gpt-5.1"), "reasoningEffort": (os.environ.get("LBF_GPT_REASONING") or "medium").strip()})
    if args.prompt_only:
        print(f"wrote GPT audit request {request}")
        return 0

    if args.ingest:
        raw = json.loads(Path(args.ingest).read_text(encoding="utf-8"))
    else:
        try:
            raw, usage = call_openai(
                SYSTEM,
                user,
                max_completion_tokens=AUDIT_MAX_COMPLETION_TOKENS,
            )
            record_call(args.book, args.chapter, args.verse, "audit-draft-gpt", usage)
        except RuntimeError as exc:
            if isinstance(exc, OpenAIResponseError):
                record_call(args.book, args.chapter, args.verse, "audit-invalid-response", exc.usage)
                print(f"Preparation stopped safely: {exc}", file=sys.stderr)
            else:
                print(f"API unavailable ({exc}). Request saved at {request}", file=sys.stderr)
            return 2

    audit = normalize_audit(raw, packet, spanish, label, auditor="GPT independent audit")
    audit["model"] = os.environ.get("LBF_GPT_MODEL", "gpt-5.1")
    audit["reasoningEffort"] = (os.environ.get("LBF_GPT_REASONING") or "medium").strip()
    audit["packetSha256"] = hashlib.sha256(json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    audit["candidateSha256"] = hashlib.sha256(json.dumps(candidate, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    output = audit_path(args.book, args.chapter, args.verse, f"gpt-{label}")
    write_json(output, audit)
    print(f"{audit['verdict']}  {output}  findings={len(audit['findings'])}")
    return 0 if audit["verdict"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
