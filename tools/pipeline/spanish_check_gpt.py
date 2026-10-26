#!/usr/bin/env python3
"""Independent current-Spanish gate for one GPT draft.

This judges Spanish flow only. It never changes the draft, translation,
alignment, or STATUS.md.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import env_load  # noqa: F401
from books import ROOT, get_book
from draft_lib import call_openai, write_json
from lint_lib import lint_spanish
from usage_lib import record_call

POLICY = "lbf-spanish-flow-v2"
SYSTEM = (Path(__file__).resolve().parent / "spanish_check_prompt.md").read_text(encoding="utf-8").strip()


def artifact_path(slug: str, chapter: int, verse: int, label: str) -> Path:
    book = get_book(slug)
    safe = re.sub(r"[^a-z0-9._-]+", "-", label.lower()).strip("-") or "gpt"
    return ROOT / "pipeline" / book.testament / book.slug / f"{book.slug}-{chapter}-{verse}.spanish-check-{safe}.json"


def normalize(raw: dict, slug: str, chapter: int, verse: int, spanish: str) -> dict:
    findings = []
    for item in raw.get("findings") or []:
        issue = str(item.get("issue") or "").strip()
        if not issue:
            continue
        severity = item.get("severity") or "fail"
        if severity not in {"fail", "warn"}:
            severity = "fail"
        findings.append({
            "severity": severity,
            "issue": issue,
            "spanishSpan": str(item.get("spanishSpan") or "").strip(),
        })
    verdict = "fail" if any(x["severity"] == "fail" for x in findings) else "pass"
    return {
        "schema": "lbf-spanish-check-v1",
        "policy": POLICY,
        "checker": "GPT independent Spanish check",
        "book": slug,
        "chapter": chapter,
        "verse": verse,
        "spanish": spanish,
        "verdict": verdict,
        "findings": findings,
        "notes": str(raw.get("notes") or "").strip(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("book")
    parser.add_argument("chapter", type=int)
    parser.add_argument("verse", type=int)
    parser.add_argument("--candidate-file", required=True)
    parser.add_argument("--label", default="gpt-pilot")
    parser.add_argument("--prompt-only", action="store_true")
    args = parser.parse_args()

    candidate = json.loads(Path(args.candidate_file).read_text(encoding="utf-8"))
    spanish = str(candidate.get("spanish") or "").strip()
    if not spanish:
        raise SystemExit("--candidate-file must contain nonempty Spanish")
    out = artifact_path(args.book, args.chapter, args.verse, args.label)
    request = out.with_suffix(".request.json")
    user = "Verify this Spanish line. JSON only.\n\n" + json.dumps({"spanish": spanish}, ensure_ascii=False)
    write_json(request, {"system": SYSTEM, "user": user, "candidateRef": args.candidate_file, "model": os.environ.get("LBF_GPT_MODEL", "gpt-5.1"), "reasoningEffort": (os.environ.get("LBF_GPT_REASONING") or "medium").strip()})
    if args.prompt_only:
        print(f"wrote GPT Spanish-check request {request}")
        return 0

    local = lint_spanish(spanish)
    if local:
        raw = {"findings": local, "notes": "failed deterministic local lint"}
    else:
        raw, usage = call_openai(SYSTEM, user, max_completion_tokens=700)
        record_call(args.book, args.chapter, args.verse, "spanish-check-gpt", usage)
    result = normalize(raw, args.book, args.chapter, args.verse, spanish)
    result["model"] = os.environ.get("LBF_GPT_MODEL", "gpt-5.1")
    result["reasoningEffort"] = (os.environ.get("LBF_GPT_REASONING") or "medium").strip()
    result["candidateSha256"] = hashlib.sha256(json.dumps(candidate, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    write_json(out, result)
    print(f"{result['verdict']}  {out}  findings={len(result['findings'])}")
    return 0 if result["verdict"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
