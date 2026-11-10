"""Fail-closed TBESG loader for secondary Greek lexical possibilities.

TBESG never chooses a contextual sense and never changes the TR1894 surface,
Robinson morphology, or syntax.  It is indexed only by Robinson's lexical
Strong identifier after the local file and provenance have been verified.
"""

from __future__ import annotations

import hashlib
import html
import re
from functools import lru_cache
from pathlib import Path

from books import ROOT

PATH = ROOT / "Lexicons" / "TBESG - Translators Brief lexicon of Extended Strongs for Greek - STEPBible.org CC BY.txt"
SHA256 = "312f723d7b8ef263bbdfb0451c9b8057125804dfff390b6f8544cff2a84b57f4"
UPSTREAM_COMMIT = "ed476a8ee6e3f7b3a46fc48af6c7dabc02387b1d"
LICENSE = "CC BY 4.0"
ATTRIBUTION = "STEPBible.org / Tyndale House Cambridge"
AUTHORITY = "secondary-possibilities-only"
ENTRY = re.compile(r"^G(\d+)\t")
TAG = re.compile(r"<[^>]+>")
SPACE = re.compile(r"\s+")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _plain(value: str) -> str:
    value = re.sub(r"<BR\s*/?>", " ", value, flags=re.IGNORECASE)
    value = TAG.sub(" ", value)
    return SPACE.sub(" ", html.unescape(value)).strip()


@lru_cache(maxsize=1)
def load() -> dict[int, tuple[dict, ...]]:
    if not PATH.is_file() or _sha256(PATH) != SHA256:
        raise ValueError("TBESG is missing or differs from its pinned checksum")
    rows: dict[int, list[dict]] = {}
    for line_number, line in enumerate(PATH.read_text(encoding="utf-8-sig").splitlines(), start=1):
        match = ENTRY.match(line)
        if not match:
            continue
        fields = line.split("\t")
        if len(fields) != 8:
            raise ValueError(f"TBESG line {line_number} has an unexpected field count")
        strong = int(match.group(1))
        # Column 3 is normally the extended Greek identifier, but cross-language
        # name rows may point to an H identifier.  The first column remains the
        # stable Greek lookup key in both cases; the line number disambiguates
        # multiple records for the same base number.
        entry_id = fields[2].strip() or f"G{strong:04d}"
        rows.setdefault(strong, []).append({
            "lexicalEvidenceId": f"TBESG:{entry_id}:{line_number}",
            "source": "STEPBible-TBESG",
            "sourceCommit": UPSTREAM_COMMIT,
            "sourceSha256": SHA256,
            "license": LICENSE,
            "attribution": ATTRIBUTION,
            "authority": AUTHORITY,
            "strong": f"G{strong:04d}",
            "entryId": entry_id,
            "greek": fields[3].strip(),
            "transliteration": fields[4].strip(),
            "lexicalMorphology": fields[5].strip(),
            "gloss": fields[6].strip(),
            "meaning": _plain(fields[7]),
        })
    if not rows:
        raise ValueError("TBESG contains no lexical records")
    return {strong: tuple(entries) for strong, entries in rows.items()}


def lookup(strong: int) -> list[dict]:
    """Return every TBESG possibility for a base Strong number."""
    return [dict(entry) for entry in load().get(int(strong), ())]


def validate_coverage(strongs: set[int]) -> None:
    missing = sorted(set(strongs) - set(load()))
    if missing:
        rendered = ", ".join(f"G{number:04d}" for number in missing[:20])
        raise ValueError(f"TBESG lacks Robinson lexical identifiers: {rendered}")
