"""Build a source packet for one Protestant verse.

Allowed evidence is closed by SOURCE_POLICY.md: TR1894 (NT), or OSHB/WLC with
pinned structural syntax, corpus usage, and lexical possibilities (OT). Never
includes another Bible, commentary, or existing LBF Spanish.
"""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from books import ROOT, Book, get_book
from hebrew_lexicon import (
    ATTRIBUTION as HEBREW_LEXICON_ATTRIBUTION,
    LICENSE as HEBREW_LEXICON_LICENSE,
    UPSTREAM_COMMIT as HEBREW_LEXICON_COMMIT,
    lookup as lookup_hebrew_lexicon,
)
from morph import expand_hebrew_morph
from ot_evidence import (
    MACULA_ATTRIBUTION,
    MACULA_COMMIT,
    MACULA_LICENSE,
    assert_no_forbidden_macula_fields,
    corpus_usage,
    normalized_lemma,
    syntax_for_tokens,
)
from paleo import strongs_from_lemma, to_paleo

SOURCE_POLICY = "lbf-source-policy-v4"
OT_EVIDENCE_POLICY = "canonical-ot-evidence-bundle-v1"
NT_EVIDENCE_POLICY = "blocked-pending-canonical-evidence-bundle"
OT_ALLOWED_SOURCES = [
    "OSHB/WLC-surface",
    "OSHB-lemma-morph",
    "Strongs-id-only",
    "OpenScriptures-HebrewLexicon@21c9add13bc727d3a951361778e97e3ff7afd1ce",
    "MACULA-Hebrew-structure-only@47db250bd55d0d8577f2a94fba114ef16c35b23c",
    "OSHB/WLC-corpus-usage",
]
NT_ALLOWED_SOURCES = ["TR1894-surface", "Robinson-morph", "Strongs-id-only"]

OSIS_NS = {"o": "http://www.bibletechnologies.net/2003/OSIS/namespace"}
VERSE_LINE = re.compile(r"^(\d+):(\d+)\s+(.*)$")
TOKEN = re.compile(r"([^{}]*)\{([^}]*)\}")

BETA_MAP = {
    "a": "α", "b": "β", "g": "γ", "d": "δ", "e": "ε", "z": "ζ", "h": "η",
    "q": "θ", "i": "ι", "k": "κ", "l": "λ", "m": "μ", "n": "ν", "c": "χ",
    "o": "ο", "p": "π", "r": "ρ", "s": "σ", "v": "ς", "t": "τ", "u": "υ",
    "f": "φ", "x": "ξ", "y": "ψ", "w": "ω",
}


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _kjv_ref_from_note(note_text: str, osis: str) -> tuple[int, int] | None:
    match = re.search(rf"\bKJV:{re.escape(osis)}\.(\d+)\.(\d+)\b", note_text)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def protestant_ref(verse: ET.Element, osis: str, oshb_ch: int, oshb_vs: int) -> tuple[int, int]:
    """Use an explicit KJV note when OSHB supplies one. Never print MT labels."""
    for child in list(verse):
        if local_name(child.tag) != "note":
            continue
        ref = _kjv_ref_from_note("".join(child.itertext()).strip(), osis)
        if ref:
            return ref
    return oshb_ch, oshb_vs


def protestant_segments(
    verse: ET.Element, osis: str, oshb_ch: int, oshb_vs: int
) -> list[tuple[int, int, list[ET.Element]]]:
    """Protestant (ch, vs) spans inside one OSHB verse, with their word nodes.

    OSHB may put several KJV notes in one verse (e.g. Ps 13:6 → KJV 13:5 then 13:6).
    Words after each note belong to that Protestant verse until the next KJV note.
    Words before the first note stay with that note if it names the same chapter
    (Ps 14:1 title+body); if it names another chapter they keep this OSHB label
    (Isa 63:19 before KJV:Isa.64.1). Verses with no KJV note keep OSHB numbering.
    """
    children = list(verse)
    has_kjv = False
    for child in children:
        if local_name(child.tag) != "note":
            continue
        if _kjv_ref_from_note("".join(child.itertext()).strip(), osis):
            has_kjv = True
            break
    if not has_kjv:
        return [(oshb_ch, oshb_vs, direct_words(verse))]

    segments: list[tuple[int, int, list[ET.Element]]] = []
    current: tuple[int, int] | None = None
    words: list[ET.Element] = []
    pending_before: list[ET.Element] = []
    for child_index, child in enumerate(children):
        name = local_name(child.tag)
        if name == "note":
            ref = _kjv_ref_from_note("".join(child.itertext()).strip(), osis)
            if ref is None:
                continue
            if current is not None:
                segments.append((current[0], current[1], words))
                words = []
            current = ref
            # Words before the first KJV note:
            # same chapter → that Protestant verse (Ps 14:1 title+body);
            # other chapter → this OSHB verse's own Protestant label (Isa 63:19
            # before KJV:Isa.64.1).
            if pending_before:
                if ref[0] == oshb_ch:
                    words = pending_before + words
                else:
                    segments.append((oshb_ch, oshb_vs, pending_before))
                pending_before = []
            continue
        if name != "w":
            continue
        if child.get("type") == "x-ketiv":
            qere = None
            if child_index + 1 < len(children) and local_name(children[child_index + 1].tag) == "note":
                qere = next(
                    (node for node in children[child_index + 1].iter() if local_name(node.tag) == "w"),
                    None,
                )
            if qere is None:
                continue
            child = qere
        if current is None:
            pending_before.append(child)
            continue
        words.append(child)
    if current is not None:
        segments.append((current[0], current[1], words))
    elif pending_before:
        segments.append((oshb_ch, oshb_vs, pending_before))
    return segments


def direct_words(verse: ET.Element) -> list[ET.Element]:
    words = []
    children = list(verse)
    for index, child in enumerate(children):
        if local_name(child.tag) != "w":
            continue
        if child.get("type") == "x-ketiv":
            # The canonical reading used by OSHB is the qere nested in the
            # immediately following variant note. Never silently drop it.
            if index + 1 < len(children) and local_name(children[index + 1].tag) == "note":
                qere = next(
                    (
                        node
                        for node in children[index + 1].iter()
                        if local_name(node.tag) == "w"
                    ),
                    None,
                )
                if qere is not None:
                    words.append(qere)
            continue
        words.append(child)
    return words

def surface(word: ET.Element) -> str:
    return "".join(word.itertext()).strip().replace("/", "")


def token_id(book: Book, chapter: int, verse: int, position: int) -> str:
    prefix = "h" if book.testament == "ot" else "n"
    return f"{prefix}{book.book_code:02d}{chapter:03d}{verse:03d}{position:03d}"


def packet_path(book: Book, chapter: int, verse: int) -> Path:
    return (
        ROOT
        / "pipeline"
        / book.testament
        / book.slug
        / f"{book.slug}-{chapter}-{verse}.packet.json"
    )


def ot_chapter_protestant_map(
    book: Book, chapter: int
) -> dict[int, tuple[list[ET.Element], list[str]]]:
    """Map Protestant verse → (word nodes, OSHB OSIS parts) for one chapter.

    Scan the whole OSHB book. A KJV note wins; a verse with no note keeps its
    OSHB chapter.verse as the Protestant label. Psalm titles (OSHB v1, no note)
    therefore merge with the following KJV:Book.N.1 body into Protestant v1.
    Cross-chapter offsets (Eccl 4:17 = Protestant 5:1; Joel 3 = Protestant 2:28)
    are collected when their KJV note names this chapter. Never print MT labels.
    """
    if not book.xml_path.is_file():
        raise FileNotFoundError(f"OSHB XML missing: {book.xml_path}")
    tree = ET.parse(book.xml_path)
    out: dict[int, tuple[list[ET.Element], list[str]]] = {}

    def append_verse(pvs: int, words: list[ET.Element], osis_parts: list[str]) -> None:
        if not words:
            return
        if pvs not in out:
            out[pvs] = ([], [])
        out[pvs][0].extend(words)
        for part in osis_parts:
            if part not in out[pvs][1]:
                out[pvs][1].append(part)

    for element in tree.getroot().iter():
        if local_name(element.tag) != "verse":
            continue
        osis_id = str(element.get("osisID") or "")
        match = re.fullmatch(rf"{re.escape(book.osis)}\.(\d+)\.(\d+)", osis_id)
        if not match:
            continue
        src_ch, src_vs = int(match.group(1)), int(match.group(2))
        osis_part = f"{book.osis}.{src_ch}.{src_vs}"
        for source_position, word in enumerate(direct_words(element), start=1):
            word.set("_lbfOshbRef", f"{osis_part}!{source_position}")
        for pch, pvs, words in protestant_segments(
            element, book.osis, src_ch, src_vs
        ):
            if pch != chapter:
                continue
            append_verse(pvs, words, [osis_part])
    return out


def build_ot_packet(book: Book, chapter: int, verse: int) -> dict:
    chapter_map = ot_chapter_protestant_map(book, chapter)
    if verse not in chapter_map or not chapter_map[verse][0]:
        raise KeyError(f"{book.slug} {chapter}:{verse} not in {book.xml_path.name}")
    word_nodes, oshb_osis_parts = chapter_map[verse]

    tokens = []
    lexical_entries: dict[str, dict] = {}
    for position, word in enumerate(word_nodes, start=1):
        lemma = word.get("lemma") or ""
        morph = word.get("morph") or ""
        strongs = strongs_from_lemma(lemma)
        hebrew = surface(word)
        entry = {
            "sourceTokenId": token_id(book, chapter, verse, position),
            "oshbId": word.get("id") or "",
            "oshbRef": word.get("_lbfOshbRef") or "",
            "position": position,
            "surface": hebrew,
            "paleo": to_paleo(hebrew),
            "lemma": lemma,
            "strongs": strongs,
            "morph": morph,
            "morphExpanded": expand_hebrew_morph(morph),
        }
        lexical_evidence = lookup_hebrew_lexicon(lemma, morph=morph)
        if lexical_evidence is not None:
            lexical_evidence_id = str(
                lexical_evidence.get("lexicalEvidenceId")
                or lexical_evidence["lexicalIndexId"]
            )
            entry["lexicalEvidenceId"] = lexical_evidence_id
            lexical_entries[lexical_evidence_id] = lexical_evidence
        else:
            entry["lexicalEvidenceId"] = None
        tokens.append(entry)

    syntax = syntax_for_tokens(book, tokens)
    corpus_entries: dict[str, dict] = {}
    for token_index, token in enumerate(tokens):
        key = normalized_lemma(token["lemma"])
        token["corpusEvidenceId"] = key
        if key not in corpus_entries:
            previous_lemma = tokens[token_index - 1]["lemma"] if token_index > 0 else None
            next_lemma = tokens[token_index + 1]["lemma"] if token_index + 1 < len(tokens) else None
            corpus_entries[key] = {
                "corpusEvidenceId": key,
                **corpus_usage(
                    token["lemma"],
                    token["morph"],
                    previous_lemma=previous_lemma,
                    next_lemma=next_lemma,
                    target_oshb_id=token["oshbId"],
                ),
            }
            corpus_entries[key]["targetMorphs"] = [token["morph"]]
        elif token["morph"] not in corpus_entries[key]["targetMorphs"]:
            corpus_entries[key]["targetMorphs"].append(token["morph"])

    context = []
    for context_verse in (verse - 1, verse, verse + 1):
        if context_verse not in chapter_map:
            continue
        context_words, context_osis = chapter_map[context_verse]
        context.append(
            {
                "reference": f"{book.label} {chapter}:{context_verse}",
                "oshbOsis": "+".join(context_osis),
                "relation": "current" if context_verse == verse else "previous" if context_verse < verse else "next",
                "tokens": [
                    {
                        "oshbId": word.get("id") or "",
                        "oshbRef": word.get("_lbfOshbRef") or "",
                        "surface": surface(word),
                        "lemma": word.get("lemma") or "",
                        "morph": word.get("morph") or "",
                    }
                    for word in context_words
                ],
            }
        )

    return {
        "schema": "lbf-source-packet-v1",
        "sourcePolicy": SOURCE_POLICY,
        "evidencePolicy": OT_EVIDENCE_POLICY,
        "evidenceStatus": "READY_FOR_MODEL",
        "book": book.slug,
        "label": book.label,
        "testament": "ot",
        "textualBasis": "OSHB/WLC",
        "reference": f"{book.label} {chapter}:{verse}",
        "chapter": chapter,
        "verse": verse,
        "oshbOsis": "+".join(oshb_osis_parts),
        "allowedSources": list(OT_ALLOWED_SOURCES),
        "forbiddenSources": [
            "memory",
            "theology",
            "RV1909",
            "BLE-gloss",
            "other-versions",
            "unapproved-lexicons",
            "web-or-retrieval",
            "macula",
            "AHRC/AHLB",
        ],
        "tokens": tokens,
        "lexicalEvidence": list(lexical_entries.values()),
        "syntax": syntax,
        "originalLanguageContext": context,
        "corpusEvidence": list(corpus_entries.values()),
    }

def beta_to_unicode(beta: str) -> str:
    out: list[str] = []
    chars = list((beta or "").lower())
    i = 0
    while i < len(chars):
        ch = chars[i]
        if ch == "*":
            i += 1
            if i < len(chars):
                mapped = BETA_MAP.get(chars[i], chars[i])
                out.append(mapped.upper() if mapped.isalpha() else mapped)
                i += 1
            continue
        if ch == "s":
            nxt = chars[i + 1] if i + 1 < len(chars) else ""
            out.append("ς" if not nxt or nxt not in BETA_MAP else "σ")
            i += 1
            continue
        out.append(BETA_MAP.get(ch, ch))
        i += 1
    return "".join(out)


def parse_utr_verse(path: Path, chapter: int, verse: int) -> list[dict]:
    current = None
    buffer: list[str] = []
    found: list[str] | None = None

    def flush() -> None:
        nonlocal found
        if current == (chapter, verse):
            found = buffer.copy()

    for line in path.read_text(encoding="utf-8").splitlines():
        match = VERSE_LINE.match(line)
        if match:
            flush()
            current = (int(match.group(1)), int(match.group(2)))
            buffer = [match.group(3)]
        elif current is not None and line.strip():
            buffer.append(line.strip())
    flush()
    if found is None:
        raise KeyError(f"{path.name} {chapter}:{verse} not in TR1894")
    body = " ".join(found)
    tokens = []
    position = 0
    for chunk, morph in TOKEN.findall(body):
        words = chunk.replace("|", " ").split()
        strongs: list[str] = []
        surfaces: list[str] = []
        for word in words:
            if word.isdigit():
                strongs.append(word)
            else:
                surfaces.append(word.strip("[]"))
        if not surfaces and not strongs:
            continue
        position += 1
        beta = surfaces[0] if surfaces else ""
        tokens.append(
            {
                "position": position,
                "surfaceBeta": beta,
                "surfaceGreek": beta_to_unicode(beta),
                "surfaceVariants": [beta_to_unicode(item) for item in surfaces[1:]],
                "strongs": f"G{int(strongs[0])}" if strongs else None,
                "morph": morph,
            }
        )
    return tokens


def build_nt_packet(book: Book, chapter: int, verse: int) -> dict:
    if not book.utr_path.is_file():
        raise FileNotFoundError(f"TR1894 UTR missing: {book.utr_path}")
    rows = parse_utr_verse(book.utr_path, chapter, verse)
    tokens = []
    for row in rows:
        tokens.append(
            {
                "sourceTokenId": token_id(book, chapter, verse, row["position"]),
                "position": row["position"],
                "surface": row["surfaceGreek"],
                "surfaceBeta": row["surfaceBeta"],
                "surfaceVariants": row["surfaceVariants"],
                "lemma": None,
                "strongs": row["strongs"],
                "morph": row["morph"],
            }
        )
    return {
        "schema": "lbf-source-packet-v1",
        "sourcePolicy": SOURCE_POLICY,
        "evidencePolicy": NT_EVIDENCE_POLICY,
        "book": book.slug,
        "label": book.label,
        "testament": "nt",
        "textualBasis": "TR1894",
        "reference": f"{book.label} {chapter}:{verse}",
        "chapter": chapter,
        "verse": verse,
        "allowedSources": list(NT_ALLOWED_SOURCES),
        "forbiddenSources": [
            "memory",
            "theology",
            "RV1909",
            "BLE-gloss",
            "critical-text",
            "other-versions",
            "lexicons",
            "web-or-retrieval",
            "macula",
        ],
        "tokens": tokens,
    }


def list_ot_verses(book: Book, chapter: int) -> list[int]:
    chapter_map = ot_chapter_protestant_map(book, chapter)
    verses = sorted(v for v, (words, _) in chapter_map.items() if words)
    if not verses:
        raise KeyError(f"{book.slug} chapter {chapter} not in {book.xml_path.name}")
    return verses

def list_nt_verses(book: Book, chapter: int) -> list[int]:
    if not book.utr_path.is_file():
        raise FileNotFoundError(f"TR1894 UTR missing: {book.utr_path}")
    verses: list[int] = []
    seen: set[int] = set()
    for line in book.utr_path.read_text(encoding="utf-8").splitlines():
        match = VERSE_LINE.match(line)
        if not match:
            continue
        ch, vs = int(match.group(1)), int(match.group(2))
        if ch == chapter and vs not in seen:
            seen.add(vs)
            verses.append(vs)
    if not verses:
        raise KeyError(f"{book.slug} chapter {chapter} not in {book.utr_path.name}")
    return verses


def list_verses(slug: str, chapter: int) -> list[int]:
    """Protestant verse numbers in one chapter. Never MT labels."""
    book = get_book(slug)
    if book.testament == "ot":
        return list_ot_verses(book, chapter)
    return list_nt_verses(book, chapter)


def build_packet(slug: str, chapter: int, verse: int) -> dict:
    book = get_book(slug)
    if book.testament == "ot":
        return build_ot_packet(book, chapter, verse)
    return build_nt_packet(book, chapter, verse)


def validate_packet(packet: dict) -> None:
    """Refuse packets outside the closed canonical source policy."""
    testament = packet.get("testament")
    expected_basis = "OSHB/WLC" if testament == "ot" else "TR1894" if testament == "nt" else None
    expected_sources = OT_ALLOWED_SOURCES if testament == "ot" else NT_ALLOWED_SOURCES if testament == "nt" else None
    if packet.get("schema") != "lbf-source-packet-v1":
        raise ValueError("noncanonical source packet schema")
    if packet.get("sourcePolicy") != SOURCE_POLICY:
        raise ValueError("source packet does not bind SOURCE_POLICY.md")
    if packet.get("textualBasis") != expected_basis:
        raise ValueError("source packet has a noncanonical textual basis")
    if packet.get("allowedSources") != expected_sources:
        raise ValueError("source packet has a noncanonical source allowlist")
    if any("ahrc" in token for token in packet.get("tokens") or []):
        raise ValueError("AHRC evidence is prohibited by SOURCE_POLICY.md")
    if testament == "ot":
        evidence = packet.get("lexicalEvidence")
        if not isinstance(evidence, list):
            raise ValueError("OT packet is missing canonical lexical evidence")
        ids = set()
        for entry in evidence:
            if (
                entry.get("source") != "OpenScriptures-HebrewLexicon"
                or entry.get("sourceCommit") != HEBREW_LEXICON_COMMIT
                or entry.get("license") != HEBREW_LEXICON_LICENSE
                or entry.get("attribution") != HEBREW_LEXICON_ATTRIBUTION
                or entry.get("authority") != "secondary-possibilities-only"
            ):
                raise ValueError("OT packet has noncanonical lexical evidence")
            ids.add(entry.get("lexicalEvidenceId") or entry.get("lexicalIndexId"))
        for token in packet.get("tokens") or []:
            lexical_id = token.get("lexicalEvidenceId")
            if lexical_id is not None and lexical_id not in ids:
                raise ValueError("OT token cites missing lexical evidence")
        syntax = packet.get("syntax") or {}
        if (
            syntax.get("source") != "MACULA-Hebrew-structure-only"
            or syntax.get("sourceCommit") != MACULA_COMMIT
            or syntax.get("license") != MACULA_LICENSE
            or syntax.get("attribution") != MACULA_ATTRIBUTION
            or syntax.get("mapping", {}).get("status") != "exact"
            or syntax.get("mapping", {}).get("matched") != len(packet.get("tokens") or [])
        ):
            raise ValueError("OT packet has incomplete or noncanonical syntax")
        allowed_ids = {token.get("sourceTokenId") for token in packet.get("tokens") or []}
        for node in syntax.get("nodes") or []:
            if not node.get("sourceTokenIds") or not set(node["sourceTokenIds"]) <= allowed_ids:
                raise ValueError("OT syntax cites noncanonical token IDs")
        if not packet.get("originalLanguageContext"):
            raise ValueError("OT packet is missing original-language context")
        corpus_ids = {item.get("corpusEvidenceId") for item in packet.get("corpusEvidence") or []}
        if not corpus_ids or any(
            token.get("corpusEvidenceId") not in corpus_ids
            for token in packet.get("tokens") or []
        ):
            raise ValueError("OT packet is missing corpus-usage evidence")
        assert_no_forbidden_macula_fields(packet)
        if packet.get("evidencePolicy") != OT_EVIDENCE_POLICY or packet.get("evidenceStatus") != "READY_FOR_MODEL":
            raise ValueError("OT evidence bundle is not ready for model use")


def packet_for_prompt(packet: dict) -> dict:
    """Return a compact, authorized projection for a live model prompt.

    The full packet remains the validated evidence record on disk. Repeated
    provenance, storage identifiers, and duplicated current-verse context do
    not carry semantic evidence and are intentionally omitted here.
    """
    validate_packet(packet)
    if packet.get("evidencePolicy") == NT_EVIDENCE_POLICY:
        raise RuntimeError(
            "model translation blocked: canonical form+morphology+syntax+discourse+corpus evidence bundle is incomplete"
        )
    tokens = []
    for token in packet.get("tokens") or []:
        tokens.append(
            {
                key: token.get(key)
                for key in (
                    "sourceTokenId",
                    "surface",
                    "lemma",
                    "strongs",
                    "morph",
                    "morphExpanded",
                    "lexicalEvidenceId",
                    "corpusEvidenceId",
                )
                if token.get(key) is not None
            }
        )

    lexical = []
    for entry in packet.get("lexicalEvidence") or []:
        lexical.append(
            {
                key: entry.get(key)
                for key in (
                    "lexicalEvidenceId",
                    "lexicalIndexId",
                    "headword",
                    "transliteration",
                    "partOfSpeech",
                    "bdbFormCrossReference",
                    "possibleSenses",
                )
                if entry.get(key) not in (None, [], "")
            }
        )

    syntax = packet.get("syntax") or {}
    syntax_nodes = []
    for node in syntax.get("nodes") or []:
        compact = {
            key: node.get(key)
            for key in (
                "class",
                "rule",
                "role",
                "head",
                "clausetype",
                "sourceTokenIds",
            )
            if node.get(key) not in (None, [], "")
        }
        if any(key in compact for key in ("class", "rule", "role", "head", "clausetype")):
            syntax_nodes.append(compact)

    context = []
    for item in packet.get("originalLanguageContext") or []:
        if item.get("relation") == "current":
            continue
        context.append(
            {
                "reference": item.get("reference"),
                "relation": item.get("relation"),
                "tokens": [
                    [token.get("surface"), token.get("lemma"), token.get("morph")]
                    for token in item.get("tokens") or []
                ],
            }
        )

    corpus = []
    for entry in packet.get("corpusEvidence") or []:
        samples = []
        for sample in (entry.get("samples") or [])[:2]:
            samples.append(
                {
                    key: sample.get(key)
                    for key in (
                        "reference",
                        "surface",
                        "morph",
                        "syntaxRoles",
                        "clauseRule",
                        "originalContext",
                    )
                    if sample.get(key) not in (None, [], "")
                }
            )
        corpus.append(
            {
                "corpusEvidenceId": entry.get("corpusEvidenceId"),
                "lemma": entry.get("lemma"),
                "targetMorphs": entry.get("targetMorphs") or [],
                "samples": samples,
            }
        )

    return {
        "promptProfile": "canonical-ot-compact-v1",
        "sourcePolicy": packet["sourcePolicy"],
        "evidencePolicy": packet["evidencePolicy"],
        "book": packet["book"],
        "reference": packet["reference"],
        "chapter": packet["chapter"],
        "verse": packet["verse"],
        "textualBasis": packet["textualBasis"],
        "tokens": tokens,
        "lexicalEvidence": lexical,
        "syntax": {
            "mappingStatus": syntax.get("mapping", {}).get("status"),
            "nodes": syntax_nodes,
            "tokenRoles": syntax.get("tokenRoles") or {},
        },
        "originalLanguageContext": context,
        "corpusEvidence": corpus,
    }


def dump_prompt(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def write_packet(packet: dict) -> Path:
    book = get_book(packet["book"])
    path = packet_path(book, packet["chapter"], packet["verse"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
