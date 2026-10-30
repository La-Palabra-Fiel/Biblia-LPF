"""Pinned, fail-closed access to the Open Scriptures Hebrew Lexicon.

This module is the only automatic Hebrew lexicon loader for LBF. It maps the
augmented Strong identifier carried by OSHB to the Open Scriptures lexical
index and its BDB entry. Lexical data documents possibilities; it never picks
the contextual sense.
"""

from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from functools import lru_cache
from pathlib import Path

from books import ROOT


LEXICON_DIR = ROOT / "Lexicons" / "HebrewLexicon-master"
UPSTREAM = "https://github.com/openscriptures/HebrewLexicon"
UPSTREAM_COMMIT = "21c9add13bc727d3a951361778e97e3ff7afd1ce"
LICENSE = "CC BY 4.0"
ATTRIBUTION = "Open Scriptures Hebrew Bible Project"
NS = {"o": "http://openscriptures.github.com/morphhb/namespace"}

PINNED_SHA256 = {
    "AugIndex.xml": "e7217ca8ff8ff3f21f9cf1bbe87411adf55f6aa88bcf5ed9ddc886cc6b160c5d",
    "BrownDriverBriggs.xml": "2b52658a4323d91674cda4090ab8b3ebddfff640f4f18143c28300e80b2c38f8",
    "LexicalIndex.xml": "8f7a605c58899d2f44430149c143c00903976e1e91232476677972a69e5bc85f",
    "HebrewStrong.xml": "a628f4f89f8bdaf2483fd3faf1abc8653cc6717758dfc9f24beb7571d9bdd0c4",
    "readme.md": "9a129c25674387c494571c3828aa3a8eb78459c165e275c313ae26994ce8ff22",
}

# BDB sometimes redirects an inflected form away from the entry selected by
# the augmented Strong index.  These redirects are lexical provenance, not a
# contextual sense choice.  Keep them narrow and verify every referenced node
# against the pinned BDB file before exposing the resolved possibilities.
FORM_BDB_REDIRECTS = {
    # BDB l.ap.ac: לְהָטִים v. לוּט.  Its noun entry l.ax.ab documents
    # "with their mysteries = enchantments".  The singular H3858 remains the
    # flame entry used in Genesis 3:24; only plural noun forms take this link.
    "3858": {
        "morphFragment": "Ncmp",
        "crossReferenceEntryId": "l.ap.ac",
        "targetRootEntryId": "l.ax.aa",
        "resolvedEntryId": "l.ax.ab",
    },
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@lru_cache(maxsize=1)
def verify_pinned_files() -> None:
    """Refuse missing or changed lexical sources."""
    for name, expected in PINNED_SHA256.items():
        path = LEXICON_DIR / name
        if not path.is_file():
            raise FileNotFoundError(f"pinned Hebrew lexicon file missing: {path}")
        actual = _sha256(path)
        if actual != expected:
            content = path.read_bytes()
            # Windows checkouts may expand LF to CRLF. Accept only that
            # reversible line-ending conversion when the pinned LF hash matches.
            crlf_only = b"\r\n" in content and b"\r" not in content.replace(b"\r\n", b"")
            normalized = hashlib.sha256(content.replace(b"\r\n", b"\n")).hexdigest() if crlf_only else None
            if normalized != expected:
                raise ValueError(
                    f"pinned Hebrew lexicon checksum mismatch: {name}: {actual}"
                )


def augmented_strong(oshb_lemma: str) -> str | None:
    """Return OSHB's augmented Strong key, stripping only morphology prefixes."""
    final = (oshb_lemma or "").split("/")[-1].strip().lower()
    match = re.fullmatch(r"(\d+)\s*([a-z]?)", final)
    if not match:
        return None
    return f"{int(match.group(1))}{match.group(2)}"


def _text(element: ET.Element | None) -> str | None:
    if element is None:
        return None
    value = " ".join("".join(element.itertext()).split())
    return value or None


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _definitions(
    entry: ET.Element | None, *, include_tail_equivalents: bool = False
) -> list[str]:
    if entry is None:
        return []
    values = [_text(node) or "" for node in entry.findall(".//o:def", NS)]
    # Some BDB senses put an English equivalent after a <def> node, e.g.
    # "with their mysteries = enchantments".  Preserve the right-hand
    # equivalent instead of silently dropping it with XML tail text.
    if include_tail_equivalents:
        for sense in entry.findall(".//o:sense", NS):
            text = _text(sense) or ""
            if "=" in text:
                values.extend(part.strip() for part in text.split("=")[1:])
    return _unique(values)


def _form_bdb_redirect(
    key: str, morph: str, bdb_entries: dict[str, ET.Element]
) -> dict[str, str] | None:
    spec = FORM_BDB_REDIRECTS.get(key)
    if spec is None or spec["morphFragment"] not in (morph or ""):
        return None
    cross_reference = bdb_entries.get(spec["crossReferenceEntryId"])
    resolved = bdb_entries.get(spec["resolvedEntryId"])
    if cross_reference is None or resolved is None:
        raise ValueError(f"pinned BDB form redirect is incomplete for H{key}")
    targets = {
        str(node.get("src"))
        for node in cross_reference.findall(".//o:w[@src]", NS)
        if node.get("src")
    }
    if spec["targetRootEntryId"] not in targets:
        raise ValueError(f"pinned BDB form redirect changed for H{key}")
    return spec


@lru_cache(maxsize=1)
def _indexes() -> tuple[dict[str, str], dict[str, ET.Element], dict[str, ET.Element]]:
    verify_pinned_files()
    aug_root = ET.parse(LEXICON_DIR / "AugIndex.xml").getroot()
    lexical_root = ET.parse(LEXICON_DIR / "LexicalIndex.xml").getroot()
    bdb_root = ET.parse(LEXICON_DIR / "BrownDriverBriggs.xml").getroot()

    augmented = {
        str(node.get("aug")): (_text(node) or "")
        for node in aug_root.findall(".//o:w", NS)
        if node.get("aug") and _text(node)
    }
    lexical = {
        str(node.get("id")): node
        for node in lexical_root.findall(".//o:entry", NS)
        if node.get("id")
    }
    bdb = {
        str(node.get("id")): node
        for node in bdb_root.findall(".//o:entry", NS)
        if node.get("id")
    }
    return augmented, lexical, bdb


def lookup(oshb_lemma: str, *, morph: str = "") -> dict | None:
    """Return compact lexical possibilities for one OSHB lemma."""
    key = augmented_strong(oshb_lemma)
    if key is None:
        return None
    augmented, lexical_entries, bdb_entries = _indexes()
    lexical_id = augmented.get(key)
    lexical = lexical_entries.get(lexical_id or "")
    if lexical is None:
        return None

    word = lexical.find("o:w", NS)
    xref = lexical.find("o:xref", NS)
    indexed_bdb_id = xref.get("bdb") if xref is not None else None
    redirect = _form_bdb_redirect(key, morph, bdb_entries)
    bdb_id = redirect["resolvedEntryId"] if redirect else indexed_bdb_id
    bdb = bdb_entries.get(bdb_id or "")
    definitions = []
    references = []
    if bdb is not None:
        definitions = _definitions(bdb, include_tail_equivalents=bool(redirect))
        references = _unique(
            [str(node.get("r")) for node in bdb.findall(".//o:ref", NS) if node.get("r")]
        )

    lexical_evidence_id = lexical_id
    if redirect:
        lexical_evidence_id = f"{lexical_id}@{bdb_id}"

    result = {
        "source": "OpenScriptures-HebrewLexicon",
        "sourceCommit": UPSTREAM_COMMIT,
        "license": LICENSE,
        "attribution": ATTRIBUTION,
        "augmentedStrong": key,
        "lexicalIndexId": lexical_id,
        "headword": _text(word),
        "transliteration": word.get("xlit") if word is not None else None,
        "partOfSpeech": _text(lexical.find("o:pos", NS)),
        "indexDefinition": _text(lexical.find("o:def", NS)),
        "bdbEntryId": bdb_id,
        "possibleSenses": definitions,
        "corpusReferences": references,
        "authority": "secondary-possibilities-only",
    }
    if redirect:
        result["lexicalEvidenceId"] = lexical_evidence_id
        result["bdbIndexedEntryId"] = indexed_bdb_id
        result["bdbFormCrossReference"] = {
            "entryId": redirect["crossReferenceEntryId"],
            "targetRootEntryId": redirect["targetRootEntryId"],
            "resolvedEntryId": redirect["resolvedEntryId"],
        }
    return result
