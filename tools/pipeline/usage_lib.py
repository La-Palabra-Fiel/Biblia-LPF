"""Record billed API tokens. Never writes translation/*.md or STATUS.md."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from books import ROOT, get_book

# USD per 1M tokens. Reasoning is inside output.
RATES = {
    "openai": {"input": 4.00, "cached": 0.40, "output": 20.00},
    "xai": {"input": 2.00, "cached": 0.50, "output": 6.00},
    "anthropic": {"input": 2.00, "cached": 0.20, "output": 10.00},
}
MODEL_RATES = {
    "gpt-5.6": {"input": 4.00, "cached": 0.40, "output": 20.00},
    "gpt-5.6-sol": {"input": 4.00, "cached": 0.40, "output": 20.00},
    "gpt-6.1-sol": {"input": 2.00, "cached": 0.10, "output": 10.00},
}

BIBLE_VERSES = 31_098


def usage_path(slug: str, chapter: int, verse: int) -> Path:
    book = get_book(slug)
    return (
        ROOT
        / "pipeline"
        / book.testament
        / book.slug
        / f"{book.slug}-{chapter}-{verse}.usage.json"
    )


def chapter_usage_path(slug: str, chapter: int) -> Path:
    book = get_book(slug)
    return ROOT / "pipeline" / book.testament / book.slug / f"{book.slug}-{chapter}.usage.json"


def extract_usage(provider: str, model: str, payload: dict) -> dict:
    u = payload.get("usage") or {}
    prompt_details = u.get("prompt_tokens_details") or u.get("input_tokens_details") or {}
    out_details = u.get("completion_tokens_details") or u.get("output_tokens_details") or {}
    input_n = int(u.get("prompt_tokens") or u.get("input_tokens") or 0)
    output_n = int(u.get("completion_tokens") or u.get("output_tokens") or 0)
    cached = int(
        prompt_details.get("cached_tokens")
        or u.get("cache_read_input_tokens")
        or 0
    )
    reasoning = int(out_details.get("reasoning_tokens") or u.get("reasoning_tokens") or 0)
    return {
        "provider": provider,
        "model": model,
        "input": input_n,
        "cachedInput": cached,
        "output": output_n,
        "reasoning": reasoning,
        "at": datetime.now(timezone.utc).isoformat(),
    }


def rates_for(usage: dict) -> dict[str, float]:
    model = str(usage.get("model") or "")
    return MODEL_RATES.get(model, RATES.get(usage.get("provider") or "", RATES["openai"]))


def call_cost(usage: dict) -> float:
    rates = rates_for(usage)
    cached = int(usage.get("cachedInput") or 0)
    billed_in = max(0, int(usage.get("input") or 0) - cached)
    output_n = int(usage.get("output") or 0)
    reasoning = int(usage.get("reasoning") or 0)
    billed_out = output_n if reasoning <= output_n else output_n + reasoning
    return (
        billed_in / 1_000_000 * rates["input"]
        + cached / 1_000_000 * rates["cached"]
        + billed_out / 1_000_000 * rates["output"]
    )


def record_call(slug: str, chapter: int, verse: int, stage: str, usage: dict) -> Path:
    path = usage_path(slug, chapter, verse)
    stored = {"schema": "lbf-usage-v1", "book": slug, "chapter": chapter, "verse": verse, "calls": []}
    if path.is_file():
        try:
            stored = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    call = dict(usage)
    call["stage"] = stage
    call["usd"] = round(call_cost(usage), 6)
    stored.setdefault("calls", []).append(call)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(stored, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def empty_totals() -> dict:
    return {
        "calls": 0,
        "verses": 0,
        "input": 0,
        "cachedInput": 0,
        "output": 0,
        "reasoning": 0,
        "usd": 0.0,
        "byProvider": {},
        "byStage": {},
    }


def _add(totals: dict, usage: dict) -> None:
    usd = float(usage.get("usd") if usage.get("usd") is not None else call_cost(usage))
    totals["calls"] += 1
    totals["input"] += int(usage.get("input") or 0)
    totals["cachedInput"] += int(usage.get("cachedInput") or 0)
    totals["output"] += int(usage.get("output") or 0)
    totals["reasoning"] += int(usage.get("reasoning") or 0)
    totals["usd"] += usd
    for key, label in (("provider", "byProvider"), ("stage", "byStage")):
        name = str(usage.get(key) or "unknown")
        bucket = totals[label].setdefault(
            name, {"calls": 0, "input": 0, "output": 0, "reasoning": 0, "usd": 0.0}
        )
        bucket["calls"] += 1
        bucket["input"] += int(usage.get("input") or 0)
        bucket["output"] += int(usage.get("output") or 0)
        bucket["reasoning"] += int(usage.get("reasoning") or 0)
        bucket["usd"] += usd


def summarize_files(paths: list[Path]) -> dict:
    totals = empty_totals()
    verses = set()
    for path in paths:
        if not path.is_file():
            continue
        try:
            stored = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        verses.add((stored.get("book"), stored.get("chapter"), stored.get("verse")))
        for call in stored.get("calls") or []:
            _add(totals, call)
    totals["verses"] = len(verses)
    totals["usd"] = round(totals["usd"], 4)
    for group in ("byProvider", "byStage"):
        for bucket in totals[group].values():
            bucket["usd"] = round(bucket["usd"], 4)
    per = totals["usd"] / totals["verses"] if totals["verses"] else 0.0
    totals["usdPerVerse"] = round(per, 4)
    totals["bibleAtThisRate"] = round(per * BIBLE_VERSES, 0)
    return totals


def summarize_chapter(slug: str, chapter: int) -> dict:
    book = get_book(slug)
    folder = ROOT / "pipeline" / book.testament / book.slug
    paths = sorted(folder.glob(f"{book.slug}-{chapter}-*.usage.json"))
    totals = summarize_files(paths)
    totals["book"] = book.slug
    totals["chapter"] = chapter
    if not paths:
        return totals
    out = chapter_usage_path(slug, chapter)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(totals, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return totals


def main() -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Roll up billed tokens for one chapter")
    parser.add_argument("book")
    parser.add_argument("chapter", type=int)
    args = parser.parse_args()
    totals = summarize_chapter(args.book, args.chapter)
    json.dump(totals, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
