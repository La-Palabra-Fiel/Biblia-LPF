"""Named-human chapter review for the closed LBF GPT workflow.

Models prepare evidence-bound candidates. Only the explicit review action
writes canonical Spanish. This module never writes a `done` status. Explicit
chapter approval promotes the already-confirmed units to canonical alignment;
book completion remains a separate named-human approval.
"""

from __future__ import annotations

import json
import hashlib
import math
import os
import re
import base64
import secrets
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PIPELINE = ROOT / "tools" / "pipeline"
sys.path.insert(0, str(PIPELINE))
sys.path.insert(0, str(ROOT / "tools"))
import env_load  # noqa: E402,F401
from publication_progress import demote_chapter_alignment, promote_chapter_alignment  # noqa: E402
from draft_lib import COMPATIBLE_TEAM_DRAFT_MODELS, TEAM_DRAFT_MODEL, TEAM_DRAFT_MODEL_REVIEW_ON, TEAM_DRAFT_REASONING  # noqa: E402
from usage_lib import rates_for  # noqa: E402
from json_io import write_json_atomic  # noqa: E402

# The team workflow is deliberately not model-configurable. Changing this is a
# policy change, not an operator preference.
TEAM_MODEL = TEAM_DRAFT_MODEL
TEAM_REASONING = TEAM_DRAFT_REASONING
TEAM_MODEL_REVIEW_ON = TEAM_DRAFT_MODEL_REVIEW_ON
TEAM_RATES = rates_for({"provider": "openai", "model": TEAM_MODEL})
COMPATIBLE_DRAFT_REASONING = {"low", "medium"}
SPANISH_GATE_MODEL = "deterministic-local"
os.environ["LBF_GPT_MODEL"] = TEAM_MODEL
os.environ["LBF_GPT_REASONING"] = TEAM_REASONING

from auto_pass import write_verse  # noqa: E402
from books import NT, OT, get_book  # noqa: E402
from nt_macula import (  # noqa: E402
    MAPPING_POLICY as NT_MACULA_MAPPING_POLICY,
    TR_AUTHORITY_FALLBACK_RULE,
    mapping_sha256,
    validate_candidate as validate_nt_syntax_candidate,
    validate_mapping_ledger as validate_nt_mapping_ledger,
)
from nt_source import TR_CODE_BY_STEM, load_reconciled_verse  # noqa: E402
from lint_lib import lint_divine_name, lint_spanish  # noqa: E402
from source_packet import build_packet, canonical_editorial_policy_fields, list_verses  # noqa: E402
from draft_lib import DRAFT_EXPECTED_COMPLETION_TOKENS, DRAFT_MAX_COMPLETION_TOKENS, DRAFT_SPEC_VERSION, alignment_precision_findings, build_user_prompt as build_draft_prompt, draft_specification_is_current, lexical_alignment_surface, load_system as load_draft_system, merge_source_units_by_id, prompt_fingerprint as draft_prompt_fingerprint  # noqa: E402
from audit_gpt import AUDIT_MAX_COMPLETION_TOKENS  # noqa: E402
from audit_lib import SYSTEM as AUDIT_SYSTEM, build_user_prompt as build_audit_prompt  # noqa: E402

HEADING = re.compile(r"^###\s+(\d+):(\d+)\s*$")
STATUS_COLUMNS = ("book", "testament", "translation", "alignment", "translation_by", "translation_on", "alignment_by", "alignment_on", "notes")
VAR = Path(os.environ.get("LBF_TEAM_DATA_DIR") or (Path(__file__).resolve().parent / "var")).expanduser().resolve()
CLAIMS, PEOPLE = VAR / "claims.json", VAR / "people.json"
PEER_REVIEWS = VAR / "peer-review-signoffs.json"
RECOVERED = VAR / "recovered-reviews"
STATUS = ROOT / "STATUS.md"
NT_SYNTAX_CANDIDATES = ROOT / "nt-syntax" / "candidates"
NT_MACULA_MAPPING = ROOT / "source" / "greek" / "TR1894" / "macula-structure-mapping.json"
NT_MACULA_MANIFEST = ROOT / "source" / "greek" / "TR1894" / "MACULA_GREEK_MANIFEST.json"
NT_STRUCTURE_ADJUDICATIONS = ROOT / "source" / "greek" / "TR1894" / "MACULA_STRUCTURE_ADJUDICATIONS.json"
MAX_RUNNING = max(1, int(os.environ.get("LBF_TEAM_WORKERS", "4")))
_lock = threading.RLock()
_threads: dict[str, threading.Thread] = {}
_stops: dict[str, threading.Event] = {}
_chapter_counts: dict[str, int] = {}
_nt_mapping_cache: tuple[str, dict] | None = None
_nt_syntax_board_cache: tuple[str, dict] | None = None
_nt_syntax_board_lock = threading.Lock()
_estimate_packet_cache: dict[tuple[str, str, int, int | None], tuple[float, dict[int, dict]]] = {}
ESTIMATE_PACKET_CACHE_SECONDS = 120

# Measured across the stored Sol requests, input tokens are at most
# about 0.341 per UTF-8 byte. Keep a small safety margin without incorrectly
# charging every byte as a full token in the preflight estimate.
INPUT_TOKENS_PER_UTF8_BYTE = 0.36
REVIEW_SPEC_VERSION = "lbf-team-review-v3"
DEFAULT_DECISION = "The named reviewer confirmed the wording against the complete canonical packet."
DECISION_CATEGORIES = {
    "confirmed",
    "lexical",
    "syntax",
    "agreement",
    "supplied",
    "proper-name",
    "natural-spanish",
    "alignment",
    "punctuation",
    "verse-specific",
}


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
    write_json_atomic(path, value)


def canonical_alignment_units(slug: str, testament: str, reference: str) -> list[dict]:
    """Load an existing canonical reverse alignment as an editable review seed."""
    path = ROOT / "alignment" / testament / slug / f"{slug}-reverse-links.json"
    document = read_json(path, {})
    links = document.get("links") if isinstance(document, dict) else []
    phrase = next(
        (row for row in (links or []) if isinstance(row, dict) and row.get("reference") == reference),
        None,
    )
    if not phrase:
        return []
    units: list[dict] = []
    for unit in phrase.get("units") or []:
        surface = lexical_alignment_surface((unit or {}).get("surface") or "")
        source_ids = list(
            dict.fromkeys(
                str(value)
                for value in ((unit or {}).get("sourceTokenIds") or [])
                if str(value)
            )
        )
        if surface and source_ids:
            units.append({"es": surface, "sourceTokenIds": source_ids})
    return units


def packet_fingerprint(packet: dict) -> str:
    raw = json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def object_fingerprint(value: dict) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def file_fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_fingerprint(value: str) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def alignment_surface_tokens(value: str, *, preserve_supplied: bool = True) -> list[str]:
    """Compare alignment surface while ignoring punctuation, not supplied markup."""
    tokens: list[str] = []
    for match in re.finditer(r"(?<!\*)\*([^*\n]+)\*(?!\*)|\w+", str(value or ""), re.UNICODE):
        supplied = match.group(1)
        if supplied is None:
            tokens.append(match.group(0).casefold())
            continue
        words = re.findall(r"\w+", supplied, re.UNICODE)
        tokens.extend((f"*{word.casefold()}*" if preserve_supplied else word.casefold()) for word in words)
    return tokens


def alignment_preflight_findings(packet: dict, units, spanish: str = "") -> tuple[list[dict], list[dict]]:
    """Return normalized units and deterministic review findings without writing data."""
    findings: list[dict] = []
    if not isinstance(units, list) or not units:
        return [], [{"severity": "fail", "code": "units-required", "issue": "Alignment units are required.", "sourceTokenIds": []}]
    tokens = packet.get("tokens") or []
    allowed = {str(token.get("sourceTokenId")) for token in tokens if token.get("sourceTokenId")}
    covered: set[str] = set()
    clean: list[dict] = []
    for index, unit in enumerate(units, start=1):
        surface = lexical_alignment_surface((unit or {}).get("es") or "")
        ids = list(dict.fromkeys(str(value) for value in ((unit or {}).get("sourceTokenIds") or []) if str(value)))
        if not surface or not ids:
            findings.append({"severity": "fail", "code": "unit-incomplete", "issue": f"Alignment unit {index} needs Spanish and source tokens.", "sourceTokenIds": ids, "spanishSpan": surface})
            continue
        unknown = sorted(set(ids) - allowed)
        if unknown:
            findings.append({"severity": "fail", "code": "unknown-source-token", "issue": "An alignment unit contains unknown source tokens: " + ", ".join(unknown), "sourceTokenIds": unknown, "spanishSpan": surface})
        valid_ids = [token_id for token_id in ids if token_id in allowed]
        covered.update(valid_ids)
        clean.append({"es": surface, "sourceTokenIds": valid_ids})
    clean = merge_source_units_by_id(clean)
    findings.extend(alignment_precision_findings(packet, clean))
    missing = sorted(allowed - covered)
    if missing:
        findings.append({"severity": "fail", "code": "missing-source-tokens", "issue": "The alignment omits source tokens: " + ", ".join(missing), "sourceTokenIds": missing})
    if spanish and clean:
        unit_text = " ".join(unit["es"] for unit in clean)
        marked_units = alignment_surface_tokens(unit_text)
        marked_spanish = alignment_surface_tokens(spanish)
        if marked_units != marked_spanish:
            plain_units = alignment_surface_tokens(unit_text, preserve_supplied=False)
            plain_spanish = alignment_surface_tokens(spanish, preserve_supplied=False)
            if plain_units == plain_spanish:
                issue = "Supplied-word italics differ between the approved Spanish and the alignment units."
                code = "supplied-markup-mismatch"
            else:
                issue = "The ordered alignment units do not reproduce the complete approved Spanish wording."
                code = "spanish-reconstruction"
            findings.append({"severity": "fail", "code": code, "issue": issue, "sourceTokenIds": []})
    return clean, findings


def approval_binding(spanish: str, units: list[dict], packet: dict) -> dict:
    """Record future provenance without invalidating grandfathered approvals."""
    return {
        "reviewSpecVersion": REVIEW_SPEC_VERSION,
        "spanishSha256": text_fingerprint(spanish),
        "unitsSha256": object_fingerprint({"units": units}),
        "packetSha256": packet_fingerprint(packet),
        "sourcePolicy": packet.get("sourcePolicy"),
        "rulesSha256": draft_prompt_fingerprint(),
    }


def estimate_input_tokens(text: str) -> int:
    return math.ceil(len(text.encode("utf-8")) * INPUT_TOKENS_PER_UTF8_BYTE)


def enforce_human_adjudication(prior: dict, gate: dict, spanish: str, decision: str, override_confirmed: bool) -> None:
    # A missing optional model audit is not a defect.  The named human is the
    # approval authority and the deterministic Spanish/source checks run
    # locally below.  Require written adjudication only for an actual failed
    # audit or an uncertainty already recorded in the seed.
    needs_adjudication = gate.get("fidelity") == "fail" or bool(prior.get("uncertainties"))
    if needs_adjudication and not decision:
        raise ValueError("Write your own human adjudication for every failed gate or model uncertainty; the app will not manufacture one.")
    unchanged = spanish == " ".join(str(prior.get("spanish") or "").split())
    if gate.get("fidelity") == "fail" and unchanged and not override_confirmed:
        raise ValueError("The independent audit failed this unchanged wording. Correct it, or explicitly confirm a reasoned human override.")


def load_claims() -> dict:
    with _lock:
        data = read_json(CLAIMS, {})
    return data if isinstance(data, dict) else {}


def save_claims(value: dict) -> None:
    with _lock:
        # Windows can refuse an atomic replace while another program has the
        # ledger open. Retry briefly without changing the atomic write.
        for delay in (0.05, 0.10, 0.20, 0.40):
            try:
                write_json(CLAIMS, value)
                return
            except PermissionError as exc:
                if getattr(exc, "winerror", None) not in (5, 32):
                    raise
                time.sleep(delay)
        write_json(CLAIMS, value)


def load_people() -> dict:
    try:
        data = read_json(PEOPLE, {})
    except json.JSONDecodeError:
        if os.environ.get("LBF_TEAM_ENV", "development").casefold() == "production":
            raise
        # Local-only compatibility for one historical hand-edited file.
        # Production remains strict, and manage_users.py rewrites valid JSON.
        raw = PEOPLE.read_text(encoding="utf-8")
        data = json.loads(re.sub(r",\s*([}\]])", r"\1", raw))
    return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}


SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1


def hashed_credential(secret: str) -> str:
    """Create a password-verifier record; the original secret is never stored."""
    value = str(secret or "")
    if not 12 <= len(value) <= 256:
        raise ValueError("Reviewer credentials must contain 12 to 256 characters.")
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(value.encode("utf-8"), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32)
    encoded_salt = base64.urlsafe_b64encode(salt).decode("ascii").rstrip("=")
    encoded_digest = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${encoded_salt}${encoded_digest}"


def credential_is_hashed(value: str) -> bool:
    return str(value or "").startswith("scrypt$")


def _decode_credential_part(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def verify_credential(secret: str, stored: str, *, allow_plaintext: bool = True) -> bool:
    """Compare a submitted credential without disclosing timing information."""
    record = str(stored or "")
    submitted = str(secret or "").strip()
    if len(submitted) > 256:
        return False
    if not credential_is_hashed(record):
        return allow_plaintext and secrets.compare_digest(submitted, record)
    try:
        algorithm, n, r, p, encoded_salt, encoded_digest = record.split("$", 5)
        if algorithm != "scrypt":
            return False
        parameters = (int(n), int(r), int(p))
        if parameters != (SCRYPT_N, SCRYPT_R, SCRYPT_P):
            return False
        expected = _decode_credential_part(encoded_digest)
        actual = hashlib.scrypt(
            submitted.encode("utf-8"),
            salt=_decode_credential_part(encoded_salt),
            n=parameters[0],
            r=parameters[1],
            p=parameters[2],
            dklen=len(expected),
        )
        return secrets.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def secure_private_storage() -> None:
    """Create the runtime data directory and restrict its local permissions."""
    VAR.mkdir(parents=True, exist_ok=True, mode=0o700)
    for path in (VAR, *VAR.rglob("*")):
        if path.is_symlink():
            continue
        try:
            path.chmod(0o700 if path.is_dir() else 0o600)
        except OSError:
            pass


def clean_name(name: str) -> str:
    value = " ".join(str(name or "").split())
    if not value or len(value) > 40 or any(x in value for x in "\r\n|"):
        raise ValueError("Enter your registered name (40 characters or fewer).")
    return value


def status_rows() -> dict[str, dict[str, str]]:
    """Read the canonical status ledger without ever changing it."""
    rows: dict[str, dict[str, str]] = {}
    if not STATUS.is_file():
        return rows
    for line in STATUS.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != len(STATUS_COLUMNS) or cells[0] in {"book", "---"}:
            continue
        rows[cells[0]] = dict(zip(STATUS_COLUMNS, cells))
    return rows


def peer_review_ledger() -> dict:
    value = read_json(PEER_REVIEWS, {})
    if not isinstance(value, dict) or value.get("schema") != "lbf-book-peer-review-signoffs-v1":
        return {"schema": "lbf-book-peer-review-signoffs-v1", "books": {}}
    if not isinstance(value.get("books"), dict):
        value["books"] = {}
    return value


def parsed_translation_book(slug: str) -> tuple[object, Path, str, list[dict]]:
    """Return canonical book text as chapter/verse rows for human reading."""
    book = book_or_raise(slug)
    path = translation_file(book.slug)
    if not path.is_file():
        raise ValueError(f"{book.label} has no canonical translation file to review.")
    text = path.read_text(encoding="utf-8")
    chapters: list[dict] = []
    current: dict | None = None
    for line in text.splitlines():
        chapter_match = re.match(r"^##\s+Cap[ií]tulo\s+(\d+)\s*$", line.strip(), re.IGNORECASE)
        if chapter_match:
            current = {"chapter": int(chapter_match.group(1)), "verses": []}
            chapters.append(current)
            continue
        verse_match = HEADING.match(line.strip())
        if verse_match and current is not None:
            current["verses"].append({"verse": int(verse_match.group(2)), "text": ""})
            continue
        if current is None or not current["verses"] or not line.strip() or line.lstrip().startswith(">"):
            continue
        current["verses"][-1]["text"] = " ".join(
            part for part in (current["verses"][-1]["text"], line.strip()) if part
        )
    chapters = [chapter for chapter in chapters if chapter["verses"]]
    if not chapters:
        raise ValueError(f"{book.label} has no canonical Protestant chapter text to review.")
    return book, path, text, chapters


def current_peer_signoffs(slug: str, translation_sha256: str | None = None) -> tuple[list[dict], list[dict]]:
    if translation_sha256 is None:
        _, path, _, _ = parsed_translation_book(slug)
        translation_sha256 = file_fingerprint(path)
    entries = peer_review_ledger().get("books", {}).get(slug, [])
    if not isinstance(entries, list):
        entries = []
    current, historical = [], []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        row = {
            "reviewedBy": str(entry.get("reviewedBy") or ""),
            "reviewedOn": str(entry.get("reviewedOn") or ""),
            "chapterCount": len(entry.get("chaptersRead") or []),
        }
        (current if entry.get("translationSha256") == translation_sha256 else historical).append(row)
    return current, historical


def peer_review_catalog() -> list[dict]:
    statuses = status_rows()
    rows = []
    for book in (*OT, *NT):
        path = translation_file(book.slug)
        if not path.is_file():
            continue
        try:
            _, _, _, chapters = parsed_translation_book(book.slug)
        except ValueError:
            continue
        current, historical = current_peer_signoffs(book.slug, file_fingerprint(path))
        state = (statuses.get(book.slug) or {}).get("translation") or "none"
        rows.append({
            "book": book.slug,
            "label": book.label,
            "testament": book.testament,
            "translationStatus": state,
            "chapterCount": len(chapters),
            "currentSignoffs": current,
            "historicalSignoffCount": len(historical),
            "signoffEligible": state in {"ready", "done"},
        })
    return rows


def peer_review_view(name, token, slug) -> dict:
    person = authorize(name, token)
    book, path, _, chapters = parsed_translation_book(str(slug or ""))
    sha256 = file_fingerprint(path)
    current, historical = current_peer_signoffs(book.slug, sha256)
    state = (status_rows().get(book.slug) or {}).get("translation") or "none"
    return {
        "reviewer": person,
        "book": book.slug,
        "label": book.label,
        "testament": book.testament,
        "translationStatus": state,
        "translationSha256": sha256,
        "signoffEligible": state in {"ready", "done"},
        "chapters": chapters,
        "currentSignoffs": current,
        "historicalSignoffs": historical,
        "scope": "Peer approval of this exact Spanish translation only; not alignment approval and not STATUS.md book completion.",
    }


def peer_review_home(name, token) -> dict:
    person = authorize(name, token)
    return {"reviewer": person, "books": peer_review_catalog()}


def sign_peer_review(payload: dict) -> dict:
    person = authorize(payload.get("name"), payload.get("token"))
    book, path, _, chapters = parsed_translation_book(str(payload.get("book") or ""))
    state = (status_rows().get(book.slug) or {}).get("translation") or "none"
    if state not in {"ready", "done"}:
        raise ValueError(f"{book.label} is {state}, not ready for a whole-book peer sign-off.")
    if payload.get("translationApproved") is not True or payload.get("scopeConfirmed") is not True:
        raise ValueError("Confirm both the whole-book translation approval and its limited peer-review scope.")
    expected_chapters = [chapter["chapter"] for chapter in chapters]
    try:
        chapters_read = sorted({int(value) for value in payload.get("chaptersRead") or []})
    except (TypeError, ValueError) as exc:
        raise ValueError("The chapter reading confirmation is invalid.") from exc
    if chapters_read != expected_chapters:
        raise ValueError("Confirm that you personally read every chapter of this exact book before signing.")
    expected_sha256 = file_fingerprint(path)
    if str(payload.get("translationSha256") or "") != expected_sha256:
        raise ValueError("The translation changed while you were reading it. Reload the book and review the current text.")
    with _lock:
        ledger = peer_review_ledger()
        entries = ledger["books"].setdefault(book.slug, [])
        if any(
            isinstance(entry, dict)
            and str(entry.get("reviewedBy") or "").casefold() == person.casefold()
            and entry.get("translationSha256") == expected_sha256
            for entry in entries
        ):
            raise ValueError(f"{person} has already signed this exact version of {book.label}.")
        entries.append({
            "schema": "lbf-book-peer-review-signoff-v1",
            "book": book.slug,
            "reviewedBy": person,
            "reviewedOn": now(),
            "translationSha256": expected_sha256,
            "chaptersRead": chapters_read,
            "translationApproved": True,
            "scopeConfirmed": True,
            "scope": "exact canonical Spanish translation only; not alignment approval and not STATUS.md book completion",
        })
        write_json(PEER_REVIEWS, ledger)
    return peer_review_view(person, payload.get("token"), book.slug)


def authorize(name: str, token: str) -> str:
    person = clean_name(name)
    allow_plaintext = os.environ.get("LBF_TEAM_ENV", "development").casefold() != "production"
    for known, secret in load_people().items():
        if known.casefold() == person.casefold() and verify_credential(token, secret, allow_plaintext=allow_plaintext):
            return known
    raise ValueError("Name or token does not match.")


def book_or_raise(slug: str):
    try:
        book = get_book(str(slug or ""))
    except KeyError as exc:
        raise ValueError(str(exc)) from exc
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


def recovered_verse_state(slug: str, chapter: int, verse: int) -> dict:
    recovered = read_json(recovered_path(slug, chapter), {})
    verses = recovered.get("verses") if isinstance(recovered, dict) else {}
    state = verses.get(str(verse)) if isinstance(verses, dict) else {}
    return state if isinstance(state, dict) else {}


def restore_recovered_units(state: dict, candidate: dict) -> dict:
    """Replace an empty failed attempt with one coherent prepared candidate."""
    if state and not state.get("units") and candidate.get("units"):
        return {
            **state,
            "spanish": candidate.get("spanish") or state.get("spanish") or "",
            "units": candidate["units"],
            "sourceConfirmed": False,
            "alignmentConfirmed": False,
            "suppliedConfirmed": False,
        }
    return state


def revision_is_open(slug: str, chapter: int, verse: int) -> bool:
    """Return true only while the open revision is bound to this approval."""
    state = recovered_verse_state(slug, chapter, verse)
    if state.get("revisionOpen") is not True:
        return False
    artifact = read_json(human_path(slug, chapter, verse), {})
    expected = str(state.get("reopenedFromApprovalSha256") or "")
    return bool(
        artifact.get("schema") == "lbf-human-reviewed-candidate-v1"
        and expected
        and expected == object_fingerprint(artifact)
    )


def save_review_attempt(book, chapter: int, verse: int, person: str, payload: dict) -> None:
    """Preserve a named human's exact form state even when validation rejects it."""
    path = recovered_path(book.slug, chapter)
    recovered = read_json(path, {})
    if not isinstance(recovered, dict):
        recovered = {}
    recovered.update(schema="lbf-recovered-browser-review-v1", book=book.slug, chapter=chapter)
    recovered.setdefault("note", "Trabajo humano guardado antes de la validación canónica.")
    verses = recovered.setdefault("verses", {})
    previous = verses.get(str(verse)) if isinstance(verses.get(str(verse)), dict) else {}
    verses[str(verse)] = {
        "spanish": str(payload.get("spanish") or ""),
        "units": payload.get("units") if isinstance(payload.get("units"), list) else [],
        "unitsComplete": bool(payload.get("unitsComplete")),
        "decision": str(payload.get("decision") or ""),
        "decisionCategory": str(payload.get("decisionCategory") or "confirmed"),
        "sourceConfirmed": bool(payload.get("sourceConfirmed")),
        "alignmentConfirmed": bool(payload.get("alignmentConfirmed")),
        "suppliedConfirmed": bool(payload.get("suppliedConfirmed")),
        "auditOverrideConfirmed": bool(payload.get("auditOverrideConfirmed")),
        "lastAttemptedBy": person,
        "lastAttemptedOn": now(),
        "revisionOpen": bool(payload.get("revisionOpen", previous.get("revisionOpen", False))),
        "reopenedFromApprovalSha256": str(
            payload.get("reopenedFromApprovalSha256")
            or previous.get("reopenedFromApprovalSha256")
            or ""
        ),
    }
    write_json(path, recovered)


def close_revision(book, chapter: int, verse: int, person: str, *, cancelled: bool = False) -> None:
    path = recovered_path(book.slug, chapter)
    recovered = read_json(path, {})
    verses = recovered.get("verses") if isinstance(recovered, dict) else {}
    state = verses.get(str(verse)) if isinstance(verses, dict) else None
    if not isinstance(state, dict):
        return
    state["revisionOpen"] = False
    state["revisionClosedBy"] = person
    state["revisionClosedOn"] = now()
    state["revisionCancelled"] = bool(cancelled)
    write_json(path, recovered)


def candidate_path(slug: str, chapter: int, verse: int) -> Path | None:
    folder = pipeline_dir(slug)
    options = []
    if human_review_is_current(slug, chapter, verse):
        options.append(human_path(slug, chapter, verse))
    # Explicit workflow priority only.  Never glob request JSON as if it were
    # a completed draft, and never choose between differing drafts by mtime.
    options += [
        folder / f"{slug}-{chapter}-{verse}.draft-team-gpt.json",
        folder / f"{slug}-{chapter}-{verse}.draft-auto.json",
        folder / f"{slug}-{chapter}-{verse}.draft-gpt56.json",
    ]
    for path in options:
        if not path.is_file() or path.name.endswith(".request.json"):
            continue
        candidate = read_json(path, {})
        if isinstance(candidate, dict) and str(candidate.get("spanish") or "").strip():
            return path
    return None


def reusable_candidate(slug: str, chapter: int, verse: int) -> tuple[Path | None, dict]:
    """Return a usable review seed without requiring another paid model call."""
    path = candidate_path(slug, chapter, verse)
    candidate = read_json(path, {}) if path else {}
    if path and str(candidate.get("spanish") or "").strip():
        return path, candidate
    return None, {}


def compatible_paid_draft(candidate: dict, packet: dict) -> bool:
    """Accept prior medium drafts while creating all new drafts at low effort."""
    return bool(
        candidate.get("model") in COMPATIBLE_TEAM_DRAFT_MODELS
        and candidate.get("reasoningEffort") in COMPATIBLE_DRAFT_REASONING
        and candidate.get("packetSha256") == packet_fingerprint(packet)
        and draft_specification_is_current(candidate)
    )


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
    fingerprint = object_fingerprint(candidate)
    audit_current = audit.get("candidateSha256") == fingerprint
    check_current = check.get("candidateSha256") == fingerprint and check.get("model") == SPANISH_GATE_MODEL
    current_audit = audit if audit_current else {}
    current_check = check if check_current else {}
    packet = read_json(packet_path(slug, chapter, verse), {})
    if check_current:
        # Recompute deterministic findings with today's rules. Keep historical
        # artifacts unchanged; only independent audits retain their verdicts.
        findings = [*lint_spanish(str(candidate.get("spanish") or ""), packet),
                    *lint_divine_name(str(candidate.get("spanish") or ""), packet)]
        current_check = {**check, "verdict": "fail" if findings else "pass", "findings": findings}
    required = audit_required(candidate, current_check)
    _, alignment_findings = alignment_preflight_findings(packet, candidate.get("units") or [], str(candidate.get("spanish") or ""))
    return {"source": path.name, "label": label, "draftModel": candidate.get("model") or "unverified", "draftReasoning": candidate.get("reasoningEffort") or "unverified", "promptCurrent": draft_specification_is_current(candidate), "auditModel": current_audit.get("model") or "unverified", "auditReasoning": current_audit.get("reasoningEffort") or "unverified", "spanishModel": current_check.get("model") or "unverified", "spanishReasoning": current_check.get("reasoningEffort") or "unverified", "auditRequired": required, "fidelity": current_audit.get("verdict") or ("missing" if required else "not-required"), "fidelityFindings": current_audit.get("findings") or [], "spanish": current_check.get("verdict") or "missing", "spanishFindings": current_check.get("findings") or [], "alignmentFindings": alignment_findings}


def human_precedents(slug: str) -> list[dict]:
    """Expose adjudication memory to people, never to a model prompt."""
    rows = []
    for path in sorted(pipeline_dir(slug).glob(f"{slug}-*-*.candidate-human-reviewed.json")):
        item = read_json(path, {})
        adjudication = item.get("adjudication") if isinstance(item, dict) else {}
        decision = str((adjudication or {}).get("decision") or "").strip()
        if not decision or decision == DEFAULT_DECISION:
            continue
        rows.append({"reference": item.get("reference") or path.stem, "category": (adjudication or {}).get("decisionCategory") or "legacy", "decision": decision})
    return rows


def decision_summary(slug: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for path in sorted(pipeline_dir(slug).glob(f"{slug}-*-*.candidate-human-reviewed.json")):
        item = read_json(path, {})
        adjudication = item.get("adjudication") if isinstance(item, dict) else {}
        category = str((adjudication or {}).get("decisionCategory") or "")
        if category in DECISION_CATEGORIES and category != "confirmed":
            counts[category] = counts.get(category, 0) + 1
    return counts


def public_packet(packet: dict, book, chapter: int, verse: int) -> dict:
    keys = ("sourceTokenId", "position", "surface", "paleo", "lemma", "strongs", "morph", "morphExpanded")
    # An NT chapter may have a complete structural candidate before its
    # per-verse translation packets have been prepared.  Keep that valid
    # no-cost review state visible: current editorial policy still needs the
    # canonical chapter context, but an absent packet must not crash the
    # chapter endpoint or masquerade as a browser connection failure.
    policy_packet = {
        **packet,
        "book": packet.get("book") or book.slug,
        "chapter": packet.get("chapter") or chapter,
        "verse": packet.get("verse") or verse,
    }
    editorial = canonical_editorial_policy_fields(policy_packet)
    return {"schema": packet.get("schema"), "sourcePolicy": packet.get("sourcePolicy"), "evidenceStatus": packet.get("evidenceStatus"), "reference": packet.get("reference"), "textualBasis": packet.get("textualBasis"), "tokens": [{k: token.get(k) for k in keys} for token in packet.get("tokens") or []], "syntaxEvidence": packet.get("syntax"), "originalLanguageContext": packet.get("originalLanguageContext") or [], "corpusEvidence": packet.get("corpusEvidence") or [], "lexicalEvidence": packet.get("lexicalEvidence") or [], "editorialLexicalPolicy": editorial["editorialLexicalPolicy"], "editorialLexicalPolicyReview": editorial["editorialLexicalPolicyReview"]}


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


def chapter_review_is_current(slug: str, chapter: int, verses: list[int]) -> bool:
    """A chapter is complete only while every bound verse approval is current."""
    artifact = read_json(pipeline_dir(slug) / f"{slug}-{chapter}.human-review.json", {})
    return bool(
        artifact.get("schema") == "lbf-human-chapter-review-v1"
        and artifact.get("invalidated") is not True
        and artifact.get("continuityVoiceFlowConfirmed") is True
        and artifact.get("verseWordingConfirmed") == verses
        and artifact.get("alignmentSeedsConfirmed") == verses
        and all(human_review_is_current(slug, chapter, verse) for verse in verses)
        and not any(revision_is_open(slug, chapter, verse) for verse in verses)
    )


def chapter_view(slug: str, chapter) -> dict:
    book, number, verses = chapter_or_raise(slug, chapter)
    path = translation_file(slug)
    canonical = path.read_text(encoding="utf-8") if path.is_file() else ""
    recovered = read_json(recovered_path(slug, number), {})
    recovered_verses = recovered.get("verses") if isinstance(recovered, dict) else {}
    recovered_verses = recovered_verses if isinstance(recovered_verses, dict) else {}
    nt_structure_status: dict[int, str] = {}
    if getattr(book, "testament", "ot") == "nt":
        try:
            nt_structure_status = {
                row["verse"]: (
                    "HOLD_STRUCTURE"
                    if row["status"] == "hold-token-disagreement"
                    else "READY_TR_STRUCTURE"
                )
                for row in nt_syntax_view(book.slug, number)["verses"]
            }
        except ValueError:
            nt_structure_status = {verse: "HOLD_NO_CHAPTER_CANDIDATE" for verse in verses}
    rows = []
    for verse in verses:
        packet = read_json(packet_path(slug, number, verse), {})
        canonical_verse = verse_body(canonical, number, verse) or ""
        candidate_file = candidate_path(slug, number, verse)
        candidate = read_json(candidate_file, {}) if candidate_file else {}
        if not candidate_file:
            # Reviewing the canonical wording against the visible packet is a
            # complete no-cost path.  The reviewer supplies and validates the
            # reverse-interlinear units by hand; GPT is optional assistance.
            candidate = {
                "schema": "lbf-local-review-seed-v1",
                "model": "human-local",
                "reasoningEffort": "not-required",
                "spanish": canonical_verse,
                "units": canonical_alignment_units(
                    book.slug,
                    book.testament,
                    f"{book.label} {number}:{verse}",
                ),
                "uncertainties": [],
                "evidenceDecisions": [],
            }
        gate_candidate = candidate
        if candidate.get("units"):
            candidate = {**candidate, "units": merge_source_units_by_id(candidate["units"])}
        recovered_verse = recovered_verses.get(str(verse)) or {}
        if isinstance(recovered_verse, dict) and recovered_verse.get("units"):
            recovered_verse = {**recovered_verse, "units": merge_source_units_by_id(recovered_verse["units"])}
        # An older failed browser submission may contain the human's text but
        # no alignment rows.  Preserve that text while restoring the model's
        # visible seed as an editable starting point; it remains unapproved
        # and must still pass exact Spanish/unit validation.
        recovered_verse = restore_recovered_units(recovered_verse, candidate)
        gate = gate_for(slug, number, verse, candidate_file, gate_candidate) if candidate_file else {
            "source": "canonical-local-seed",
            "draftModel": "human-local",
            "draftReasoning": "not-required",
            "promptCurrent": True,
            "auditRequired": False,
            "fidelity": "not-required",
            "fidelityFindings": [],
            "spanish": "local",
            "spanishFindings": [],
            "alignmentFindings": [],
        }
        human_current = human_review_is_current(slug, number, verse)
        revision_open = revision_is_open(slug, number, verse)
        packet_view = public_packet(packet, book, number, verse)
        if book.testament == "nt" and not packet_view.get("evidenceStatus"):
            packet_view["evidenceStatus"] = nt_structure_status.get(verse, "HOLD_NO_CHAPTER_CANDIDATE")
        rows.append({"verse": verse, "reference": f"{book.label} {number}:{verse}", "canonical": canonical_verse, "packet": packet_view, "candidate": candidate, "recovered": recovered_verse, "gate": gate, "humanReviewed": human_current and not revision_open, "priorApprovalCurrent": human_current, "revisionOpen": revision_open})
    return {"book": slug, "label": book.label, "chapter": number, "claim": load_claims().get(claim_key(slug, number)) or {}, "policy": "lbf-source-policy-v4", "textualBasis": "TR1894" if book.testament == "nt" else "OSHB/WLC", "model": TEAM_MODEL, "reasoningEffort": TEAM_REASONING, "promptSha256": draft_prompt_fingerprint(), "reviewSpecVersion": REVIEW_SPEC_VERSION, "chapterReviewed": chapter_review_is_current(slug, number, verses), "precedents": human_precedents(slug), "decisionSummary": decision_summary(slug), "precedentBoundary": "Human adjudication memory guides reviewers only. It is never model evidence and never overrides the canonical source packet. Repeated decisions are candidates for an explicit project rule, never automatic model evidence.", "recoveryNote": recovered.get("note") if isinstance(recovered, dict) else "", "verses": rows}


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
    if getattr(book, "testament", "ot") == "nt":
        phase = nt_structure_phase_status()
        if not phase["complete"]:
            raise ValueError(
                "La fase estructural del NT todavía no está completa: "
                f"{phase['unbuiltChapters']} capítulos sin candidato y "
                f"{phase['holdChapters']} capítulos con HOLD. "
                "Resuelve primero toda la cola estructural; después prepara la traducción."
            )
    selected_verses = verses
    selected_verse = None
    if verse is not None:
        selected_verse = int(verse or 0)
        if selected_verse not in verses:
            raise ValueError("That verse is not in this Protestant chapter.")
        selected_verses = [selected_verse]
    cache_key = (person, book.slug, number, selected_verse)
    cache_now = time.monotonic()
    with _lock:
        expired = [key for key, (created, _) in _estimate_packet_cache.items() if cache_now - created > ESTIMATE_PACKET_CACHE_SECONDS]
        for key in expired:
            _estimate_packet_cache.pop(key, None)
        cached = _estimate_packet_cache.get(cache_key)
        cached_packets = cached[1] if cached else {}
    estimate_packets: dict[int, dict] = {}
    draft_calls = audit_calls = skipped_human = reused_candidates = 0
    structural_holds: list[dict] = []
    estimated_input_tokens = 0
    possible_audit_input_tokens = 0
    for verse in selected_verses:
        if human_review_is_current(book.slug, number, verse):
            skipped_human += 1
            continue
        # The first estimate rebuilds every derived packet in memory so a
        # stale stored packet cannot understate paid calls. Cost confirmation
        # immediately calls this function a second time; reuse the exact
        # packets displayed in that recent estimate while
        # rechecking human approvals and candidate compatibility below. This
        # avoids making a long OT chapter look frozen twice without weakening
        # the server-side maximum-cost check.
        packet = cached_packets.get(verse)
        if packet is None:
            packet = build_packet(book.slug, number, verse)
        estimate_packets[verse] = packet
        # A HOLD packet is still the canonical, no-cost explanation of what
        # must be adjudicated. Persist it so Team Desk can show the source
        # tokens without pretending that translation/alignment already exist.
        write_json(packet_path(book.slug, number, verse), packet)
        if getattr(book, "testament", "ot") == "nt" and packet.get("evidenceStatus") != "READY_FOR_MODEL":
            status = packet.get("evidenceStatus") or "HOLD_STRUCTURE"
            if selected_verse is not None:
                raise ValueError(
                    f"{book.label} {number}:{verse} no está listo para el modelo: "
                    f"{status}. Resuelve su evidencia estructural en esta misma sesión."
                )
            structural_holds.append({"verse": verse, "status": status})
            continue
        existing_path, existing_candidate = reusable_candidate(book.slug, number, verse)
        if (
            existing_path
            and existing_candidate
            and compatible_paid_draft(existing_candidate, packet)
        ):
            reused_candidates += 1
            continue
        path = pipeline_dir(book.slug) / f"{book.slug}-{number}-{verse}.draft-team-gpt.json"
        candidate = read_json(path, {})
        fresh_draft = bool(packet and path.is_file() and compatible_paid_draft(candidate, packet))
        if not fresh_draft:
            draft_calls += 1
            if packet:
                estimated_input_tokens += estimate_input_tokens(load_draft_system() + build_draft_prompt(packet))
                possible_audit_input_tokens += estimate_input_tokens(AUDIT_SYSTEM + build_audit_prompt(packet, "[candidate]", "team-gpt"))
        # Audits are never launched automatically.  A reviewer may request a
        # paid one-verse audit explicitly from the verse card.
    output_cap_tokens = draft_calls * DRAFT_MAX_COMPLETION_TOKENS + audit_calls * AUDIT_MAX_COMPLETION_TOKENS
    likely_output_tokens = draft_calls * DRAFT_EXPECTED_COMPLETION_TOKENS
    likely_usd = estimated_input_tokens / 1_000_000 * TEAM_RATES["input"] + likely_output_tokens / 1_000_000 * TEAM_RATES["output"]
    conservative_usd = estimated_input_tokens / 1_000_000 * TEAM_RATES["input"] + output_cap_tokens / 1_000_000 * TEAM_RATES["output"]
    all_flagged_usd = conservative_usd
    maximum_paid_calls = draft_calls
    likely_new_audits = 0
    with _lock:
        _estimate_packet_cache[cache_key] = (time.monotonic(), estimate_packets)
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
        "reusedCandidates": reused_candidates,
        "structuralHolds": structural_holds,
        "structuralHoldCount": len(structural_holds),
        "possibleSelectiveAudits": 0,
        "localSpanishChecks": draft_calls,
        "estimatedLikelyUsd": round(likely_usd, 2),
        "estimatedMaximumUsd": math.ceil(conservative_usd * 100) / 100,
        "estimatedAllFlaggedMaximumUsd": math.ceil(all_flagged_usd * 100) / 100,
        "note": "Existing candidates are reused. Paid audits are optional, one verse at a time, and are never included or launched automatically.",
    }


def prepare(name, slug, chapter, token="", cost_confirmed=False, verse=None, confirmed_maximum_usd=None) -> None:
    person = authorize(name, token)
    book, number, verses = chapter_or_raise(slug, chapter)
    selected_verse = None
    if verse is not None:
        selected_verse = int(verse or 0)
        if selected_verse not in verses:
            raise ValueError("That verse is not in this Protestant chapter.")
    if not cost_confirmed:
        raise ValueError("Review and confirm the preparation cost estimate first.")
    estimate = prepare_estimate(name, slug, chapter, token, verse)
    try:
        confirmed_maximum = float(confirmed_maximum_usd)
    except (TypeError, ValueError) as exc:
        raise ValueError("Confirm the displayed maximum preparation cost.") from exc
    if confirmed_maximum < float(estimate["estimatedMaximumUsd"]):
        raise ValueError("The preparation estimate changed. Review and confirm the new maximum before any paid call.")
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
            # from an earlier policy must never reach the paid Sol model.
            _run([sys.executable, str(PIPELINE / "build_source_packet.py"), slug, str(chapter), str(verse)])
            packet = read_json(packet_path(slug, chapter, verse), {})
            # Chapter preparation is allowed to make progress around NT
            # structural holds. A HOLD packet is displayed to the reviewer
            # but never reaches a paid model call.
            if packet.get("evidenceStatus") != "READY_FOR_MODEL":
                continue
            existing_path, existing_candidate = reusable_candidate(slug, chapter, verse)
            if (
                existing_path
                and existing_candidate
                and compatible_paid_draft(existing_candidate, packet)
            ):
                continue
            path = pipeline_dir(slug) / f"{slug}-{chapter}-{verse}.draft-team-gpt.json"
            candidate = read_json(path, {})
            if candidate.get("schema") == "lbf-human-reviewed-candidate-v1": continue
            if not path.is_file() or not compatible_paid_draft(candidate, packet):
                _run([sys.executable, str(PIPELINE / "draft_gpt.py"), slug, str(chapter), str(verse), "--label", "team-gpt"])
                path = pipeline_dir(slug) / f"{slug}-{chapter}-{verse}.draft-team-gpt.json"; candidate = read_json(path, {})
            label = label_for(candidate, path); folder = pipeline_dir(slug)
            check = folder / f"{slug}-{chapter}-{verse}.spanish-check-{label}.json"
            check_data = read_json(check, {})
            fingerprint = object_fingerprint(candidate)
            if check_data.get("model") != SPANISH_GATE_MODEL or check_data.get("candidateSha256") != fingerprint: _run([sys.executable, str(PIPELINE / "spanish_check_local.py"), slug, str(chapter), str(verse), "--candidate-file", str(path), "--label", label], allow_gate_failure=True)
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
        raise ValueError("A saved unapproved candidate is required before requesting an optional paid audit.")
    packet = read_json(packet_path(book.slug, chapter, verse), {})
    label = label_for(candidate, path)
    audit_path = pipeline_dir(book.slug) / f"{book.slug}-{chapter}-{verse}.audit-gpt-{label}.json"
    existing = read_json(audit_path, {})
    fingerprint = object_fingerprint(candidate)
    if existing.get("model") != TEAM_MODEL or existing.get("reasoningEffort") != TEAM_REASONING or existing.get("candidateSha256") != fingerprint:
        _run([sys.executable, str(PIPELINE / "audit_gpt.py"), book.slug, str(chapter), str(verse), "--candidate-file", str(path), "--label", label], allow_gate_failure=True)
    return chapter_view(book.slug, chapter)


def validate_units(packet: dict, units, spanish: str = "") -> list[dict]:
    clean, findings = alignment_preflight_findings(packet, units, spanish)
    if findings:
        finding = findings[0]
        suffix = f' Spanish unit: "{finding["spanishSpan"]}"' if finding.get("spanishSpan") and "too broad" in finding.get("issue", "") else ""
        raise ValueError(f'{finding["issue"]}{suffix}')
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


def invalidate_chapter_review(book, chapter: int, verse: int, person: str) -> None:
    """Invalidate chapter-level confirmations after a material verse revision."""
    review_path = pipeline_dir(book.slug) / f"{book.slug}-{chapter}.human-review.json"
    review = read_json(review_path, {})
    if isinstance(review, dict) and review.get("schema") == "lbf-human-chapter-review-v1":
        review.update(
            invalidated=True,
            invalidatedBy=person,
            invalidatedOn=now(),
            invalidatedVerse=verse,
            invalidationReason="A previously approved verse was materially revised.",
        )
        write_json(review_path, review)
    seed_path = pipeline_dir(book.slug) / f"{book.slug}-{chapter}.alignment-seed.json"
    seed = read_json(seed_path, {})
    if isinstance(seed, dict) and seed.get("schema") == "lbf-alignment-seed-manifest-v1":
        seed.update(
            status="seeded-hand-incomplete",
            chapterReviewInvalidated=True,
            invalidatedBy=person,
            invalidatedOn=now(),
            invalidatedVerse=verse,
        )
        for item in seed.get("verses") or []:
            if isinstance(item, dict) and item.get("verse") == verse:
                item["confirmed"] = False
        write_json(seed_path, seed)
    testament = getattr(book, "testament", "")
    if testament:
        demote_chapter_alignment(book=book.slug, testament=testament, chapter=chapter)


def archived_approval(prior: dict, person: str) -> dict:
    """Keep an immutable, noncanonical record of an approval being replaced."""
    return {
        "schema": "lbf-human-approval-history-entry-v1",
        "archivedBy": person,
        "archivedOn": now(),
        "spanish": prior.get("spanish") or "",
        "units": prior.get("units") if isinstance(prior.get("units"), list) else [],
        "approvalBinding": prior.get("approvalBinding") if isinstance(prior.get("approvalBinding"), dict) else {},
        "adjudication": prior.get("adjudication") if isinstance(prior.get("adjudication"), dict) else {},
    }


def clean_candidate_for_chapter_approval(slug: str, chapter: int, verse: int) -> tuple[dict | None, list[str]]:
    """Return the exact server candidate only when every no-cost gate is clean."""
    path = candidate_path(slug, chapter, verse)
    candidate = read_json(path, {}) if path else {}
    packet = read_json(packet_path(slug, chapter, verse), {})
    reasons: list[str] = []
    if not path or candidate.get("schema") == "lbf-human-reviewed-candidate-v1":
        return None, ["no hay candidato preparado sin aprobar"]
    if packet.get("sourcePolicy") != "lbf-source-policy-v4" or packet.get("evidenceStatus") != "READY_FOR_MODEL":
        reasons.append("el paquete canónico no está READY_FOR_MODEL")
    if not compatible_paid_draft(candidate, packet):
        reasons.append("el candidato no está ligado al paquete vigente de un modelo Sol autorizado")
    if candidate.get("uncertainties"):
        reasons.append("el candidato declaró incertidumbre")
    if candidate.get("addedConcepts"):
        reasons.append("el candidato declaró conceptos añadidos")
    if candidate.get("droppedUncitedUnits"):
        reasons.append("el candidato omitió unidades sin justificar")
    # Historical precision findings stay in the draft for provenance. The
    # current validator and gate below recheck those units against today's
    # packet and rules, including OSHB compound-name continuation markers.
    spanish = " ".join(str(candidate.get("spanish") or "").split())
    if not spanish:
        reasons.append("falta el texto español")
    policy_findings = [*lint_spanish(spanish, packet), *lint_divine_name(spanish, packet)]
    reasons.extend(item["issue"] for item in policy_findings)
    try:
        units = validate_units(packet, candidate.get("units"), spanish)
    except ValueError as exc:
        units = []
        reasons.append(str(exc))
    gate = gate_for(slug, chapter, verse, path, candidate)
    if gate.get("promptCurrent") is False:
        reasons.append("las reglas del candidato no son compatibles")
    if gate.get("spanish") != "pass":
        reasons.append("la comprobación mecánica del español no pasó")
    if gate.get("fidelity") == "fail" or (gate.get("auditRequired") and gate.get("fidelity") != "pass"):
        reasons.append("la fidelidad requiere adjudicación humana")
    reasons.extend(str(item.get("issue") or "problema de fidelidad") for item in gate.get("fidelityFindings") or [])
    reasons.extend(str(item.get("issue") or "problema de español") for item in gate.get("spanishFindings") or [])
    reasons.extend(str(item.get("issue") or "problema de alineación") for item in gate.get("alignmentFindings") or [])
    if reasons:
        return None, list(dict.fromkeys(reasons))
    return {"candidate": candidate, "packet": packet, "spanish": spanish, "units": units}, []


def human_artifact(book, chapter: int, verse: int, person: str, spanish: str, units: list[dict], packet: dict, *, approval_mode: str, decision: str = DEFAULT_DECISION) -> dict:
    return {
        "schema": "lbf-human-reviewed-candidate-v1",
        "reviewSpecVersion": REVIEW_SPEC_VERSION,
        "book": book.slug,
        "reference": f"{book.label} {chapter}:{verse}",
        "chapter": chapter,
        "verse": verse,
        "sourcePolicy": packet.get("sourcePolicy"),
        "packetSha256": packet_fingerprint(packet),
        "approvalBinding": approval_binding(spanish, units, packet),
        "spanish": spanish,
        "units": units,
        "adjudication": {
            "status": "approved",
            "decisionCategory": "confirmed",
            "decision": decision,
            "reviewedBy": person,
            "reviewedOn": today(),
            "humanApprovedInTeamDesk": True,
            "approvalMode": approval_mode,
            "sourceEvidenceConfirmed": True,
            "alignmentUnitsConfirmed": True,
            "suppliedWordsConfirmed": True,
            "failedAuditOverrideConfirmed": False,
            "scope": "verse wording and reviewed alignment units; canonical promotion requires explicit chapter approval; not STATUS.md book-done approval",
        },
    }


def finish_chapter_locked(book, chapter: int, verses: list[int], person: str) -> None:
    canonical_path = promote_chapter_alignment(
        book=book.slug,
        testament=book.testament,
        label=book.label,
        chapter=chapter,
        verses=verses,
    )
    write_json(pipeline_dir(book.slug) / f"{book.slug}-{chapter}.human-review.json", {"schema": "lbf-human-chapter-review-v1", "book": book.slug, "chapter": chapter, "reviewedBy": person, "reviewedOn": today(), "continuityVoiceFlowConfirmed": True, "verseWordingConfirmed": verses, "alignmentSeedsConfirmed": verses, "canonicalAlignmentConfirmed": True, "canonicalAlignmentFile": str(canonical_path.relative_to(ROOT)), "statusScope": "chapter review and canonical alignment only; not STATUS.md book-done approval"})
    write_json(pipeline_dir(book.slug) / f"{book.slug}-{chapter}.alignment-seed.json", {"schema": "lbf-alignment-seed-manifest-v1", "book": book.slug, "chapter": chapter, "status": "promoted-hand", "canonicalAlignmentChanged": True, "canonicalAlignmentFile": str(canonical_path.relative_to(ROOT)), "instruction": "Named reviewers confirmed these visible unit links and explicit chapter approval promoted them to canonical reverse links. Book completion remains separate.", "verses": [{"verse": v, "candidate": human_path(book.slug, chapter, v).name, "confirmed": True, "canonical": True} for v in verses]})


def reopen_verse(payload: dict) -> dict:
    """Open a no-cost revision seeded from the exact current approval."""
    person = authorize(payload.get("name"), payload.get("token"))
    book, chapter, verses = chapter_or_raise(payload.get("book"), payload.get("chapter"))
    verse = int(payload.get("verse") or 0)
    if verse not in verses:
        raise ValueError("That verse is not in this Protestant chapter.")
    with _lock:
        claims, key = assert_holder(person, book.slug, chapter)
        if not human_review_is_current(book.slug, chapter, verse):
            raise ValueError("Only a current human-approved verse can be reopened.")
        artifact = read_json(human_path(book.slug, chapter, verse), {})
        save_review_attempt(book, chapter, verse, person, {
            "spanish": artifact.get("spanish") or "",
            "units": artifact.get("units") if isinstance(artifact.get("units"), list) else [],
            "unitsComplete": True,
            "decision": "",
            "decisionCategory": "confirmed",
            "sourceConfirmed": False,
            "alignmentConfirmed": False,
            "suppliedConfirmed": False,
            "auditOverrideConfirmed": False,
            "revisionOpen": True,
            "reopenedFromApprovalSha256": object_fingerprint(artifact),
        })
        claims[key].update(verse=verse, note=f"Revision opened for {chapter}:{verse}; no paid call made", updated=now())
        save_claims(claims)
    return chapter_view(book.slug, chapter)


def cancel_revision(payload: dict) -> dict:
    """Discard the temporary revision while leaving the approval untouched."""
    person = authorize(payload.get("name"), payload.get("token"))
    book, chapter, verses = chapter_or_raise(payload.get("book"), payload.get("chapter"))
    verse = int(payload.get("verse") or 0)
    if verse not in verses:
        raise ValueError("That verse is not in this Protestant chapter.")
    with _lock:
        claims, key = assert_holder(person, book.slug, chapter)
        if not revision_is_open(book.slug, chapter, verse):
            raise ValueError("This verse does not have an open revision.")
        close_revision(book, chapter, verse, person, cancelled=True)
        claims[key].update(verse=verse, note=f"Revision cancelled for {chapter}:{verse}; prior approval preserved", updated=now())
        save_claims(claims)
    return chapter_view(book.slug, chapter)


def approve_verse(payload: dict) -> dict:
    person = authorize(payload.get("name"), payload.get("token")); book, chapter, verses = chapter_or_raise(payload.get("book"), payload.get("chapter")); verse = int(payload.get("verse") or 0)
    if verse not in verses: raise ValueError("That verse is not in this Protestant chapter.")
    with _lock:
        assert_holder(person, book.slug, chapter)
        prior_human_current = human_review_is_current(book.slug, chapter, verse)
        prior_human = read_json(human_path(book.slug, chapter, verse), {})
        revision_was_open = revision_is_open(book.slug, chapter, verse)
        save_review_attempt(book, chapter, verse, person, payload)
        packet = read_json(packet_path(book.slug, chapter, verse), {})
        if packet.get("sourcePolicy") != "lbf-source-policy-v4" or packet.get("evidenceStatus") != "READY_FOR_MODEL":
            status = packet.get("evidenceStatus") or "HOLD_STRUCTURE"
            raise ValueError(
                f"{book.label} {chapter}:{verse} no puede aprobarse todavía: {status}. "
                "Resuelve primero la evidencia estructural de este versículo. Tu trabajo quedó guardado."
            )
        if not payload.get("sourceConfirmed"): raise ValueError("Confirm the complete source-evidence review.")
        if not payload.get("alignmentConfirmed"): raise ValueError("Confirm every visible Spanish-to-source link.")
        if not payload.get("suppliedConfirmed"): raise ValueError("Confirm that every supplied Spanish word is marked in italics.")
        spanish = " ".join(str(payload.get("spanish") or "").split()); units = validate_units(packet, payload.get("units"), spanish)
        if not spanish: raise ValueError("Spanish text is required.")
        policy_findings = [*lint_spanish(spanish, packet), *lint_divine_name(spanish, packet)]
        if policy_findings:
            raise ValueError("Spanish policy failed: " + "; ".join(item["issue"] for item in policy_findings))
        prior_path = candidate_path(book.slug, chapter, verse); prior = read_json(prior_path, {}) if prior_path else {}; decision = " ".join(str(payload.get("decision") or "").split())
        decision_category = str(payload.get("decisionCategory") or "confirmed")
        if decision_category not in DECISION_CATEGORIES:
            raise ValueError("Choose a valid human decision category.")
        prior_spanish = " ".join(str(prior.get("spanish") or "").split())
        if prior_spanish and prior_spanish != spanish and decision_category == "confirmed":
            raise ValueError("Choose the category that best describes the human change.")
        if prior.get("schema") != "lbf-human-reviewed-candidate-v1":
            if prior_path:
                gate = gate_for(book.slug, chapter, verse, prior_path, prior)
                enforce_human_adjudication(prior, gate, spanish, decision, bool(payload.get("auditOverrideConfirmed")))
        binding = approval_binding(spanish, units, packet)
        history = list(prior_human.get("approvalHistory") or []) if isinstance(prior_human.get("approvalHistory"), list) else []
        if prior_human_current and prior_human.get("schema") == "lbf-human-reviewed-candidate-v1":
            history.append(archived_approval(prior_human, person))
        artifact = {
            "schema": "lbf-human-reviewed-candidate-v1",
            "reviewSpecVersion": REVIEW_SPEC_VERSION,
            "book": book.slug,
            "reference": f"{book.label} {chapter}:{verse}",
            "chapter": chapter,
            "verse": verse,
            "sourcePolicy": packet.get("sourcePolicy"),
            "packetSha256": packet_fingerprint(packet),
            "approvalBinding": binding,
            "spanish": spanish,
            "units": units,
            "approvalHistory": history,
            "adjudication": {
                "status": "approved",
                "decisionCategory": decision_category,
                "decision": decision or DEFAULT_DECISION,
                "reviewedBy": person,
                "reviewedOn": today(),
                "humanApprovedInTeamDesk": True,
                "sourceEvidenceConfirmed": True,
                "alignmentUnitsConfirmed": True,
                "suppliedWordsConfirmed": True,
                "failedAuditOverrideConfirmed": bool(payload.get("auditOverrideConfirmed")),
                "scope": "verse wording and reviewed alignment units; canonical promotion requires explicit chapter approval; not STATUS.md book-done approval",
            },
        }
        current_path = translation_file(book.slug)
        current_text = current_path.read_text(encoding="utf-8") if current_path.is_file() else ""
        changed = verse_body(current_text, chapter, verse) != spanish
        prior_units = prior_human.get("units") if isinstance(prior_human.get("units"), list) else []
        material_revision = bool(
            prior_human_current
            and (
                " ".join(str(prior_human.get("spanish") or "").split()) != spanish
                or prior_units != units
            )
        )
        if material_revision:
            invalidate_chapter_review(book, chapter, verse, person)
        if changed:
            invalidate_status(book.slug)
            write_verse(book.slug, chapter, verse, spanish)
        write_json(human_path(book.slug, chapter, verse), artifact)
        if revision_was_open:
            close_revision(book, chapter, verse, person)
        claims, key = assert_holder(person, book.slug, chapter); claims[key].update(verse=verse, note=f"Approved {chapter}:{verse}; alignment seed confirmed", updated=now()); save_claims(claims)
    return chapter_view(book.slug, chapter)


def approve_clean_chapter(payload: dict) -> dict:
    """Approve unchanged clean candidates and leave every HOLD untouched."""
    person = authorize(payload.get("name"), payload.get("token")); book, chapter, verses = chapter_or_raise(payload.get("book"), payload.get("chapter"))
    if not payload.get("contextConfirmed"):
        raise ValueError("Confirm the complete chapter continuity, voice, and flow review.")
    if not payload.get("cleanCandidatesConfirmed"):
        raise ValueError("Confirm that the chapter approval covers the exact clean candidates, their visible source links, and supplied-word italics.")
    with _lock:
        claims, key = assert_holder(person, book.slug, chapter)
        approved_now: list[int] = []
        holds: dict[int, list[str]] = {}
        planned: list[tuple[int, dict]] = []
        excluded = {int(value) for value in (payload.get("excludedVerses") or []) if str(value).isdigit()}
        for verse in verses:
            if revision_is_open(book.slug, chapter, verse):
                holds[verse] = ["hay una revisión abierta"]
                continue
            if human_review_is_current(book.slug, chapter, verse):
                continue
            if verse in excluded:
                holds[verse] = ["hay cambios humanos sin aprobación individual"]
                continue
            clean, reasons = clean_candidate_for_chapter_approval(book.slug, chapter, verse)
            if not clean:
                holds[verse] = reasons
                continue
            planned.append((verse, clean))
        canonical_path = translation_file(book.slug)
        canonical = canonical_path.read_text(encoding="utf-8") if canonical_path.is_file() else ""
        if any(verse_body(canonical, chapter, verse) != clean["spanish"] for verse, clean in planned):
            invalidate_status(book.slug)
        for verse, clean in planned:
            if verse_body(canonical_path.read_text(encoding="utf-8"), chapter, verse) != clean["spanish"]:
                write_verse(book.slug, chapter, verse, clean["spanish"])
            artifact = human_artifact(
                book, chapter, verse, person, clean["spanish"], clean["units"], clean["packet"],
                approval_mode="whole-chapter-clean-candidate",
                decision="The named reviewer approved this unchanged clean candidate in the whole-chapter review.",
            )
            write_json(human_path(book.slug, chapter, verse), artifact)
            approved_now.append(verse)
        missing = [verse for verse in verses if not human_review_is_current(book.slug, chapter, verse) or revision_is_open(book.slug, chapter, verse)]
        complete = not missing
        if complete:
            finish_chapter_locked(book, chapter, verses, person)
            note = "Chapter review complete; canonical alignment promoted"
        else:
            note = f"Clean candidates approved; HOLD verses: {', '.join(map(str, missing))}"
        claims[key].update(note=note, updated=now()); save_claims(claims)
    result = chapter_view(book.slug, chapter)
    result["chapterApproval"] = {"approvedNow": approved_now, "holds": holds, "missing": missing, "complete": complete}
    return result


def finish_chapter(payload: dict) -> dict:
    person = authorize(payload.get("name"), payload.get("token")); book, chapter, verses = chapter_or_raise(payload.get("book"), payload.get("chapter"))
    if not payload.get("contextConfirmed"): raise ValueError("Confirm the complete chapter continuity, voice, and flow review.")
    with _lock:
        claims, key = assert_holder(person, book.slug, chapter); missing = [v for v in verses if not human_review_is_current(book.slug, chapter, v) or revision_is_open(book.slug, chapter, v)]
        if missing: raise ValueError("Human review is missing for verse(s): " + ", ".join(map(str, missing)))
        finish_chapter_locked(book, chapter, verses, person)
        claims[key].update(note="Chapter review complete; canonical alignment promoted", updated=now()); save_claims(claims)
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


def nt_syntax_candidate_path(book, chapter: int) -> Path:
    return NT_SYNTAX_CANDIDATES / f"{book.utr_stem}.{chapter}.macula.json"


def nt_chapter_adjudication_fingerprint(book: str, chapter: int) -> str:
    adjudications = read_json(NT_STRUCTURE_ADJUDICATIONS, {})
    relevant = [
        decision
        for decision in adjudications.get("decisions") or []
        if decision.get("book") == book and decision.get("chapter") == chapter
    ]
    payload = {
        "schema": adjudications.get("schema"),
        "book": book,
        "chapter": chapter,
        "decisions": relevant,
    }
    return hashlib.sha256(
        json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def validate_nt_candidate_adjudication_binding(candidate: dict) -> None:
    binding = (candidate.get("provenance") or {}).get("structureAdjudications") or {}
    if (
        str(binding.get("path") or "").replace("\\", "/") != NT_STRUCTURE_ADJUDICATIONS.relative_to(ROOT).as_posix()
        or not NT_STRUCTURE_ADJUDICATIONS.is_file()
        or binding.get("scope") != "chapter"
        or binding.get("sha256") != nt_chapter_adjudication_fingerprint(
            str(candidate.get("book") or ""), int(candidate.get("chapter") or 0)
        )
    ):
        raise ValueError("The NT structural candidate is not bound to current human adjudications.")


def nt_candidate_board_row(candidate: dict, book, chapter: int) -> dict:
    """Describe one candidate without letting it break the whole NT board."""
    try:
        validate_nt_syntax_candidate(candidate)
        validate_nt_candidate_adjudication_binding(candidate)
        if candidate.get("book") != book.slug or candidate.get("chapter") != chapter:
            raise ValueError("Candidate identity does not match its filename.")
    except ValueError as exc:
        summary = candidate.get("summary") if isinstance(candidate.get("summary"), dict) else {}
        return {
            "book": book.slug,
            "label": book.label,
            "chapter": chapter,
            "candidateBuilt": False,
            "status": "stale-candidate",
            "validationError": str(exc),
            "summary": {
                "mappedWords": int(summary.get("mappedWords") or 0),
                "trOnlyTokens": int(summary.get("trOnlyTokens") or 0),
                "unmatchedMaculaWords": int(summary.get("unmatchedMaculaWords") or 0),
                "robinsonDisagreements": int(summary.get("robinsonDisagreements") or 0),
            },
        }
    return {
        "book": book.slug,
        "label": book.label,
        "chapter": chapter,
        "candidateBuilt": True,
        "status": candidate["status"],
        "summary": candidate["summary"],
    }


def nt_syntax_board_signature() -> str:
    paths = sorted(NT_SYNTAX_CANDIDATES.glob("*.macula.json"))
    paths.extend((NT_STRUCTURE_ADJUDICATIONS, NT_MACULA_MAPPING, NT_MACULA_MANIFEST))
    rows = []
    for path in paths:
        try:
            stat = path.stat()
            rows.append((str(path.relative_to(ROOT)), stat.st_size, stat.st_mtime_ns))
        except FileNotFoundError:
            rows.append((str(path), None, None))
    return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode("utf-8")).hexdigest()


def load_validated_nt_mapping() -> dict:
    """Load the pinned triple-agreement ledger once per content hash."""
    global _nt_mapping_cache
    manifest = read_json(NT_MACULA_MANIFEST, {})
    mapping = read_json(NT_MACULA_MAPPING, {})
    expected = (manifest.get("mapping") or {}).get("sha256")
    actual = mapping_sha256(NT_MACULA_MAPPING) if NT_MACULA_MAPPING.is_file() else ""
    if not expected or actual != expected:
        raise ValueError("The NT MACULA mapping ledger is missing or stale.")
    if (manifest.get("mapping") or {}).get("policy") != NT_MACULA_MAPPING_POLICY:
        raise ValueError("The NT MACULA mapping policy is not current.")
    if _nt_mapping_cache is None or _nt_mapping_cache[0] != actual:
        validate_nt_mapping_ledger(mapping)
        _nt_mapping_cache = (actual, mapping)
    return _nt_mapping_cache[1]


def nt_syntax_board() -> dict:
    """List every NT chapter, including candidates not built yet."""
    global _nt_syntax_board_cache
    signature = nt_syntax_board_signature()
    if _nt_syntax_board_cache and _nt_syntax_board_cache[0] == signature:
        return _nt_syntax_board_cache[1]
    with _nt_syntax_board_lock:
        signature = nt_syntax_board_signature()
        if _nt_syntax_board_cache and _nt_syntax_board_cache[0] == signature:
            return _nt_syntax_board_cache[1]
        result = _build_nt_syntax_board()
        _nt_syntax_board_cache = (signature, result)
        return result


def _build_nt_syntax_board() -> dict:
    available_by_key = {}
    by_stem = {book.utr_stem: book for book in NT}
    for path in sorted(NT_SYNTAX_CANDIDATES.glob("*.macula.json")):
        parts = path.name.split(".")
        if len(parts) != 4 or parts[2:] != ["macula", "json"]:
            continue
        book = by_stem.get(parts[0])
        if book is None or not parts[1].isdigit():
            continue
        candidate = read_json(path, {})
        available_by_key[(book.slug, int(parts[1]))] = nt_candidate_board_row(
            candidate, book, int(parts[1])
        )
    mapping = load_validated_nt_mapping()
    by_code = {TR_CODE_BY_STEM[book.utr_stem]: book for book in NT}
    chapter_rows: dict[tuple[str, int], list[dict]] = {}
    for row in mapping.get("verses") or []:
        parts = str(row.get("reference") or "").split(".")
        if len(parts) != 3 or not parts[1].isdigit():
            continue
        book = by_code.get(parts[0])
        if book is not None:
            chapter_rows.setdefault((book.slug, int(parts[1])), []).append(row)
    available = []
    book_order = {book.slug: index for index, book in enumerate(NT)}
    for key, rows in sorted(
        chapter_rows.items(), key=lambda item: (book_order[item[0][0]], item[0][1])
    ):
        built = available_by_key.get(key)
        if built:
            available.append(built)
            continue
        book = get_book(key[0])
        available.append({
            "book": book.slug,
            "label": book.label,
            "chapter": key[1],
            "candidateBuilt": False,
            "status": "not-built",
            "summary": {
                "mappedWords": sum(len(row.get("mapping") or []) for row in rows),
                "trOnlyTokens": sum(len(row.get("unmatchedTrTokenIds") or []) for row in rows),
                "unmatchedMaculaWords": sum(len(row.get("unmatchedMaculaTerminalIds") or []) for row in rows),
                "robinsonDisagreements": sum(len(row.get("nonAgreeingRobinsonTokenIds") or []) for row in rows),
            },
        })
    return {
        "status": "review-only-not-canonical",
        "translationEnabled": False,
        "approvalEnabled": False,
        "mappingPolicy": NT_MACULA_MAPPING_POLICY,
        "candidates": available,
    }


def warm_nt_syntax_board() -> None:
    """Fill the read-only NT menu cache before the first reviewer opens it."""
    try:
        nt_syntax_board()
    except (OSError, ValueError):
        # The request endpoint still reports any global mapping defect. A
        # best-effort startup warmup must never stop Team Desk itself.
        return


def nt_structure_phase_status() -> dict:
    rows = nt_syntax_board()["candidates"]
    unbuilt = [row for row in rows if not row["candidateBuilt"]]
    holds = [
        row for row in rows
        if row["candidateBuilt"]
        and "trAuthorityFallbackVerses" not in row["summary"]
        and (
            int(row["summary"].get("holdGroups") or 0) > 0
            or int(row["summary"].get("trOnlyTokens") or 0) > 0
            or int(row["summary"].get("unmatchedMaculaWords") or 0) > 0
        )
    ]
    return {
        "complete": not unbuilt and not holds,
        "totalChapters": len(rows),
        "unbuiltChapters": len(unbuilt),
        "holdChapters": len(holds),
    }


def build_nt_syntax_candidate(payload: dict) -> dict:
    """Build one no-cost review candidate; this never approves a HOLD."""
    authorize(payload.get("name"), payload.get("token"))
    book = book_or_raise(payload.get("book"))
    try:
        chapter = int(payload.get("chapter"))
    except (TypeError, ValueError) as exc:
        raise ValueError("Choose a valid NT chapter.") from exc
    if book.testament != "nt" or chapter < 1:
        raise ValueError("Choose a valid NT chapter.")
    _run([
        sys.executable,
        str(ROOT / "tools" / "build_nt_macula_candidate.py"),
        book.slug,
        str(chapter),
    ])
    return nt_syntax_view(book.slug, chapter)


def nt_syntax_view(slug: str, chapter) -> dict:
    """Return a validated NT structural candidate and its three-source tokens."""
    try:
        book = get_book(str(slug or ""))
        number = int(chapter)
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Choose an available NT structural candidate.") from exc
    if book.testament != "nt" or number < 1:
        raise ValueError("Choose an available NT structural candidate.")
    path = nt_syntax_candidate_path(book, number)
    candidate = read_json(path, {})
    if not candidate:
        raise ValueError(f"No review-only structural candidate exists for {book.label} {number}.")
    validate_nt_syntax_candidate(candidate)
    validate_nt_candidate_adjudication_binding(candidate)
    if (
        candidate.get("book") != book.slug
        or candidate.get("chapter") != number
        or (candidate.get("provenance") or {}).get("mappingPolicy") != NT_MACULA_MAPPING_POLICY
    ):
        raise ValueError("The NT structural candidate is not bound to the current mapping policy.")
    mapping = load_validated_nt_mapping()
    code = TR_CODE_BY_STEM[book.utr_stem]
    verse_rows = [
        row for row in mapping.get("verses") or []
        if row["reference"].startswith(f"{code}.{number}.")
    ]
    verse_rows.sort(key=lambda row: int(row["reference"].rsplit(".", 1)[-1]))
    verses = []
    all_token_ids: set[str] = set()
    mapped_candidate_ids: set[str] = set()
    adjudicated_tokens: dict[str, str] = {}
    adapted_tokens: dict[str, str] = {}
    unresolved_macula_terminals: set[str] = set()
    fallback_by_reference = {
        row["reference"]: row
        for row in candidate.get("trAuthorityFallbacks") or []
    }
    for fallback in fallback_by_reference.values():
        for token_id in fallback.get("trTokenIds") or []:
            adapted_tokens[token_id] = TR_AUTHORITY_FALLBACK_RULE

    def collect_candidate_ids(node: dict) -> None:
        if node.get("kind") in {"word", "tr-word"}:
            mapped_candidate_ids.add(node["trTokenId"])
        if node.get("kind") == "tr-word":
            if node.get("status") == "human-adjudicated-tr":
                adjudicated_tokens[node["trTokenId"]] = node["decisionId"]
            elif node.get("status") == "tr-authority-adapted":
                adapted_tokens[node["trTokenId"]] = node["adaptationRuleId"]
        if node.get("kind") == "reference-word" and node.get("maculaTerminalId"):
            unresolved_macula_terminals.add(node["maculaTerminalId"])
        for child in node.get("children") or []:
            collect_candidate_ids(child)

    for sentence in candidate.get("sentences") or []:
        for root in sentence.get("roots") or []:
            collect_candidate_ids(root)
    for row in verse_rows:
        verse = int(row["reference"].rsplit(".", 1)[-1])
        source = load_reconciled_verse(book, number, verse)
        terminal_by_token = {
            item["trTokenId"]: item["maculaTerminalId"]
            for item in row.get("mapping") or []
        }
        nonagreeing = set(row.get("nonAgreeingRobinsonTokenIds") or [])
        fallback = fallback_by_reference.get(row["reference"])
        retired_terminals = set(
            (fallback or {}).get("removedMaculaTerminalIds") or []
        )
        tokens = []
        for token in source["trTokens"]:
            token_id = token["tokenId"]
            all_token_ids.add(token_id)
            terminal_id = terminal_by_token.get(token_id)
            decision_id = adjudicated_tokens.get(token_id)
            adaptation_id = adapted_tokens.get(token_id)
            tokens.append({
                "tokenId": token_id,
                "surface": token["surfaceGreek"],
                "surfaceBeta": token["surfaceBeta"],
                "robinsonMorphology": (token.get("morphology") or {}).get("rawTag"),
                "strongs": (token.get("morphology") or {}).get("strongs") or [],
                "maculaTerminalId": terminal_id,
                "tripleAgreement": terminal_id is not None,
                "structurallyResolved": decision_id is not None or adaptation_id is not None,
                "structureDecisionId": decision_id,
                "structureAdaptationRuleId": adaptation_id,
                "structureResolution": (
                    "human" if decision_id is not None
                    else "tr-authority" if adaptation_id is not None
                    else None
                ),
                "holdReason": (
                    None
                    if decision_id is not None or adaptation_id is not None
                    else
                    "La reconciliación SCV/Robinson ya está aprobada; falta resolver la rama MACULA no aislada."
                    if token_id in nonagreeing
                    else "MACULA no ofrece una correspondencia inequívoca para este token."
                    if terminal_id is None
                    else None
                ),
            })
        unresolved = [
            token for token in tokens
            if not token["tripleAgreement"] and not token["structurallyResolved"]
        ]
        unresolved_terminals = [
            terminal_id
            for terminal_id in row.get("unmatchedMaculaTerminalIds") or []
            if terminal_id in unresolved_macula_terminals
            and terminal_id not in retired_terminals
        ]
        verses.append({
            "verse": verse,
            "reference": row["reference"],
            "status": (
                "human-adjudicated-tr"
                if not unresolved and not unresolved_terminals and any(token["structureResolution"] == "human" for token in tokens)
                else "tr-authority-adapted"
                if not unresolved and not unresolved_terminals and (
                    fallback is not None
                    or any(token["structureResolution"] == "tr-authority" for token in tokens)
                )
                else "exact"
                if not unresolved and not unresolved_terminals
                else "hold-token-disagreement"
            ),
            "tokens": tokens,
            "trAuthorityFallback": fallback,
            "unresolvedMaculaTerminalIds": unresolved_terminals,
            "maculaSurfaceOnHold": row.get("maculaSurface"),
        })
    candidate_coverage = (
        mapped_candidate_ids
        | set(candidate.get("trOnlyTokenIds") or [])
        | set(candidate.get("unplacedMappedTrTokenIds") or [])
    )
    if candidate_coverage != all_token_ids:
        raise ValueError("The NT structural candidate does not cover the complete TR chapter.")
    return {
        "book": book.slug,
        "label": book.label,
        "chapter": number,
        "status": "review-only-not-canonical",
        "translationEnabled": False,
        "approvalEnabled": False,
        "mappingPolicy": NT_MACULA_MAPPING_POLICY,
        "summary": candidate["summary"],
        "verses": verses,
        "candidate": candidate,
    }


def board() -> dict:
    return {"model": model_name(), "modelReviewOn": TEAM_MODEL_REVIEW_ON, "reasoningEffort": reasoning_effort(), "draftSpecVersion": DRAFT_SPEC_VERSION, "reviewSpecVersion": REVIEW_SPEC_VERSION, "sourcePolicy": "lbf-source-policy-v4", "textualBasis": "OSHB/WLC + TR1894", "maxRunning": MAX_RUNNING, "running": sum(_alive(k) for k in _threads), "people": sorted(load_people()), "books": [{"slug": b.slug, "label": b.label, "chapters": chapter_count(b.slug)} for b in (*OT, *NT) if chapter_count(b.slug)], "claims": load_claims(), "ntBlocked": False, "ntReadiness": "whole-nt-structure-first"}


def warm_totals() -> None:
    for book in (*OT, *NT): chapter_count(book.slug)
