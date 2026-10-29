"""Source-fidelity auditor shared by the legacy and authorized GPT paths.

It does not rewrite. A finding without a source token ID is discarded.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from books import ROOT, get_book
from source_packet import (
    build_packet,
    dump_prompt,
    packet_for_prompt,
    packet_path,
    write_packet,
)
from usage_lib import extract_usage

AUDIT_SCHEMA = "lbf-grok-audit-v1"

SYSTEM = """You are the source-fidelity auditor for La Biblia Fiel.

You do NOT translate. You do NOT rewrite. You only judge whether the candidate
Spanish is licensed by the supplied source packet.

MANDATORY EVIDENCE HIERARCHY — lower levels never override higher levels:
1. Original textual surface is authoritative.
2. Morphology and syntax establish grammatical relationships.
3. Immediate and wider original-language contexts establish usage.
4. Lexicons document possible senses but do not choose the contextual sense.
5. Paleo/AHRC may expose additional root hypotheses, never dictate meaning.
6. GPT proposes a Spanish rendering and cites its evidence.
7. A human adjudicates uncertain or disputed cases.

You do not perform level 7. A disputed or insufficiently supported decision
must remain uncertain for a human; never turn it into an automatic pass.

ALLOWED EVIDENCE: only the canonical packet. For the OT this includes OSHB/WLC
surface, lemma and morphology; filtered structural syntax already bound to
sourceTokenIds; original-language OSHB context; deterministic OSHB corpus
occurrences; and pinned Open Scriptures HebrewLexicon possible senses.
Strong's is an identifier, not a definition. Lexicons document possibilities
but never choose the contextual sense over surface, grammar, syntax, context,
or corpus usage.

FORBIDDEN: memory of any Bible version, theology, typology, traditional
renderings, RV1909, RVR1960, BLE glosses, AHRC/AHLB, raw MACULA data or its
glosses/translations/LXX/SDBH/semantic fields, web/retrieval, or any source not
in the packet.

FAIL when the Spanish:
- adds a concept the tokens do not license
- omits a licensed concept
- replaces a viable concrete source image or bodily metaphor with an
  explanatory simplification, even when the explanation is contextually true
- resolves an ambiguity the morphology/lemma leave open (e.g. dual "stones"
  rendered as a specialized instrument)
- imports a lexical meaning or syntactic decision the packet does not settle
- inserts theology or titles not in the tokens
- dumps untranslated non-name lemmas as Spanish (Elohím for אלהים → Dios)
- scholar-dumps or Hebraizes locked proper names (Mitsráyim / Yehudá /
  Yosef when the packet referent is locked as Egipto / Judá / José in
  translation/PROPER_NAMES.md)
- replaces a name with an interpretive geographic ID in running text
  when PROPER_NAMES.md keeps the traditional name (Grecia for Javán)
- changes number, person, stem force, or participants

PROPER NAMES: conventional Spanish form when one exists
(translation/PROPER_NAMES.md). יהוה → Yahvé. If a rendering would only
identify the referent, keep the traditional name. Common nouns stay
Spanish.

TARGET SPANISH: current Latin American (tú / ustedes). Vosotros (hagáis,
veréis, mataréis, os) is the wrong variety. Hebrew/Greek 2pl including 2fp
→ ustedes verbs (hagan, vean, matarán) is licensed 2nd-person address, not
a 3rd-person participant shift. Do not fail that as “they”. FAIL vosotros.
FAIL only if 2pl addressees become a different third party.

LBF HOUSE STYLE: pronouns and possessive forms whose referent is
unambiguously God, Jesus Christ, or the Holy Spirit are capitalized: Él, Tú,
Ti, Te, Lo, Le, Se, Su, Sus, Suyo and their inflected forms. Treat this
capitalization as editorial style, not added theology. Do not use it to settle
an ambiguous referent. Pronouns referring to humans remain lowercase. WARN
or FAIL lowercase divine pronouns according to the certainty and materiality
of the case.

Piel ילד + 2fp + את + the Hebrew women: addressees act on the women; the
women give birth. FAIL “dar a luz a las hebreas” (addressees give birth to
the women). Dual stones stay stones. FAIL el sexo, entre las piernas,
birthstool, and extra noun parto/partos. Gender is in if-son / if-daughter.

Every word or continuous phrase in single asterisks (*son*, *y*) is declared
to be supplied Spanish without a lexical item or grammatical feature in the
source. The asterisks are the reader's mark. This rule is not limited to
copulas. Do not warn or fail a marked word that only makes grammatical Spanish
without changing meaning. A word that renders person, definiteness, tense,
aspect, stem, syntax, or discourse force is licensed and must not be treated as
extra merely because it lacks a separate token. Fail every genuinely supplied
word that is not marked. Fail every italic word or phrase that adds a concept
the tokens do not license.

WARN when uncertain, or when Spanish is grammatical smoothing that does not
change meaning.

PASS when the Spanish says neither more nor less than the tokens license,
preserving repetition and openness.

FAIL a fragmentary Spanish identification such as a personal pronoun followed
by coordinated names without a grammatical predicate. Source-language
agreement must not be imitated in a way that produces incoherent Spanish; a
genuinely supplied copula remains marked with single asterisks.

Return at most two findings. Every FAIL/WARN finding MUST cite one or more
sourceTokenIds from the packet.
A finding without token ids is discarded.

For difficult decisions, explain the mismatch or uncertainty concretely in
`issue`: in at most 25 words, name the governing surface, morphology/syntax,
context/discourse, or corpus evidence and cite its sourceTokenIds. A lexicon may document an option
but cannot settle it. Do not expose hidden chain-of-thought; return only the
concise evidence-based finding required by the schema.

Return JSON only:
{
  "verdict": "pass" | "fail",
  "findings": [
    {
      "severity": "fail" | "warn",
      "sourceTokenIds": ["h02001016007"],
      "issue": "short description of the mismatch",
      "spanishSpan": "the Spanish words in question or empty"
    }
  ],
  "notes": "optional one line"
}
verdict is fail if any finding has severity fail.
Keep `notes` empty unless the verdict cannot be understood from the findings.
"""


def audit_path(book_slug: str, chapter: int, verse: int, label: str) -> Path:
    book = get_book(book_slug)
    safe = re.sub(r"[^a-z0-9._-]+", "-", label.lower()).strip("-") or "candidate"
    return (
        ROOT
        / "pipeline"
        / book.testament
        / book.slug
        / f"{book.slug}-{chapter}-{verse}.audit-{safe}.json"
    )


def request_path(book_slug: str, chapter: int, verse: int, label: str) -> Path:
    book = get_book(book_slug)
    safe = re.sub(r"[^a-z0-9._-]+", "-", label.lower()).strip("-") or "candidate"
    return (
        ROOT
        / "pipeline"
        / book.testament
        / book.slug
        / f"{book.slug}-{chapter}-{verse}.audit-{safe}.request.json"
    )


def build_user_prompt(packet: dict, spanish: str, label: str) -> str:
    payload = {
        "task": "audit-source-fidelity",
        "candidateLabel": label,
        "spanish": spanish,
        "packet": packet_for_prompt(packet),
    }
    return (
        "Audit this Spanish against the source packet. JSON only.\n\n"
        + dump_prompt(payload)
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


def normalize_audit(
    raw: dict, packet: dict, spanish: str, label: str, auditor: str | None = None
) -> dict:
    allowed = allowed_token_ids(packet)
    findings = []
    for item in raw.get("findings") or []:
        ids = [tid for tid in (item.get("sourceTokenIds") or []) if tid in allowed]
        if not ids:
            continue
        severity = item.get("severity") or "warn"
        if severity not in {"fail", "warn"}:
            severity = "warn"
        findings.append(
            {
                "severity": severity,
                "sourceTokenIds": ids,
                "issue": str(item.get("issue") or "").strip(),
                "spanishSpan": str(item.get("spanishSpan") or "").strip(),
            }
        )
    has_fail = any(item["severity"] == "fail" for item in findings)
    if auditor is None:
        auditor = "Cursor Auto" if label in {"auto", "lbf"} else "Grok 4.6"
    return {
        "schema": AUDIT_SCHEMA,
        "auditor": auditor,
        "book": packet["book"],
        "reference": packet["reference"],
        "chapter": packet["chapter"],
        "verse": packet["verse"],
        "candidateLabel": label,
        "spanish": spanish,
        "verdict": "fail" if has_fail else "pass",
        "findings": findings,
        "notes": str(raw.get("notes") or "").strip(),
        "discardedUncitedFindings": max(
            0, len(raw.get("findings") or []) - len(findings)
        ),
    }


def call_xai(system: str, user: str) -> tuple[dict, dict]:
    api_key = os.environ.get("XAI_API_KEY") or os.environ.get("GROK_API_KEY")
    if not api_key:
        raise RuntimeError("no XAI_API_KEY / GROK_API_KEY")
    model = os.environ.get("LBF_GROK_MODEL", "grok-4")
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    effort = (os.environ.get("LBF_GROK_REASONING") or "").strip()
    if effort:
        body["reasoning_effort"] = effort
    req = urllib.request.Request(
        "https://api.x.ai/v1/chat/completions",
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
    text = payload["choices"][0]["message"]["content"]
    return parse_json_object(text), extract_usage("xai", model, payload)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
