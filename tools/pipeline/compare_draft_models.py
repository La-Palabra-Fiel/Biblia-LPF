#!/usr/bin/env python3
"""Blind GPT-5.6 Sol vs GPT-6.1 Sol evaluation for the LBF draft stage.

This is an evaluation tool, not a translation path. It never writes canonical
data or pipeline candidates. Outputs live under /tmp by default.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import env_load  # noqa: F401,E402
from draft_lib import (  # noqa: E402
    DRAFT_EXPECTED_COMPLETION_TOKENS,
    DRAFT_MAX_COMPLETION_TOKENS,
    alignment_precision_findings,
    build_user_prompt,
    call_openai,
    load_system,
    normalize_draft,
)
from source_packet import validate_packet  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
PIPELINE = ROOT / "pipeline" / "ot" / "exodo"
DEFAULT_OUT = Path("/tmp/lbf-model-eval/exodo-gpt56-vs-gpt61")
MODELS = ("gpt-5.6-sol", "gpt-6.1-sol")
REASONING = "low"
RATES = {
    "gpt-5.6-sol": {"input": 4.00, "cached": 0.40, "output": 20.00},
    "gpt-6.1-sol": {"input": 2.00, "cached": 0.10, "output": 10.00},
}

# Four unchanged approvals, four Spanish corrections, four alignment-only
# corrections. Approved answers are never included in either model prompt.
SAMPLE = (
    (1, 2, "accepted-unchanged"),
    (12, 1, "accepted-unchanged"),
    (20, 1, "accepted-unchanged"),
    (29, 1, "accepted-unchanged"),
    (1, 1, "spanish-correction"),
    (13, 17, "spanish-correction"),
    (21, 6, "spanish-correction"),
    (22, 2, "spanish-correction"),
    (1, 16, "alignment-correction"),
    (14, 19, "alignment-correction"),
    (20, 20, "alignment-correction"),
    (24, 13, "alignment-correction"),
)


def canonical_json(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def object_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def token_words(value: str, *, preserve_supplied: bool = True) -> list[str]:
    result: list[str] = []
    for match in re.finditer(r"(?<!\*)\*([^*\n]+)\*(?!\*)|\w+", str(value or ""), re.UNICODE):
        supplied = match.group(1)
        if supplied is None:
            result.append(match.group(0).casefold())
        else:
            words = re.findall(r"\w+", supplied, re.UNICODE)
            result.extend((f"*{word.casefold()}*" if preserve_supplied else word.casefold()) for word in words)
    return result


def edit_distance(left: list[str], right: list[str]) -> int:
    prior = list(range(len(right) + 1))
    for i, a in enumerate(left, start=1):
        row = [i]
        for j, b in enumerate(right, start=1):
            row.append(min(row[-1] + 1, prior[j] + 1, prior[j - 1] + (a != b)))
        prior = row
    return prior[-1]


def structural_findings(packet: dict, candidate: dict) -> list[dict]:
    units = candidate.get("units")
    if not isinstance(units, list) or not units:
        return [{"code": "units-required", "issue": "Alignment units are required."}]
    allowed = {str(row.get("sourceTokenId")) for row in packet.get("tokens") or [] if row.get("sourceTokenId")}
    covered: set[str] = set()
    findings: list[dict] = []
    clean: list[dict] = []
    for index, unit in enumerate(units, start=1):
        surface = " ".join(str((unit or {}).get("es") or "").split())
        ids = list(dict.fromkeys(str(value) for value in ((unit or {}).get("sourceTokenIds") or []) if str(value)))
        if not surface or not ids:
            findings.append({"code": "unit-incomplete", "issue": f"Unit {index} is incomplete."})
            continue
        unknown = sorted(set(ids) - allowed)
        if unknown:
            findings.append({"code": "unknown-source-token", "issue": "Unknown source tokens: " + ", ".join(unknown)})
        valid = [value for value in ids if value in allowed]
        covered.update(valid)
        clean.append({"es": surface, "sourceTokenIds": valid})
    missing = sorted(allowed - covered)
    if missing:
        findings.append({"code": "missing-source-tokens", "issue": "Missing source tokens: " + ", ".join(missing)})
    for finding in alignment_precision_findings(packet, clean):
        findings.append({"code": "alignment-precision", **finding})
    spanish = str(candidate.get("spanish") or "")
    ordered = " ".join(unit["es"] for unit in clean)
    if token_words(ordered) != token_words(spanish):
        code = "spanish-reconstruction"
        if token_words(ordered, preserve_supplied=False) == token_words(spanish, preserve_supplied=False):
            code = "supplied-markup-mismatch"
        findings.append({"code": code, "issue": "Ordered units do not reproduce the complete Spanish."})
    return findings


def current_chapter_review(chapter: int) -> None:
    path = PIPELINE / f"exodo-{chapter}.human-review.json"
    review = read_json(path)
    if review.get("schema") != "lbf-human-chapter-review-v1" or review.get("invalidated"):
        raise SystemExit(f"Éxodo {chapter}: current human chapter review is required")


def sample_item(chapter: int, verse: int, category: str, system: str) -> dict:
    packet_path = PIPELINE / f"exodo-{chapter}-{verse}.packet.json"
    gold_path = PIPELINE / f"exodo-{chapter}-{verse}.candidate-human-reviewed.json"
    baseline_path = PIPELINE / f"exodo-{chapter}-{verse}.draft-team-gpt.json"
    for path in (packet_path, gold_path, baseline_path):
        if not path.is_file():
            raise SystemExit(f"missing evaluation input: {path}")
    current_chapter_review(chapter)
    packet = read_json(packet_path)
    validate_packet(packet)
    gold, baseline = read_json(gold_path), read_json(baseline_path)
    if gold.get("schema") != "lbf-human-reviewed-candidate-v1" or gold.get("adjudication", {}).get("status") != "approved":
        raise SystemExit(f"Éxodo {chapter}:{verse}: approved gold artifact is invalid")
    text_same = gold.get("spanish") == baseline.get("spanish")
    units_same = gold.get("units") == baseline.get("units")
    actual = "accepted-unchanged" if text_same and units_same else "alignment-correction" if text_same else "spanish-correction"
    if actual != category:
        raise SystemExit(f"Éxodo {chapter}:{verse}: category changed ({category} -> {actual})")
    prompt = build_user_prompt(packet)
    return {
        "reference": f"Éxodo {chapter}:{verse}", "chapter": chapter, "verse": verse,
        "category": category, "packet": rel(packet_path), "packetSha256": file_sha256(packet_path),
        "gold": rel(gold_path), "goldSha256": file_sha256(gold_path),
        "historicalBaseline": rel(baseline_path), "historicalBaselineSha256": file_sha256(baseline_path),
        "modelPromptSha256": object_sha256({"system": system, "user": prompt}),
        "promptUtf8Bytes": len(system.encode()) + len(prompt.encode()),
    }


def cost_projection(items: list[dict]) -> dict:
    by_model, likely_total, maximum_total = {}, 0.0, 0.0
    for model in MODELS:
        rate, likely, maximum = RATES[model], 0.0, 0.0
        for item in items:
            likely_input = int(item["promptUtf8Bytes"] * 0.36) + 200
            maximum_input = item["promptUtf8Bytes"] + 2048
            likely += (likely_input * rate["input"] + DRAFT_EXPECTED_COMPLETION_TOKENS * rate["output"]) / 1_000_000
            maximum += (maximum_input * rate["input"] + DRAFT_MAX_COMPLETION_TOKENS * rate["output"]) / 1_000_000
        by_model[model] = {"calls": len(items), "likelyUsdNoCache": round(likely, 4), "maximumUsdNoCache": round(maximum, 4)}
        likely_total += likely
        maximum_total += maximum
    return {
        "assumptions": {"ratesPerMillionTokens": RATES, "reasoningEffort": REASONING,
            "expectedCompletionTokensPerCall": DRAFT_EXPECTED_COMPLETION_TOKENS,
            "maximumCompletionTokensPerCall": DRAFT_MAX_COMPLETION_TOKENS,
            "maximumAssumesNoPromptCache": True},
        "byModel": by_model, "likelyUsd": round(likely_total, 4), "maximumUsd": round(maximum_total, 4),
    }


def build_manifest() -> dict:
    system = load_system()
    items = [sample_item(ch, vs, category, system) for ch, vs, category in SAMPLE]
    manifest = {
        "schema": "lbf-draft-model-eval-v1", "purpose": "Blind GPT-5.6 Sol vs GPT-6.1 Sol comparison",
        "noncanonical": True, "writesCanonicalData": False, "book": "exodo", "models": list(MODELS),
        "reasoningEffort": REASONING, "draftPromptSha256": hashlib.sha256(system.encode()).hexdigest(),
        "sample": items, "cost": cost_projection(items),
        "approval": {"paidCallsAuthorized": False, "instruction": "Run only after the user confirms maximumUsd."},
    }
    manifest["bindingSha256"] = object_sha256(manifest)
    return manifest


def verify_manifest(manifest: dict, *, before_paid_calls: bool = True) -> None:
    """Verify the paid binding, or only its frozen scoring inputs afterward.

    Before the first call every assumption must still match. After calls have
    completed, a later prompt edit must not prevent scoring the already-billed
    outputs; packet and hidden-gold hashes must still match exactly.
    """
    if before_paid_calls:
        if manifest.get("bindingSha256") != build_manifest().get("bindingSha256"):
            raise SystemExit("Evaluation inputs, prompt, prices, or sample changed. Prepare and review again.")
        return
    for item in manifest.get("sample") or []:
        for path_key, hash_key in (
            ("packet", "packetSha256"),
            ("gold", "goldSha256"),
            ("historicalBaseline", "historicalBaselineSha256"),
        ):
            path = ROOT / item[path_key]
            if not path.is_file() or file_sha256(path) != item[hash_key]:
                raise SystemExit(f"Frozen scoring input changed: {path}")


def result_path(out: Path, chapter: int, verse: int, model: str) -> Path:
    return out / "results" / f"exodo-{chapter}-{verse}.{model.replace('.', '-')}.json"


def usage_cost(model: str, usage: dict) -> float:
    rate, cached = RATES[model], int(usage.get("cachedInput") or 0)
    uncached = max(0, int(usage.get("input") or 0) - cached)
    return (uncached * rate["input"] + cached * rate["cached"] + int(usage.get("output") or 0) * rate["output"]) / 1_000_000


@contextmanager
def model_environment(model: str):
    old = (os.environ.get("LBF_GPT_MODEL"), os.environ.get("LBF_GPT_REASONING"))
    os.environ.update(LBF_GPT_MODEL=model, LBF_GPT_REASONING=REASONING)
    try:
        yield
    finally:
        for key, value in zip(("LBF_GPT_MODEL", "LBF_GPT_REASONING"), old):
            if value is None: os.environ.pop(key, None)
            else: os.environ[key] = value


def run_paid(manifest: dict, out: Path, confirmed: float) -> None:
    maximum = float(manifest["cost"]["maximumUsd"])
    if confirmed + 1e-9 < maximum:
        raise SystemExit(f"Confirmation ${confirmed:.4f} is below maximum ${maximum:.4f}.")
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is unavailable; no paid calls were made.")
    verify_manifest(manifest)
    system, actual_total = load_system(), 0.0
    for item in manifest["sample"]:
        packet = read_json(ROOT / item["packet"])
        prompt = build_user_prompt(packet)
        for model in MODELS:
            destination = result_path(out, item["chapter"], item["verse"], model)
            if destination.is_file():
                stored = read_json(destination)
                if stored.get("bindingSha256") != manifest["bindingSha256"]:
                    raise SystemExit(f"incompatible existing result: {destination}")
                actual_total += float(stored.get("usd") or 0)
                continue
            started = datetime.now(timezone.utc).isoformat()
            with model_environment(model):
                raw, usage = call_openai(system, prompt, max_completion_tokens=DRAFT_MAX_COMPLETION_TOKENS)
            candidate = normalize_draft(raw, packet, f"eval-{model}")
            candidate.update(
                model=model,
                reasoningEffort=REASONING,
                packetSha256=object_sha256(packet),
                promptSha256=manifest["draftPromptSha256"],
            )
            usd = usage_cost(model, usage); actual_total += usd
            write_json(destination, {"schema": "lbf-draft-model-eval-result-v1", "bindingSha256": manifest["bindingSha256"],
                "reference": item["reference"], "category": item["category"], "model": model,
                "reasoningEffort": REASONING, "startedAt": started,
                "draftPromptSha256": manifest["draftPromptSha256"],
                "modelPromptSha256": item["modelPromptSha256"],
                "usage": usage, "usd": round(usd, 6),
                "candidate": candidate, "canonical": False, "humanApproved": False})
            print(f"saved {item['reference']} {model} ${usd:.4f}", flush=True)
    print(f"Paid phase complete. Actual total: ${actual_total:.4f}")
    score_results(manifest, out)


def candidate_score(packet: dict, gold: dict, candidate: dict) -> dict:
    gold_words, candidate_words = token_words(gold.get("spanish", "")), token_words(candidate.get("spanish", ""))
    distance = edit_distance(gold_words, candidate_words)
    findings = structural_findings(packet, candidate)
    return {"structuralPass": not findings, "structuralFindings": findings,
        "spanishExact": candidate.get("spanish") == gold.get("spanish"),
        "spanishWordEditDistance": distance, "spanishWordSimilarity": round(max(0.0, 1 - distance / max(1, len(gold_words))), 4),
        "unitsExact": candidate.get("units") == gold.get("units"), "uncertainties": len(candidate.get("uncertainties") or []),
        "addedConcepts": len(candidate.get("addedConcepts") or []), "droppedUncitedUnits": int(candidate.get("droppedUncitedUnits") or 0)}


def blind_label(reference: str) -> dict[str, str]:
    return ({MODELS[0]: "A", MODELS[1]: "B"} if hashlib.sha256(reference.encode()).digest()[0] % 2 else {MODELS[0]: "B", MODELS[1]: "A"})


def score_results(manifest: dict, out: Path) -> None:
    verify_manifest(manifest, before_paid_calls=False)
    rows, blind_rows = [], []
    totals = {model: {"results": 0, "structuralPass": 0, "spanishExact": 0, "unitsExact": 0, "spanishWordEditDistance": 0, "usd": 0.0} for model in MODELS}
    for item in manifest["sample"]:
        packet, gold, labels = read_json(ROOT / item["packet"]), read_json(ROOT / item["gold"]), blind_label(item["reference"])
        blind_candidates = []
        for model in MODELS:
            path = result_path(out, item["chapter"], item["verse"], model)
            if not path.is_file(): raise SystemExit(f"missing result: {path}")
            stored, total = read_json(path), totals[model]
            score = candidate_score(packet, gold, stored["candidate"])
            rows.append({"reference": item["reference"], "category": item["category"], "model": model, "usd": stored.get("usd"), **score})
            total["results"] += 1; total["structuralPass"] += int(score["structuralPass"])
            total["spanishExact"] += int(score["spanishExact"]); total["unitsExact"] += int(score["unitsExact"])
            total["spanishWordEditDistance"] += score["spanishWordEditDistance"]; total["usd"] += float(stored.get("usd") or 0)
            candidate = stored["candidate"]
            blind_candidates.append({"candidate": labels[model], "spanish": candidate.get("spanish"), "units": candidate.get("units"), "declaredUncertainties": candidate.get("uncertainties") or []})
        blind_rows.append({"reference": item["reference"], "category": item["category"],
            "candidates": sorted(blind_candidates, key=lambda row: row["candidate"]),
            "humanReview": {"preferredCandidate": "", "seriousMeaningErrorA": False, "seriousMeaningErrorB": False,
                "wordingEditsA": None, "wordingEditsB": None, "alignmentEditsA": None, "alignmentEditsB": None,
                "reviewMinutesA": None, "reviewMinutesB": None, "notes": ""}})
    for total in totals.values(): total["usd"] = round(total["usd"], 4)
    write_json(out / "report.json", {"schema": "lbf-draft-model-eval-report-v1", "bindingSha256": manifest["bindingSha256"], "totals": totals, "results": rows})
    write_json(out / "blind-review.json", {"schema": "lbf-draft-model-blind-review-v1", "bindingSha256": manifest["bindingSha256"],
        "instruction": "Review A and B without opening report.json or result files, then fill humanReview.", "items": blind_rows})
    print(out / "report.json"); print(out / "blind-review.json")


def prepare(out: Path) -> dict:
    manifest = build_manifest()
    if (out / "results").is_dir() and list((out / "results").glob("*.json")):
        raise SystemExit(f"{out} contains paid results; choose a new --out directory.")
    write_json(out / "manifest.json", manifest)
    counts: dict[str, int] = {}
    for item in manifest["sample"]: counts[item["category"]] = counts.get(item["category"], 0) + 1
    print(f"Prepared {len(manifest['sample'])} verses / {len(manifest['sample']) * 2} calls")
    print("Sample: " + ", ".join(f"{key}={value}" for key, value in sorted(counts.items())))
    for item in manifest["sample"]: print(f"  {item['reference']:<14} {item['category']}")
    print(f"Likely cost:  ${manifest['cost']['likelyUsd']:.4f}")
    print(f"Maximum cost: ${manifest['cost']['maximumUsd']:.4f}")
    print(out / "manifest.json"); print("No API calls were made.")
    print(f"After reviewing, run with: --confirm-max-usd {manifest['cost']['maximumUsd']:.4f}")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "run", "score")); parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--confirm-max-usd", type=float); args = parser.parse_args(); out = args.out.resolve()
    if args.command == "prepare": prepare(out); return 0
    manifest_path = out / "manifest.json"
    if not manifest_path.is_file(): raise SystemExit(f"missing {manifest_path}; run prepare first")
    manifest = read_json(manifest_path)
    if args.command == "run":
        if args.confirm_max_usd is None: raise SystemExit("run requires --confirm-max-usd with the displayed ceiling")
        run_paid(manifest, out, args.confirm_max_usd); return 0
    score_results(manifest, out); return 0


if __name__ == "__main__": raise SystemExit(main())
