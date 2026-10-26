#!/usr/bin/env python3
"""Deterministic Spanish-policy gate for a GPT candidate. No API calls."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from books import ROOT, get_book
from lint_lib import lint_spanish


def artifact_path(slug: str, chapter: int, verse: int, label: str) -> Path:
    book = get_book(slug)
    safe = re.sub(r"[^a-z0-9._-]+", "-", label.lower()).strip("-") or "gpt"
    return ROOT / "pipeline" / book.testament / book.slug / f"{book.slug}-{chapter}-{verse}.spanish-check-{safe}.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("book")
    parser.add_argument("chapter", type=int)
    parser.add_argument("verse", type=int)
    parser.add_argument("--candidate-file", required=True)
    parser.add_argument("--label", default="gpt-draft")
    args = parser.parse_args()

    candidate_path = Path(args.candidate_file)
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    spanish = str(candidate.get("spanish") or "").strip()
    if not spanish:
        raise SystemExit("--candidate-file must contain nonempty Spanish")
    findings = lint_spanish(spanish)
    result = {
        "schema": "lbf-spanish-check-v1",
        "policy": "lbf-spanish-deterministic-v1",
        "checker": "deterministic local lint; final flow is adjudicated by the named human",
        "book": args.book,
        "chapter": args.chapter,
        "verse": args.verse,
        "spanish": spanish,
        "verdict": "fail" if findings else "pass",
        "findings": findings,
        "notes": "No paid model call.",
        "model": "deterministic-local",
        "reasoningEffort": "none",
        "candidateSha256": hashlib.sha256(
            json.dumps(candidate, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
    }
    out = artifact_path(args.book, args.chapter, args.verse, args.label)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{result['verdict']}  {out}  findings={len(findings)}")
    return 0 if result["verdict"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
