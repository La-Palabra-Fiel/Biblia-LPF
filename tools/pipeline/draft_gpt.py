#!/usr/bin/env python3
"""Authorized GPT path: draft one verse from its canonical evidence packet.

Does not write translation markdown or STATUS.md.

    python3 tools/pipeline/draft_gpt.py exodo 1 16
    python3 tools/pipeline/draft_gpt.py exodo 1 16 --prompt-only
    python3 tools/pipeline/draft_gpt.py exodo 1 16 --ingest gpt-response.json
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
from books import get_book
from draft_lib import (
    DRAFT_MAX_COMPLETION_TOKENS,
    OpenAIResponseError,
    build_user_prompt,
    call_openai,
    draft_path,
    load_system,
    normalize_draft,
    request_path,
    write_json,
)
from source_packet import build_packet, packet_path, validate_packet, write_packet
from usage_lib import record_call


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("book")
    parser.add_argument("chapter", type=int)
    parser.add_argument("verse", type=int)
    parser.add_argument("--label", default="gpt56")
    parser.add_argument("--prompt-only", action="store_true")
    parser.add_argument("--ingest", help="JSON reply saved from Cursor GPT")
    args = parser.parse_args()

    book = get_book(args.book)
    stored = packet_path(book, args.chapter, args.verse)
    if stored.is_file():
        packet = json.loads(stored.read_text(encoding="utf-8"))
        validate_packet(packet)
    else:
        packet = build_packet(args.book, args.chapter, args.verse)
        stored = write_packet(packet)

    system = load_system()
    user_prompt = build_user_prompt(packet)
    req_file = request_path(args.book, args.chapter, args.verse, args.label)
    write_json(req_file, {"system": system, "user": user_prompt, "packetRef": str(stored), "model": os.environ.get("LBF_GPT_MODEL", "gpt-5.1"), "reasoningEffort": (os.environ.get("LBF_GPT_REASONING") or "medium").strip()})
    out = draft_path(args.book, args.chapter, args.verse, args.label)

    if args.prompt_only:
        print(f"wrote GPT request {req_file}")
        return 0

    if args.ingest:
        ingest_path = Path(args.ingest)
        if not ingest_path.is_file():
            print(f"--ingest file not found: {ingest_path}", file=sys.stderr)
            return 2
        raw = json.loads(ingest_path.read_text(encoding="utf-8"))
        draft = normalize_draft(raw, packet, args.label)
        draft["reasoningEffort"] = (os.environ.get("LBF_GPT_REASONING") or "medium").strip()
        draft["packetSha256"] = hashlib.sha256(json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        write_json(out, draft)
        print(f"draft  {out}")
        print(draft["spanish"])
        return 0

    try:
        raw, usage = call_openai(
            system,
            user_prompt,
            max_completion_tokens=DRAFT_MAX_COMPLETION_TOKENS,
        )
        record_call(args.book, args.chapter, args.verse, "draft", usage)
    except RuntimeError as exc:
        if isinstance(exc, OpenAIResponseError):
            record_call(args.book, args.chapter, args.verse, "draft-invalid-response", exc.usage)
            print(f"Preparation stopped safely: {exc}", file=sys.stderr)
        else:
            print(f"API unavailable ({exc}). Request saved at {req_file}", file=sys.stderr)
        if out.is_file():
            existing = json.loads(out.read_text(encoding="utf-8"))
            print(
                f"Cursor GPT draft already on disk: {out}",
                file=sys.stderr,
            )
            print(existing.get("spanish") or "", file=sys.stderr)
            return 0
        print("Use the saved request JSON in the authorized GPT task, then --ingest the response.", file=sys.stderr)
        return 2

    draft = normalize_draft(raw, packet, args.label)
    draft["reasoningEffort"] = (os.environ.get("LBF_GPT_REASONING") or "medium").strip()
    draft["packetSha256"] = hashlib.sha256(json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    write_json(out, draft)
    print(f"draft  {out}")
    print(draft["spanish"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
