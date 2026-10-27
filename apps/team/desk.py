"""Named-human chapter review for the closed LBF GPT workflow.

Models prepare evidence-bound candidates. Only the explicit review action
writes canonical Spanish. This module never writes a `done` status and never
promotes alignment seeds to canonical alignment.
"""

from __future__ import annotations

import json
import hashlib
import math
import os
import re
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PIPELINE = ROOT / "tools" / "pipeline"
sys.path.insert(0, str(PIPELINE))
import env_load  # noqa: E402,F401

# The team workflow is deliberately not model-configurable. Changing this is a
# policy change, not an operator preference.
TEAM_MODEL = "gpt-5.6-sol"
TEAM_REASONING = "medium"
SPANISH_GATE_MODEL = "deterministic-local"
os.environ["LBF_GPT_MODEL"] = TEAM_MODEL
os.environ["LBF_GPT_REASONING"] = TEAM_REASONING

from auto_pass import write_verse  # noqa: E402
from books import OT, get_book  # noqa: E402
from lint_lib import lint_divine_name, lint_spanish  # noqa: E402
from source_packet import build_packet, list_verses  # noqa: E402
from draft_lib import DRAFT_MAX_COMPLETION_TOKENS, alignment_precision_findings, build_user_prompt as build_draft_prompt, load_system as load_draft_system, prompt_fingerprint as draft_prompt_fingerprint  # noqa: E402
from audit_gpt import AUDIT_MAX_COMPLETION_TOKENS  # noqa: E402
from audit_lib import SYSTEM as AUDIT_SYSTEM, build_user_prompt as build_audit_prompt  # noqa: E402

HEADING = re.compile(r"^###\s+(\d+):(\d+)\s*$")
STATUS_COLUMNS = ("book", "testament", "translation", "alignment", "translation_by", "translation_on", "alignment_by", "alignment_on", "notes")
VAR = Path(__file__).resolve().parent / "var"
CLAIMS, PEOPLE = VAR / "claims.json", VAR / "people.json"
RECOVERED = VAR / "recovered-reviews"
STATUS = ROOT / "STATUS.md"
MAX_RUNNING = max(1, int(os.environ.get("LBF_TEAM_WORKERS", "4")))
_lock = threading.RLock()
_threads: dict[str, threading.Thread] = {}
_stops: dict[str, threading.Event] = {}
_chapter_counts: dict[str, int] = {}

# Measured across the stored GPT-5.6 Sol requests, input tokens are at most
# about 0.341 per UTF-8 byte. Keep a small safety margin without incorrectly
# charging every byte as a full token in the preflight estimate.
INPUT_TOKENS_PER_UTF8_BYTE = 0.36


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def model_name() -> str:
    return TEAM_MODEL


def reasoning_effort() -> str:
    return TEAM_REASONING


def read_json(path: Path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else default


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def packet_fingerprint(packet: dict) -> str:
    raw = json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def object_fingerprint(value: dict) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def estimate_input_tokens(text: str) -> int:
    return math.ceil(len(text.encode("utf-8")) * INPUT_TOKENS_PER_UTF8_BYTE)


def enforce_human_adjudication(prior: dict, gate: dict, spanish: str, decision: str, override_confirmed: bool) -> None:
    needs_adjudication = gate.get("fidelity") not in {"pass", "not-required"} or gate.get("spanish") != "pass" or bool(prior.get("uncertainties"))
    if needs_adjudication and not decision:
        raise ValueError("Write your own human adjudication for every failed gate or model uncertainty; the app will not manufacture one.")
    unchanged = spanish == " ".join(str(prior.get("spanish") or "").split())
    if gate.get("fidelity") == "fail" and unchanged and not override_confirmed:
        raise ValueError("The independent audit failed this unchanged wording. Correct it, or explicitly confirm a reasoned human override.")


def load_claims() -> dict:
    data = read_json(CLAIMS, {})
    return data if isinstance(data, dict) else {}


def save_claims(value: dict) -> None:
    write_json(CLAIMS, value)


def load_people() -> dict:
    data = read_json(PEOPLE, {})
    return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}


def clean_name(name: str) -> str:
    value = " ".join(str(name or "").split())
    if not value or len(value) > 40 or any(x in value for x in "\r\n|"):
        raise ValueError("Enter your registered name (40 characters or fewer).")
    return value


def authorize(name: str, token: str) -> str:
    person = clean_name(name)
    for known, secret in load_people().items():
        if known.casefold() == person.casefold() and str(token or "").strip() == secret:
            return known
    raise ValueError("Name or token does not match.")


def book_or_raise(slug: str):
    try:
        book = get_book(str(slug or ""))
    except KeyError as exc:
        raise ValueError(str(exc)) from exc
    if book.testament != "ot":
        raise ValueError("The New Testament is blocked until its equivalent evidence packet is authorized.")
    return book


def chapter_or_raise(slug: str, chapter):
    book = book_or_raise(slug)
    try:
        number = int(chapter)
        verses = list(list_verses(book.slug, number))
    except (TypeError, ValueError, KeyError) as exc:
        raise ValueError("Choose a canonical chapter.") from exc
    if not verses:
        raise ValueError(f"{book.label} {number} has no canonical verses.")
    return book, number, verses


def claim_key(slug: str, chapter: int) -> str:
    return f"{slug}:{chapter}"


def _alive(key: str) -> bool:
    return bool(_threads.get(key) and _threads[key].is_alive())


def claim(name, slug, chapter, token="") -> dict:
    person = authorize(name, token)
    book, number, _ = chapter_or_raise(slug, chapter)
    key = claim_key(book.slug, number)
    with _lock:
        claims = load_claims()
        old = claims.get(key)
        if old and old.get("name") != person:
            raise ValueError(f"{book.label} {number} is already held by {old.get('name')}.")
        claims[key] = {"book": book.slug, "chapter": number, "name": person, "running": _alive(key), "verse": (old or {}).get("verse"), "note": (old or {}).get("note") or "Claimed for human review", "updated": now()}
        save_claims(claims)
        return claims[key]


def assert_holder(person: str, slug: str, chapter: int):
    claims, key = load_claims(), claim_key(slug, chapter)
    if not claims.get(key) or claims[key].get("name") != person:
        raise ValueError(f"Claim {slug} {chapter} before reviewing it.")
    return claims, key


def release(name, slug, chapter, token="") -> None:
    person = authorize(name, token)
    book, number, _ = chapter_or_raise(slug, chapter)
    with _lock:
        claims, key = assert_holder(person, book.slug, number)
        if _alive(key):
            _stops[key].set()
            raise ValueError("Preparation is stopping after this verse. Release again when it stops.")
        claims.pop(key)
        save_claims(claims)


def pipeline_dir(slug: str) -> Path:
    book = book_or_raise(slug)
    return ROOT / "pipeline" / book.testament / book.slug


def packet_path(slug: str, chapter: int, verse: int) -> Path:
    return pipeline_dir(slug) / f"{slug}-{chapter}-{verse}.packet.json"


def human_path(slug: str, chapter: int, verse: int) -> Path:
    return pipeline_dir(slug) / f"{slug}-{chapter}-{verse}.candidate-human-reviewed.json"


def recovered_path(slug: str, chapter: int) -> Path:
    return RECOVERED / f"{slug}-{chapter}.json"


def save_review_attempt(book, chapter: int, verse: int, person: str, payload: dict) -> None:
    """Preserve a named human's exact form state even when validation rejects it."""
    path = recovered_path(book.slug, chapter)
    recovered = read_json(path, {})
    if not isinstance(recovered, dict):
        recovered = {}
    recovered.update(schema="lbf-recovered-browser-review-v1", book=book.slug, chapter=chapter)
    recovered.setdefault("note", "Trabajo humano guardado antes de la validación canónica.")
    verses = recovered.setdefault("verses", {})
    verses[str(verse)] = {
        "spanish": str(payload.get("spanish") or ""),
        "units": payload.get("units") if isinstance(payload.get("units"), list) else [],
        "unitsComplete": bool(payload.get("unitsComplete")),
        "decision": str(payload.get("decision") or ""),
        "sourceConfirmed": bool(payload.get("sourceConfirmed")),
        "alignmentConfirmed": bool(payload.get("alignmentConfirmed")),
        "suppliedConfirmed": bool(payload.get("suppliedConfirmed")),
        "auditOverrideConfirmed": bool(payload.get("auditOverrideConfirmed")),
        "lastAttemptedBy": person,
        "lastAttemptedOn": now(),
    }
    write_json(path, recovered)


def candidate_path(slug: str, chapter: int, verse: int) -> Path | None:
    folder = pipeline_dir(slug)
    options = []
    if human_review_is_current(slug, chapter, verse):
        options.append(human_path(slug, chapter, verse))
    options += [folder / f"{slug}-{chapter}-{verse}.draft-team-gpt.json", folder / f"{slug}-{chapter}-{verse}.draft-gpt56.json"]
    options += sorted(folder.glob(f"{slug}-{chapter}-{verse}.draft-gpt-*.json"), reverse=True)
    return next((path for path in options if path.is_file()), None)


def label_for(candidate: dict, path: Path) -> str:
    if candidate.get("label"):
        return str(candidate["label"])
    return path.name.split(".draft-", 1)[1][:-5] if ".draft-" in path.name else "human-reviewed"


def audit_required(candidate: dict, check: dict) -> bool:
    return bool(candidate.get("uncertainties")) or check.get("verdict") == "fail"


def gate_for(slug: str, chapter: int, verse: int, path: Path, candidate: dict) -> dict:
    if candidate.get("schema") == "lbf-human-reviewed-candidate-v1":
        return {"source": path.name, "fidelity": "human", "spanish": "human"}
    label = label_for(candidate, path)
    folder = pipeline_dir(slug)
    audit = read_json(folder / f"{slug}-{chapter}-{verse}.audit-gpt-{label}.json", {})
    check = read_json(folder / f"{slug}-{chapter}-{verse}.spanish-check-{label}.json", {})
    required = audit_required(candidate, check)
    packet = read_json(packet_path(slug, chapter, verse), {})
    alignment_findings = alignment_precision_findings(packet, candidate.get("units") or [])
    return {"source": path.name, "label": label, "draftModel": candidate.get("model") or "unverified", "draftReasoning": candidate.get("reasoningEffort") or "unverified", "promptCurrent": candidate.get("promptSha256") == draft_prompt_fingerprint(), "auditModel": audit.get("model") or "unverified", "auditReasoning": audit.get("reasoningEffort") or "unverified", "spanishModel": check.get("model") or "unverified", "spanishReasoning": check.get("reasoningEffort") or "unverified", "auditRequired": required, "fidelity": audit.get("verdict") or ("missing" if required else "not-required"), "fidelityFindings": audit.get("findings") or [], "spanish": check.get("verdict") or "missing", "spanishFindings": check.get("findings") or [], "alignmentFindings": alignment_findings}


def human_precedents(slug: str) -> list[dict]:
    """Expose adjudication memory to people, never to a model prompt."""
    rows = []
    for path in sorted(pipeline_dir(slug).glob(f"{slug}-*-*.candidate-human-reviewed.json")):
        item = read_json(path, {})
        adjudication = item.get("adjudication") if isinstance(item, dict) else {}
        decision = str((adjudication or {}).get("decision") or "").strip()
        if not decision:
            continue
        rows.append({"reference": item.get("reference") or path.stem, "decision": decision})
    return rows


def public_packet(packet: dict) -> dict:
    keys = ("sourceTokenId", "position", "surface", "paleo", "lemma", "strongs", "morph", "morphExpanded")
    return {"schema": packet.get("schema"), "sourcePolicy": packet.get("sourcePolicy"), "evidenceStatus": packet.get("evidenceStatus"), "reference": packet.get("reference"), "textualBasis": packet.get("textualBasis"), "tokens": [{k: token.get(k) for k in keys} for token in packet.get("tokens") or []], "syntaxEvidence": packet.get("syntax"), "originalLanguageContext": packet.get("originalLanguageContext") or [], "corpusEvidence": packet.get("corpusEvidence") or [], "lexicalEvidence": packet.get("lexicalEvidence") or []}


def translation_file(slug: str) -> Path:
    book = book_or_raise(slug)
    return ROOT / "translation" / book.testament / f"{slug}.md"


def verse_body(text: str, chapter: int, verse: int) -> str | None:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        match = HEADING.match(line.strip())
        if not match or (int(match.group(1)), int(match.group(2))) != (chapter, verse):
            continue
        body = []
        for item in lines[index + 1:]:
            if item.startswith("### ") or item.startswith("## "):
                break
            if item.strip() and not item.startswith(">"):
                body.append(item.strip())
        return " ".join(body).strip()
    return None


def human_review_is_current(slug: str, chapter: int, verse: int) -> bool:
    """A human artifact only shields the exact Spanish it approved."""
    artifact = read_json(human_path(slug, chapter, verse), {})
    adjudication = artifact.get("adjudication") if isinstance(artifact, dict) else {}
    path = translation_file(slug)
    canonical = path.read_text(encoding="utf-8") if path.is_file() else ""
    return bool(
        artifact.get("schema") == "lbf-human-reviewed-candidate-v1"
        and isinstance(adjudication, dict)
        and adjudication.get("humanApprovedInTeamDesk") is True
        and " ".join(str(artifact.get("spanish") or "").split())
        == " ".join(str(verse_body(canonical, chapter, verse) or "").split())
    )


def chapter_view(slug: str, chapter) -> dict:
    book, number, verses = chapter_or_raise(slug, chapter)
    path = translation_file(slug)
    canonical = path.read_text(encoding="utf-8") if path.is_file() else ""
    recovered = read_json(recovered_path(slug, number), {})
    recovered_verses = recovered.get("verses") if isinstance(recovered, dict) else {}
    recovered_verses = recovered_verses if isinstance(recovered_verses, dict) else {}
    rows = []
    for verse in verses:
        packet = read_json(packet_path(slug, number, verse), {})
        candidate_file = candidate_path(slug, number, verse)
        candidate = read_json(candidate_file, {}) if candidate_file else {}
        recovered_verse = recovered_verses.get(str(verse)) or {}
        # An older failed browser submission may contain the human's text but
        # no alignment rows.  Preserve that text while restoring the model's
        # visible seed as an editable starting point; it remains unapproved
        # and must still pass exact Spanish/unit validation.
        if (
            isinstance(recovered_verse, dict)
            and not recovered_verse.get("units")
            and candidate.get("units")
        ):
            recovered_verse = {**recovered_verse, "units": candidate["units"]}
        rows.append({"verse": verse, "reference": f"{book.label} {number}:{verse}", "canonical": verse_body(canonical, number, verse) or "", "packet": public_packet(packet), "candidate": candidate, "recovered": recovered_verse, "gate": gate_for(slug, number, verse, candidate_file, candidate) if candidate_file else {"source": "missing", "fidelity": "missing", "spanish": "missing"}, "humanReviewed": human_review_is_current(slug, number, verse)})
    return {"book": slug, "label": book.label, "chapter": number, "claim": load_claims().get(claim_key(slug, number)) or {}, "policy": "lbf-source-policy-v4", "textualBasis": "OSHB/WLC", "model": TEAM_MODEL, "reasoningEffort": TEAM_REASONING, "promptSha256": draft_prompt_fingerprint(), "precedents": human_precedents(slug), "precedentBoundary": "Human adjudication memory guides reviewers only. It is never model evidence and never overrides the canonical source packet.", "recoveryNote": recovered.get("note") if isinstance(recovered, dict) else "", "verses": rows}


def _run(args: list[str], *, allow_gate_failure: bool = False) -> None:
    result = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, check=False)
    allowed_returncodes = {0, 1} if allow_gate_failure else {0}
    if result.returncode not in allowed_returncodes:
        raise RuntimeError((result.stderr or result.stdout or "Pipeline command failed").strip())


def prepare_estimate(name, slug, chapter, token="", verse=None) -> dict:
    person = authorize(name, token)
    book, number, verses = chapter_or_raise(slug, chapter)
    with _lock:
        assert_holder(person, book.slug, number)
    selected_verses = verses
    selected_verse = None
    if verse is not None:
        selected_verse = int(verse or 0)
        if selected_verse not in verses:
            raise ValueError("That verse is not in this Protestant chapter.")
        selected_verses = [selected_verse]
    draft_calls = audit_calls = skipped_human = 0
    estimated_input_tokens = 0
    possible_audit_input_tokens = 0
    for verse in selected_verses:
        if human_review_is_current(book.slug, number, verse):
            skipped_human += 1
            continue
        # Preparation always rebuilds the derived packet. Do the same in
        # memory here so a stale stored packet cannot understate paid calls.
        packet = build_packet(book.slug, number, verse)
        path = pipeline_dir(book.slug) / f"{book.slug}-{number}-{verse}.draft-team-gpt.json"
        candidate = read_json(path, {})
        fresh_draft = bool(
            packet
            and path.is_file()
            and candidate.get("model") == TEAM_MODEL
            and candidate.get("reasoningEffort") == TEAM_REASONING
            and candidate.get("packetSha256") == packet_fingerprint(packet)
            and candidate.get("promptSha256") == draft_prompt_fingerprint()
        )
        if not fresh_draft:
            draft_calls += 1
            if packet:
                estimated_input_tokens += estimate_input_tokens(load_draft_system() + build_draft_prompt(packet))
                possible_audit_input_tokens += estimate_input_tokens(AUDIT_SYSTEM + build_audit_prompt(packet, "[candidate]", "team-gpt"))
        current = candidate if fresh_draft else {}
        check = read_json(pipeline_dir(book.slug) / f"{book.slug}-{number}-{verse}.spanish-check-team-gpt.json", {})
        fingerprint = object_fingerprint(candidate) if fresh_draft else ""
        audit = read_json(pipeline_dir(book.slug) / f"{book.slug}-{number}-{verse}.audit-gpt-team-gpt.json", {})
        fresh_audit = fresh_draft and audit.get("model") == TEAM_MODEL and audit.get("reasoningEffort") == TEAM_REASONING and audit.get("candidateSha256") == fingerprint
        if fresh_draft and audit_required(current, check) and not fresh_audit:
            audit_calls += 1
            if packet:
                estimated_input_tokens += estimate_input_tokens(AUDIT_SYSTEM + build_audit_prompt(packet, str(current.get("spanish") or "[candidate]"), "team-gpt"))
    output_cap_tokens = draft_calls * DRAFT_MAX_COMPLETION_TOKENS + audit_calls * AUDIT_MAX_COMPLETION_TOKENS
    conservative_usd = estimated_input_tokens / 1_000_000 * 4 + output_cap_tokens / 1_000_000 * 20
    all_flagged_usd = conservative_usd + possible_audit_input_tokens / 1_000_000 * 4 + draft_calls * AUDIT_MAX_COMPLETION_TOKENS / 1_000_000 * 20
    maximum_paid_calls = draft_calls + audit_calls + draft_calls
    likely_new_audits = math.ceil(draft_calls * 0.5)
    return {
        "book": book.slug,
        "chapter": number,
        "verse": selected_verse,
        "draftCalls": draft_calls,
        "auditCalls": audit_calls,
        "paidCalls": draft_calls + audit_calls,
        "likelyPaidCalls": draft_calls + audit_calls + likely_new_audits,
        "maximumPaidCalls": maximum_paid_calls,
        "humanReviewedSkipped": skipped_human,
        "possibleSelectiveAudits": draft_calls,
        "localSpanishChecks": draft_calls,
        "estimatedLikelyUsd": round(draft_calls * 0.0678 + (audit_calls + likely_new_audits) * 0.0324, 2),
        "estimatedMaximumUsd": round(conservative_usd, 2),
        "estimatedAllFlaggedMaximumUsd": round(all_flagged_usd, 2),
        "note": "Likely cost uses recorded Sol averages and the observed 50% selective-audit rate. Maximum assumes every new draft is flagged and reaches both output caps.",
    }


def prepare(name, slug, chapter, token="", cost_confirmed=False, verse=None) -> None:
    person = authorize(name, token)
    book, number, verses = chapter_or_raise(slug, chapter)
    selected_verse = None
    if verse is not None:
        selected_verse = int(verse or 0)
        if selected_verse not in verses:
            raise ValueError("That verse is not in this Protestant chapter.")
    if not cost_confirmed:
        raise ValueError("Review and confirm the preparation cost estimate first.")
    with _lock:
        _, key = assert_holder(person, slug, number)
        if _alive(key):
            raise ValueError("This chapter is already being prepared.")
        if sum(_alive(item) for item in _threads) >= MAX_RUNNING:
            raise ValueError("All preparation workers are occupied.")
        event = threading.Event()
        _stops[key] = event
        _threads[key] = threading.Thread(target=_prepare, args=(book.slug, number, event, selected_verse), daemon=True)
        claims = load_claims(); claims[key].update(running=True, note=(f"Preparing {number}:{selected_verse}" if selected_verse else "Preparing GPT gates"), updated=now()); save_claims(claims)
        _threads[key].start()


def _prepare(slug: str, chapter: int, event: threading.Event, only_verse: int | None = None) -> None:
    key, error = claim_key(slug, chapter), ""
    try:
        verses = list_verses(slug, chapter)
        if only_verse is not None:
            if only_verse not in verses:
                raise ValueError("That verse is not in this Protestant chapter.")
            verses = [only_verse]
        for verse in verses:
            if event.is_set(): break
            if human_review_is_current(slug, chapter, verse):
                continue
            with _lock:
                claims = load_claims(); claims[key].update(verse=verse, note=f"Preparing {chapter}:{verse}", updated=now()); save_claims(claims)
            # Rebuild the derived packet from pinned sources. A stale packet
            # from an earlier policy must never reach GPT-5.6 Sol.
            _run([sys.executable, str(PIPELINE / "build_source_packet.py"), slug, str(chapter), str(verse)])
            path = pipeline_dir(slug) / f"{slug}-{chapter}-{verse}.draft-team-gpt.json"
            candidate = read_json(path, {})
            if candidate.get("schema") == "lbf-human-reviewed-candidate-v1": continue
            packet = read_json(packet_path(slug, chapter, verse), {})
            if not path.is_file() or candidate.get("model") != TEAM_MODEL or candidate.get("reasoningEffort") != TEAM_REASONING or candidate.get("packetSha256") != packet_fingerprint(packet) or candidate.get("promptSha256") != draft_prompt_fingerprint():
                _run([sys.executable, str(PIPELINE / "draft_gpt.py"), slug, str(chapter), str(verse), "--label", "team-gpt"])
                path = pipeline_dir(slug) / f"{slug}-{chapter}-{verse}.draft-team-gpt.json"; candidate = read_json(path, {})
            label = label_for(candidate, path); folder = pipeline_dir(slug)
            check = folder / f"{slug}-{chapter}-{verse}.spanish-check-{label}.json"
            audit = folder / f"{slug}-{chapter}-{verse}.audit-gpt-{label}.json"
            check_data = read_json(check, {})
            fingerprint = object_fingerprint(candidate)
            if check_data.get("model") != SPANISH_GATE_MODEL or check_data.get("candidateSha256") != fingerprint: _run([sys.executable, str(PIPELINE / "spanish_check_local.py"), slug, str(chapter), str(verse), "--candidate-file", str(path), "--label", label], allow_gate_failure=True)
            check_data = read_json(check, {})
            audit_data = read_json(audit, {})
            if audit_required(candidate, check_data) and (audit_data.get("model") != TEAM_MODEL or audit_data.get("reasoningEffort") != TEAM_REASONING or audit_data.get("candidateSha256") != fingerprint): _run([sys.executable, str(PIPELINE / "audit_gpt.py"), slug, str(chapter), str(verse), "--candidate-file", str(path), "--label", label], allow_gate_failure=True)
    except Exception as exc:  # noqa: BLE001
        error = str(exc)
    with _lock:
        claims = load_claims()
        if key in claims:
            claims[key].update(running=False, note=(f"Preparation stopped: {error}" if error else ("Preparation stopped" if event.is_set() else "Ready for human review")), updated=now()); save_claims(claims)


def stop(name, slug, chapter, token="") -> None:
    person = authorize(name, token); book, number, _ = chapter_or_raise(slug, chapter)
    with _lock:
        _, key = assert_holder(person, book.slug, number)
        if key in _stops: _stops[key].set()


def audit_verse(payload: dict) -> dict:
    person = authorize(payload.get("name"), payload.get("token"))
    book, chapter, verses = chapter_or_raise(payload.get("book"), payload.get("chapter"))
    verse = int(payload.get("verse") or 0)
    if verse not in verses:
        raise ValueError("That verse is not in this Protestant chapter.")
    with _lock:
        assert_holder(person, book.slug, chapter)
    path = candidate_path(book.slug, chapter, verse)
    candidate = read_json(path, {}) if path else {}
    if not path or candidate.get("schema") == "lbf-human-reviewed-candidate-v1":
        raise ValueError("Prepare an unapproved GPT candidate before requesting an audit.")
    packet = read_json(packet_path(book.slug, chapter, verse), {})
    if candidate.get("packetSha256") != packet_fingerprint(packet):
        raise ValueError("Prepare this verse again before requesting an audit.")
    if candidate.get("model") != TEAM_MODEL or candidate.get("reasoningEffort") != TEAM_REASONING or candidate.get("promptSha256") != draft_prompt_fingerprint():
        raise ValueError("Prepare this verse with the current GPT and alignment specification before requesting an audit.")
    label = label_for(candidate, path)
    audit_path = pipeline_dir(book.slug) / f"{book.slug}-{chapter}-{verse}.audit-gpt-{label}.json"
    existing = read_json(audit_path, {})
    fingerprint = object_fingerprint(candidate)
    if existing.get("model") != TEAM_MODEL or existing.get("reasoningEffort") != TEAM_REASONING or existing.get("candidateSha256") != fingerprint:
        _run([sys.executable, str(PIPELINE / "audit_gpt.py"), book.slug, str(chapter), str(verse), "--candidate-file", str(path), "--label", label], allow_gate_failure=True)
    return chapter_view(book.slug, chapter)


def validate_units(packet: dict, units, spanish: str = "") -> list[dict]:
    if not isinstance(units, list) or not units: raise ValueError("Alignment units are required.")
    tokens = packet.get("tokens") or []
    allowed = {str(t.get("sourceTokenId")) for t in tokens}; covered = set(); clean = []
    for unit in units:
        surface = " ".join(str((unit or {}).get("es") or "").split()); ids = [str(x) for x in ((unit or {}).get("sourceTokenIds") or [])]
        if not surface or not ids: raise ValueError("Every alignment unit needs Spanish and source tokens.")
        if set(ids) - allowed: raise ValueError("An alignment unit contains an unknown source token.")
        covered.update(ids); clean.append({"es": surface, "sourceTokenIds": ids})
    precision = alignment_precision_findings(packet, clean)
    if precision:
        finding = precision[0]
        raise ValueError(f'{finding["issue"]} Spanish unit: "{finding["spanishSpan"]}"')
    if allowed - covered: raise ValueError("The alignment omits source tokens: " + ", ".join(sorted(allowed - covered)))
    if spanish:
        words = lambda value: [x.casefold() for x in re.findall(r"\w+", value, re.UNICODE)]
        if words(" ".join(unit["es"] for unit in clean)) != words(spanish):
            raise ValueError("The ordered alignment units do not reproduce the complete approved Spanish wording.")
    return clean


def invalidate_status(slug: str) -> None:
    lines = STATUS.read_text(encoding="utf-8").splitlines(); found = False
    for index, line in enumerate(lines):
        if not line.startswith("| "): continue
        cells = [x.strip() for x in line[1:-1].split("|")]
        if len(cells) != len(STATUS_COLUMNS) or cells[0] != slug: continue
        found = True; row = dict(zip(STATUS_COLUMNS, cells, strict=True))
        row.update(translation="draft", translation_by="", translation_on="", alignment_by="", alignment_on="")
        if row["alignment"] != "none": row["alignment"] = "draft"
        lines[index] = "| " + " | ".join(row[key] for key in STATUS_COLUMNS) + " |"; break
    if not found: raise ValueError(f"{slug} is not in STATUS.md")
    STATUS.write_text("\n".join(lines) + "\n", encoding="utf-8")


def approve_verse(payload: dict) -> dict:
    person = authorize(payload.get("name"), payload.get("token")); book, chapter, verses = chapter_or_raise(payload.get("book"), payload.get("chapter")); verse = int(payload.get("verse") or 0)
    if verse not in verses: raise ValueError("That verse is not in this Protestant chapter.")
    with _lock:
        assert_holder(person, book.slug, chapter)
        save_review_attempt(book, chapter, verse, person, payload)
        packet = read_json(packet_path(book.slug, chapter, verse), {})
        if packet.get("sourcePolicy") != "lbf-source-policy-v4" or packet.get("evidenceStatus") != "READY_FOR_MODEL": raise ValueError("The canonical packet is not READY_FOR_MODEL under lbf-source-policy-v4.")
        if not payload.get("sourceConfirmed"): raise ValueError("Confirm the complete source-evidence review.")
        if not payload.get("alignmentConfirmed"): raise ValueError("Confirm every visible Spanish-to-source link.")
        if not payload.get("suppliedConfirmed"): raise ValueError("Confirm that every supplied Spanish word is marked in italics.")
        spanish = " ".join(str(payload.get("spanish") or "").split()); units = validate_units(packet, payload.get("units"), spanish)
        if not spanish: raise ValueError("Spanish text is required.")
        policy_findings = [*lint_spanish(spanish), *lint_divine_name(spanish, packet)]
        if policy_findings:
            raise ValueError("Spanish policy failed: " + "; ".join(item["issue"] for item in policy_findings))
        prior_path = candidate_path(book.slug, chapter, verse); prior = read_json(prior_path, {}) if prior_path else {}; decision = " ".join(str(payload.get("decision") or "").split())
        if prior.get("schema") != "lbf-human-reviewed-candidate-v1":
            if prior.get("model") != TEAM_MODEL:
                raise ValueError("This candidate is not proven to have been drafted by GPT-5.6 Sol. Prepare this verse again.")
            if prior.get("reasoningEffort") != TEAM_REASONING:
                raise ValueError("This candidate was not drafted with the required medium reasoning effort. Prepare this verse again.")
            if prior.get("packetSha256") != packet_fingerprint(packet):
                raise ValueError("This candidate is not bound to the current canonical packet. Prepare this verse again.")
            if prior.get("promptSha256") != draft_prompt_fingerprint():
                raise ValueError("This candidate was created under an older translation or alignment specification. Prepare this verse again.")
            gate = gate_for(book.slug, chapter, verse, prior_path, prior)
            if gate["spanish"] == "missing":
                raise ValueError("The deterministic Spanish gate must run before human adjudication.")
            if gate["spanishModel"] != SPANISH_GATE_MODEL or gate["spanishReasoning"] != "none":
                raise ValueError("The Spanish gate must be deterministic local lint.")
            if gate["auditRequired"] and gate["fidelity"] == "missing":
                raise ValueError("This flagged candidate requires an independent GPT-5.6 Sol fidelity audit.")
            if gate["fidelity"] not in {"missing", "not-required"} and (gate["auditModel"] != TEAM_MODEL or gate["auditReasoning"] != TEAM_REASONING):
                raise ValueError("Any fidelity audit must use GPT-5.6 Sol with medium reasoning.")
            enforce_human_adjudication(prior, gate, spanish, decision, bool(payload.get("auditOverrideConfirmed")))
        artifact = {"schema": "lbf-human-reviewed-candidate-v1", "book": book.slug, "reference": f"{book.label} {chapter}:{verse}", "chapter": chapter, "verse": verse, "sourcePolicy": packet.get("sourcePolicy"), "packetSha256": packet_fingerprint(packet), "spanish": spanish, "units": units, "adjudication": {"status": "approved", "decision": decision or "The named reviewer confirmed the wording against the complete canonical packet.", "reviewedBy": person, "reviewedOn": today(), "humanApprovedInTeamDesk": True, "sourceEvidenceConfirmed": True, "alignmentUnitsConfirmed": True, "suppliedWordsConfirmed": True, "failedAuditOverrideConfirmed": bool(payload.get("auditOverrideConfirmed")), "scope": "verse wording and alignment seed; not STATUS.md done approval"}}
        current_path = translation_file(book.slug)
        current_text = current_path.read_text(encoding="utf-8") if current_path.is_file() else ""
        changed = verse_body(current_text, chapter, verse) != spanish
        if changed:
            invalidate_status(book.slug)
            write_verse(book.slug, chapter, verse, spanish)
        write_json(human_path(book.slug, chapter, verse), artifact)
        claims, key = assert_holder(person, book.slug, chapter); claims[key].update(verse=verse, note=f"Approved {chapter}:{verse}; alignment seed confirmed", updated=now()); save_claims(claims)
    return chapter_view(book.slug, chapter)


def finish_chapter(payload: dict) -> dict:
    person = authorize(payload.get("name"), payload.get("token")); book, chapter, verses = chapter_or_raise(payload.get("book"), payload.get("chapter"))
    if not payload.get("contextConfirmed"): raise ValueError("Confirm the complete chapter continuity, voice, and flow review.")
    with _lock:
        claims, key = assert_holder(person, book.slug, chapter); missing = [v for v in verses if not human_review_is_current(book.slug, chapter, v)]
        if missing: raise ValueError("Human review is missing for verse(s): " + ", ".join(map(str, missing)))
        write_json(pipeline_dir(book.slug) / f"{book.slug}-{chapter}.human-review.json", {"schema": "lbf-human-chapter-review-v1", "book": book.slug, "chapter": chapter, "reviewedBy": person, "reviewedOn": today(), "continuityVoiceFlowConfirmed": True, "verseWordingConfirmed": verses, "alignmentSeedsConfirmed": verses, "statusScope": "chapter review only; not STATUS.md done and not canonical alignment"})
        write_json(pipeline_dir(book.slug) / f"{book.slug}-{chapter}.alignment-seed.json", {"schema": "lbf-alignment-seed-manifest-v1", "book": book.slug, "chapter": chapter, "status": "seeded-hand", "canonicalAlignmentChanged": False, "instruction": "Named reviewers confirmed these visible unit links. They remain a noncanonical seed until copied into and validated in the canonical reverse-links file.", "verses": [{"verse": v, "candidate": human_path(book.slug, chapter, v).name, "confirmed": True} for v in verses]})
        claims[key].update(note="Chapter review complete; canonical alignment still pending", updated=now()); save_claims(claims)
    return chapter_view(book.slug, chapter)


def chapter_count(slug: str) -> int:
    if slug not in _chapter_counts:
        # The Markdown headings use Protestant numbering and make a cheap UI
        # index. Source existence is still checked by chapter_or_raise.
        path = translation_file(slug)
        headings = [int(x) for x in re.findall(r"^## Capítulo (\d+)\s*$", path.read_text(encoding="utf-8"), re.MULTILINE)] if path.is_file() else []
        count = max(headings, default=0)
        _chapter_counts[slug] = count
    return _chapter_counts[slug]


def board() -> dict:
    return {"model": model_name(), "reasoningEffort": reasoning_effort(), "sourcePolicy": "lbf-source-policy-v4", "textualBasis": "OSHB/WLC", "maxRunning": MAX_RUNNING, "running": sum(_alive(k) for k in _threads), "people": sorted(load_people()), "books": [{"slug": b.slug, "label": b.label, "chapters": chapter_count(b.slug)} for b in OT], "claims": load_claims(), "ntBlocked": True}


def warm_totals() -> None:
    for book in OT: chapter_count(book.slug)
