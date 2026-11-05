#!/usr/bin/env python3
"""AI-verify reverse-link alignment for one book (Ollama).

Structural integrity (`audit_map_integrity.py`) is necessary but not enough.
This tool asks a local model to judge each Spanish unit against its linked
source tokens using surface + lemma/Strong's + BLE gloss.

It does **not** claim Hebraist/Hellenist review. It is the project's AI
alignment check for an owner who does not read the source languages.

    python3 tools/audit_alignment_ai.py zacarias
    python3 tools/audit_alignment_ai.py zacarias --limit 5
    python3 tools/audit_alignment_ai.py zacarias --resume

Writes:
  alignment/{nt|ot}/{book}/{book}-ai-alignment-audit.json

`tools/status.py` / `verify.py` require a passing audit (verdict=pass, every
phrase covered, 0 fail/error) before alignment may stay `ready`/`done`.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import status as lbf

ROOT = lbf.ROOT
DEFAULT_MODEL = os.environ.get("LBF_ALIGNMENT_AI_MODEL") or os.environ.get(
    "CGV_TRANSLATOR_OLLAMA_MODEL", "qwen2.5:14b"
)
DEFAULT_BASE = (
    os.environ.get("LBF_OLLAMA_BASE_URL")
    or os.environ.get("OLLAMA_HOST")
    or "http://127.0.0.1:11434"
).rstrip("/")

SYSTEM = """You verify Bible reverse-link alignment for LPF.

Each phrase lists Spanish alignment units and the source tokens they claim.
Each token includes: Hebrew/Greek surface, lemma/Strong's id, and an optional
BLE helper gloss.

IMPORTANT about BLE glosses:
- BLE glosses in this corpus are often wrong or crude.
- A Spanish↔gloss disagreement is NOT by itself a failed alignment.
- Gloss-only problems → verdict "warn" at most.
- Never fail a phrase solely because the BLE gloss looks wrong.

Judge the MAP:
- Does this Spanish unit reasonably render the linked lemma/Strong's token(s)?
- fail only for clear wrong links (e.g. Spanish "octavo" linked to a token that
  cannot mean eighth; Spanish name linked to an unrelated verb; empty tokens).
- pass when Spanish is a plausible rendering of the linked Strong's/lemma even
  if the BLE gloss says something else.
- warn when uncertain.

Return JSON only:
{
  "results": [
    {
      "phraseIndex": 0,
      "verdict": "pass" | "warn" | "fail",
      "issues": [{"unitId": "0:0", "severity": "short reason"}],
      "note": "optional one-line note"
    }
  ]
}

Rules:
- One result object per input phrase, same phraseIndex values.
- Prefer pass when the map is plausible.
- Be sparse with fails. Be specific in issue severity text.
- Do not rewrite Spanish. Do not invent tokens.
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def testament_for(book: str) -> str:
    rows = lbf.parse_status_table(lbf.STATUS_PATH.read_text(encoding="utf-8"))
    for row in rows:
        if row["book"] == book:
            return row["testament"]
    raise SystemExit(f"{book}: not in STATUS.md")


def audit_path(book: str, testament: str) -> Path:
    return ROOT / "alignment" / testament / book / f"{book}-ai-alignment-audit.json"


def phrases_path(book: str, testament: str) -> Path:
    return ROOT / "alignment" / testament / book / f"{book}-phrases.json"


def gloss_candidates(book: str) -> list[Path]:
    return [
        ROOT.parent / "cgv-data" / "interlinears" / "OT" / f"{book}.tokens.jsonl",
        ROOT.parent / "cgv-data" / "datasets" / "interlinear" / "OT" / f"{book}.tokens.jsonl",
        ROOT.parent / "herramientas" / "MNA" / "datasets" / "interlinear" / "OT" / f"{book}.tokens.jsonl",
        Path("/Users/johnwry/Nextcloud/Documents/GitHub/cgv-data/interlinears/OT")
        / f"{book}.tokens.jsonl",
        Path("/Users/johnwry/Nextcloud/Documents/GitHub/herramientas/MNA/datasets/interlinear/OT")
        / f"{book}.tokens.jsonl",
    ]


def load_gloss_index(book: str) -> dict[str, str]:
    index: dict[str, str] = {}
    for path in gloss_candidates(book):
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            gloss = str(row.get("es") or row.get("gloss") or "").replace("·", " ").replace("•", " ").strip()
            if not gloss:
                continue
            for key in (row.get("id"), row.get("sourceTokenId"), row.get("source_token_id")):
                if key:
                    index[str(key)] = gloss
            # Also index by ch|vs|w for spine fallback.
            try:
                ch, vs, w = int(row["ch"]), int(row["vs"]), int(row["w"])
                index[f"{ch}|{vs}|{w}"] = gloss
            except (KeyError, TypeError, ValueError):
                pass
        if index:
            return index
    return index


def strongs_from_lemma(lemma: str) -> str:
    match = re.search(r"(\d{3,5})", str(lemma or ""))
    return f"H{match.group(1)}" if match else ""


def build_phrase_payload(link: dict, phrase: dict | None, glosses: dict[str, str]) -> dict:
    token_rows = {
        str(row.get("sourceTokenId") or ""): row
        for row in (phrase or {}).get("tokenRows") or []
        if row.get("sourceTokenId")
    }
    units_out = []
    for unit in link.get("units") or []:
        tokens = []
        for tid in unit.get("sourceTokenIds") or []:
            tid = str(tid)
            row = token_rows.get(tid) or {}
            oshb = str(row.get("oshbId") or "")
            gloss = glosses.get(tid) or glosses.get(oshb) or ""
            if not gloss and phrase:
                # try ch|vs|w from token id hBBCCCVVVWWW
                m = re.match(r"^h\d{2}(\d{3})(\d{3})(\d{3})$", tid)
                if m:
                    gloss = glosses.get(
                        f"{int(m.group(1))}|{int(m.group(2))}|{int(m.group(3))}", ""
                    )
            lemma = str(row.get("lemma") or "")
            tokens.append(
                {
                    "id": tid,
                    "surface": row.get("surface") or row.get("hebrew") or "",
                    "lemma": lemma,
                    "strongs": strongs_from_lemma(lemma),
                    "gloss": gloss,
                }
            )
        units_out.append(
            {
                "unitId": unit.get("unitId"),
                "spanish": unit.get("surface"),
                "tokens": tokens,
            }
        )
    return {
        "phraseIndex": int(link.get("phraseIndex")),
        "reference": link.get("reference"),
        "spanish": (phrase or {}).get("spanish")
        or "".join(str(u.get("surface") or "") for u in link.get("units") or []),
        "units": units_out,
    }


def ollama_chat(base: str, model: str, prompt: str, timeout: int = 180) -> dict:
    body = {
        "model": model,
        "stream": False,
        "format": "json",
        "keep_alive": "20m",
        "options": {"temperature": 0, "num_ctx": 16384},
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ],
    }
    req = urllib.request.Request(
        f"{base}/api/chat",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise SystemExit(f"Ollama unreachable at {base}: {exc}") from exc
    text = ((raw.get("message") or {}).get("content") or "").strip()
    if not text:
        raise RuntimeError("Ollama returned empty content")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Ollama returned non-JSON: {text[:240]}") from exc


def normalize_results(payload: dict, expected_indexes: list[int]) -> list[dict]:
    results = payload.get("results")
    if not isinstance(results, list):
        raise RuntimeError("response missing results[]")
    by_index = {}
    for item in results:
        if not isinstance(item, dict):
            continue
        try:
            idx = int(item.get("phraseIndex"))
        except (TypeError, ValueError):
            continue
        verdict = str(item.get("verdict") or "").lower()
        if verdict not in {"pass", "warn", "fail"}:
            verdict = "fail"
        issues = item.get("issues") if isinstance(item.get("issues"), list) else []
        clean_issues = []
        for issue in issues:
            if isinstance(issue, dict):
                clean_issues.append(
                    {
                        "unitId": str(issue.get("unitId") or ""),
                        "severity": str(issue.get("severity") or issue.get("reason") or ""),
                    }
                )
            elif issue:
                clean_issues.append({"unitId": "", "severity": str(issue)})
        by_index[idx] = {
            "phraseIndex": idx,
            "verdict": verdict,
            "issues": clean_issues,
            "note": str(item.get("note") or ""),
        }
    out = []
    for idx in expected_indexes:
        if idx in by_index:
            out.append(by_index[idx])
        else:
            out.append(
                {
                    "phraseIndex": idx,
                    "verdict": "fail",
                    "issues": [{"unitId": "", "severity": "model omitted this phrase"}],
                    "note": "",
                }
            )
    return out


def empty_report(book: str, model: str, base: str) -> dict:
    return {
        "bookId": book,
        "schemaVersion": 1,
        "provider": "ollama",
        "model": model,
        "baseUrl": base,
        "startedAt": utc_now(),
        "finishedAt": None,
        "summary": {"pass": 0, "warn": 0, "fail": 0, "error": 0},
        "verdict": "fail",
        "phrases": [],
    }


def summarize(phrases: list[dict]) -> dict:
    counts = {"pass": 0, "warn": 0, "fail": 0, "error": 0}
    for row in phrases:
        key = str(row.get("verdict") or "error")
        if key not in counts:
            key = "error"
        counts[key] += 1
    verdict = "pass" if counts["fail"] == 0 and counts["error"] == 0 else "fail"
    return counts, verdict


def save_report(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("book", help="Book slug, e.g. zacarias")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url", default=DEFAULT_BASE)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--limit", type=int, default=0, help="Only first N unfinished phrases")
    parser.add_argument("--from-index", type=int, default=0)
    parser.add_argument("--resume", action="store_true", help="Keep prior phrase verdicts")
    parser.add_argument("--sleep", type=float, default=0.1)
    parser.add_argument("--timeout", type=int, default=600, help="Per-batch Ollama timeout seconds")
    args = parser.parse_args()

    book = args.book.strip().lower()
    testament = testament_for(book)
    align = lbf.alignment_path(book, testament)
    phrases_file = phrases_path(book, testament)
    out = audit_path(book, testament)
    if not align.is_file():
        raise SystemExit(f"missing {align}")

    links = load_json(align).get("links") or []
    phrases_raw = load_json(phrases_file) if phrases_file.is_file() else []
    if isinstance(phrases_raw, dict):
        phrases_raw = phrases_raw.get("phrases") or []
    by_phrase = {
        int(p["phraseIndex"]): p
        for p in phrases_raw
        if isinstance(p, dict) and "phraseIndex" in p
    }
    glosses = load_gloss_index(book)
    print(f"{book}: links={len(links)} glosses={len(glosses)} model={args.model}")

    report = empty_report(book, args.model, args.base_url)
    prior = {}
    if args.resume and out.is_file():
        old = load_json(out)
        report["startedAt"] = old.get("startedAt") or report["startedAt"]
        for row in old.get("phrases") or []:
            if isinstance(row, dict) and "phraseIndex" in row:
                prior[int(row["phraseIndex"])] = row
        print(f"resume: keeping {len(prior)} prior phrase verdicts")

    work = []
    for link in links:
        idx = int(link.get("phraseIndex"))
        if idx < args.from_index:
            continue
        if args.resume and idx in prior and prior[idx].get("verdict") in {"pass", "warn", "fail"}:
            continue
        work.append(link)
    if args.limit:
        work = work[: args.limit]

    results_by_index = dict(prior)
    batch_size = max(1, args.batch_size)
    total_batches = (len(work) + batch_size - 1) // batch_size if work else 0

    for batch_no, start in enumerate(range(0, len(work), batch_size), start=1):
        batch = work[start : start + batch_size]
        payloads = [
            build_phrase_payload(link, by_phrase.get(int(link.get("phraseIndex"))), glosses)
            for link in batch
        ]
        indexes = [int(p["phraseIndex"]) for p in payloads]
        prompt = (
            "Verify these alignment phrases. Return one results[] entry per phrase.\n\n"
            + json.dumps({"phrases": payloads}, ensure_ascii=False, indent=2)
        )
        print(f"batch {batch_no}/{total_batches}: phrases {indexes[0]}–{indexes[-1]} …", flush=True)
        try:
            response = ollama_chat(args.base_url, args.model, prompt, timeout=args.timeout)
            for row in normalize_results(response, indexes):
                # attach reference for humans
                link = next(l for l in batch if int(l.get("phraseIndex")) == row["phraseIndex"])
                row["reference"] = link.get("reference")
                results_by_index[row["phraseIndex"]] = row
                mark = {"pass": "·", "warn": "!", "fail": "X"}.get(row["verdict"], "?")
                print(f"  {mark} [{row['phraseIndex']}] {row['reference']} {row['verdict']}")
                if row["issues"]:
                    for issue in row["issues"][:3]:
                        print(f"      - {issue.get('unitId')}: {issue.get('severity')}")
        except Exception as exc:  # noqa: BLE001 — record and continue
            print(f"  ERROR batch {indexes}: {exc}", file=sys.stderr)
            for idx in indexes:
                link = next(l for l in batch if int(l.get("phraseIndex")) == idx)
                results_by_index[idx] = {
                    "phraseIndex": idx,
                    "reference": link.get("reference"),
                    "verdict": "error",
                    "issues": [{"unitId": "", "severity": str(exc)}],
                    "note": "",
                }
        # checkpoint after each batch
        phrases_out = [results_by_index[i] for i in sorted(results_by_index)]
        summary, verdict = summarize(phrases_out)
        report["phrases"] = phrases_out
        report["summary"] = summary
        report["verdict"] = verdict
        report["finishedAt"] = utc_now()
        save_report(out, report)
        if args.sleep:
            time.sleep(args.sleep)

    # Ensure every link has a row when not using --limit
    if not args.limit and not args.from_index:
        for link in links:
            idx = int(link.get("phraseIndex"))
            if idx not in results_by_index:
                results_by_index[idx] = {
                    "phraseIndex": idx,
                    "reference": link.get("reference"),
                    "verdict": "fail",
                    "issues": [{"unitId": "", "severity": "not audited"}],
                    "note": "",
                }

    phrases_out = [results_by_index[i] for i in sorted(results_by_index)]
    summary, verdict = summarize(phrases_out)
    if len(phrases_out) < len(links):
        # Partial runs must not look like a book-level pass.
        verdict = "fail"
    report["phrases"] = phrases_out
    report["summary"] = summary
    report["verdict"] = verdict
    report["finishedAt"] = utc_now()
    report["coveredPhraseCount"] = len(phrases_out)
    report["expectedPhraseCount"] = len(links)
    save_report(out, report)

    print(
        f"\n{book}: verdict={verdict} pass={summary['pass']} warn={summary['warn']} "
        f"fail={summary['fail']} error={summary['error']} "
        f"covered={len(phrases_out)}/{len(links)}"
    )
    print(f"wrote {out}")
    return 0 if verdict == "pass" and len(phrases_out) >= len(links) else 1


if __name__ == "__main__":
    raise SystemExit(main())
