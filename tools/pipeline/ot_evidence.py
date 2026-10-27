"""Canonical OT syntax, discourse context, and corpus-usage evidence.

OSHB/WLC remains authoritative. MACULA Hebrew contributes only allowlisted
structural annotations after an exact orthographic-word reconciliation.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
import xml.etree.ElementTree as ET
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

from books import OT, ROOT, Book


MACULA_ROOT = ROOT / "source" / "hebrew" / "macula-hebrew-main"
MACULA_COMMIT = "47db250bd55d0d8577f2a94fba114ef16c35b23c"
MACULA_MANIFEST_SHA256 = "5f5397d2be7856b9863c291f9f017ec55e9c4fddc2f2b0dcbacd658b43738e48"
MACULA_LICENSE = "CC BY 4.0"
MACULA_ATTRIBUTION = (
    "MACULA Hebrew Linguistic Datasets, available at "
    "https://github.com/Clear-Bible/macula-hebrew/"
)

ALLOWED_GROUP_ATTRS = ("class", "rule", "role", "head", "clausetype")
FORBIDDEN_MACULA_ATTRS = {
    "english", "mandarin", "gloss", "greek", "greekstrong", "sdbh",
    "lexdomain", "coredomain", "contextualdomain", "frame", "sensenumber",
}
ACCENTS = re.compile(r"[\u0591-\u05AF\u05BD\u05BF\u05C0\u05C4\u05C5\u05C7]")
OSIS_NS = "http://www.bibletechnologies.net/2003/OSIS/namespace"


def _blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    # Windows checkouts may expand LF to CRLF. Reconstruct the pinned Git blob
    # only for that reversible conversion; all other byte changes remain visible.
    crlf_only = b"\r\n" in data and b"\r" not in data.replace(b"\r\n", b"")
    if crlf_only:
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


@lru_cache(maxsize=1)
def verify_macula_source() -> None:
    """Verify the complete allowlisted local MACULA surface."""
    files = [
        MACULA_ROOT / "LICENSE.md",
        MACULA_ROOT / "README.md",
        *sorted((MACULA_ROOT / "WLC" / "lowfat").glob("*.xml")),
    ]
    if len(files) != 932 or any(not path.is_file() for path in files):
        raise ValueError("MACULA allowlisted source must contain exactly 932 files")
    lines = [
        f"{path.relative_to(MACULA_ROOT).as_posix()} {_blob_sha1(path)}"
        for path in files
    ]
    actual = hashlib.sha256("\n".join(lines).encode()).hexdigest()
    if actual != MACULA_MANIFEST_SHA256:
        raise ValueError(f"MACULA allowlisted manifest checksum mismatch: {actual}")


def _macula_path(book: Book, mt_chapter: int) -> Path:
    matches = sorted(
        (MACULA_ROOT / "WLC" / "lowfat").glob(
            f"{book.book_code:02d}-*-{mt_chapter:03d}-lowfat.xml"
        )
    )
    if len(matches) != 1:
        raise FileNotFoundError(
            f"MACULA chapter mapping is not unique: {book.slug} {mt_chapter}"
        )
    return matches[0]


def _norm_hebrew(value: str) -> str:
    value = unicodedata.normalize("NFC", value or "").replace("/", "")
    return ACCENTS.sub("", value).replace("־", "").strip()


def _ref_parts(ref: str) -> tuple[int, int] | None:
    match = re.search(r"\s(\d+):(\d+)!([0-9]+)$", ref or "")
    if not match:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


@lru_cache(maxsize=256)
def _macula_chapter(book_code: int, mt_chapter: int) -> ET.Element:
    verify_macula_source()
    book = next(item for item in OT if item.book_code == book_code)
    return ET.parse(_macula_path(book, mt_chapter)).getroot()


def _word_groups(root: ET.Element) -> dict[tuple[int, int, int], list[ET.Element]]:
    out: dict[tuple[int, int, int], list[ET.Element]] = defaultdict(list)
    for word in root.iter("w"):
        parts = _ref_parts(word.get("ref") or "")
        if parts:
            out[parts].append(word)
    return out


def _sentence_for(root: ET.Element, refs: set[tuple[int, int, int]]) -> ET.Element | None:
    for sentence in root.findall("sentence"):
        found = {
            parts
            for word in sentence.iter("w")
            if (parts := _ref_parts(word.get("ref") or "")) is not None
        }
        if found & refs:
            return sentence
    return None


def syntax_for_tokens(book: Book, tokens: list[dict]) -> dict:
    """Return allowlisted structural nodes after exact MACULA↔OSHB matching."""
    by_chapter: dict[int, list[dict]] = defaultdict(list)
    for token in tokens:
        match = re.fullmatch(r"[^.]+\.(\d+)\.(\d+)!([0-9]+)", token["oshbRef"])
        if not match:
            raise ValueError(f"invalid canonical OSHB ref: {token['oshbRef']}")
        mt_ch, mt_vs, mt_pos = map(int, match.groups())
        token["_maculaRef"] = (mt_ch, mt_vs, mt_pos)
        by_chapter[mt_ch].append(token)

    structural_nodes: list[dict] = []
    token_roles: dict[str, set[str]] = defaultdict(set)
    matched = 0
    for mt_chapter, chapter_tokens in sorted(by_chapter.items()):
        root = _macula_chapter(book.book_code, mt_chapter)
        groups = _word_groups(root)
        ref_to_id: dict[tuple[int, int, int], str] = {}
        by_verse: dict[int, list[dict]] = defaultdict(list)
        for token in chapter_tokens:
            by_verse[token["_maculaRef"][1]].append(token)
        for mt_verse, verse_tokens in sorted(by_verse.items()):
            candidates = sorted(
                (ref for ref in groups if ref[:2] == (mt_chapter, mt_verse)),
                key=lambda item: item[2],
            )
            cursor = 0
            for token in verse_tokens:
                actual_ref = None
                combined = ""
                for candidate_index in range(cursor, len(candidates)):
                    candidate = candidates[candidate_index]
                    morphs = groups[candidate]
                    candidate_surface = "".join(
                        ("".join(word.itertext()).strip() or word.get("unicode") or "")
                        for word in morphs
                    )
                    candidate_norm = _norm_hebrew(candidate_surface)
                    token_norm = _norm_hebrew(token["surface"])
                    exact = candidate_norm == token_norm
                    transparent_aggregate = (
                        candidate[2] == token["_maculaRef"][2]
                        and token_norm in candidate_norm.split()
                    )
                    if exact or transparent_aggregate:
                        actual_ref = candidate
                        combined = candidate_surface
                        cursor = candidate_index + 1
                        break
                token.pop("_maculaRef", None)
                if actual_ref is None:
                    raise ValueError(
                        f"MACULA/OSHB ordered surface mismatch at {token['oshbRef']}: "
                        f"no match for {token['surface']!r}"
                    )
                matched += 1
                ref_to_id[actual_ref] = token["sourceTokenId"]
                for word in groups[actual_ref]:
                    role = word.get("role")
                    if role:
                        token_roles[token["sourceTokenId"]].add(role)

        refs = set(ref_to_id)
        sentence = _sentence_for(root, refs)
        if sentence is None:
            raise ValueError(f"MACULA sentence missing for {book.slug} {mt_chapter}")

        counter = 0
        for group in sentence.iter("wg"):
            group_refs = [
                parts
                for word in group.iter("w")
                if (parts := _ref_parts(word.get("ref") or "")) in refs
            ]
            ids = list(dict.fromkeys(ref_to_id[ref] for ref in group_refs))
            if not ids:
                continue
            counter += 1
            node = {"nodeId": f"m{book.book_code:02d}{mt_chapter:03d}{counter:04d}"}
            for attr in ALLOWED_GROUP_ATTRS:
                if group.get(attr):
                    node[attr] = group.get(attr)
            node["sourceTokenIds"] = ids
            structural_nodes.append(node)

    return {
        "source": "MACULA-Hebrew-structure-only",
        "sourceCommit": MACULA_COMMIT,
        "license": MACULA_LICENSE,
        "attribution": MACULA_ATTRIBUTION,
        "mapping": {"matched": matched, "total": len(tokens), "status": "exact"},
        "nodes": structural_nodes,
        "tokenRoles": {
            token_id: sorted(roles) for token_id, roles in sorted(token_roles.items())
        },
    }


def normalized_lemma(lemma: str) -> str:
    return (lemma or "").split("/")[-1].strip().lower()


@lru_cache(maxsize=1)
def _corpus_index() -> dict[str, list[dict]]:
    """Index only canonical OSHB evidence; no glosses or translations."""
    out: dict[str, list[dict]] = defaultdict(list)
    ns = f"{{{OSIS_NS}}}"
    for book in OT:
        root = ET.parse(book.xml_path).getroot()
        for verse in root.iter(f"{ns}verse"):
            osis = verse.get("osisID") or ""
            match = re.fullmatch(rf"{re.escape(book.osis)}\.(\d+)\.(\d+)", osis)
            if not match:
                continue
            chapter, number = map(int, match.groups())
            verse_rows = []
            position = 0
            children = list(verse)
            canonical_words = []
            for child_index, word in enumerate(children):
                if word.tag.rsplit("}", 1)[-1] != "w":
                    continue
                if word.get("type") == "x-ketiv":
                    if child_index + 1 < len(children):
                        qere = next(
                            (node for node in children[child_index + 1].iter() if node.tag.rsplit("}", 1)[-1] == "w"),
                            None,
                        )
                        if qere is not None:
                            canonical_words.append(qere)
                    continue
                canonical_words.append(word)
            for word in canonical_words:
                position += 1
                lemma = word.get("lemma") or ""
                verse_rows.append(
                    {
                        "bookCode": book.book_code,
                        "reference": osis,
                        "mtChapter": chapter,
                        "mtVerse": number,
                        "mtPosition": position,
                        "surface": "".join(word.itertext()).strip().replace("/", ""),
                        "lemma": lemma,
                        "morph": word.get("morph") or "",
                        "oshbId": word.get("id") or "",
                    }
                )
            for index, row in enumerate(verse_rows):
                row["context"] = [
                    item["surface"]
                    for item in verse_rows[max(0, index - 2): index + 3]
                ]
                row["previousLemma"] = (
                    normalized_lemma(verse_rows[index - 1]["lemma"])
                    if index > 0 else None
                )
                row["nextLemma"] = (
                    normalized_lemma(verse_rows[index + 1]["lemma"])
                    if index + 1 < len(verse_rows) else None
                )
                out[normalized_lemma(row["lemma"])].append(row)
    return out


def _spread(rows: list[dict], limit: int) -> list[dict]:
    if limit <= 0:
        return []
    if limit == 1:
        return rows[:1]
    if len(rows) <= limit:
        return rows
    return [rows[round(i * (len(rows) - 1) / (limit - 1))] for i in range(limit)]


def _corpus_role(row: dict) -> tuple[list[str], str | None]:
    root = _macula_chapter(row["bookCode"], row["mtChapter"])
    groups = _word_groups(root)
    expected = (row["mtChapter"], row["mtVerse"], row["mtPosition"])
    candidates = []
    for candidate, morphs in groups.items():
        if candidate[:2] != expected[:2]:
            continue
        combined = "".join(
            word.get("unicode") or "".join(word.itertext()) for word in morphs
        )
        if _norm_hebrew(combined) == _norm_hebrew(row["surface"]):
            candidates.append(candidate)
    ref = min(candidates, key=lambda item: abs(item[2] - expected[2])) if candidates else expected
    morphs = groups.get(ref) or []
    roles = sorted({word.get("role") for word in morphs if word.get("role")})
    sentence = _sentence_for(root, {ref})
    clause_rule = None
    if sentence is not None:
        for group in sentence.iter("wg"):
            if any(_ref_parts(word.get("ref") or "") == ref for word in group.iter("w")):
                if group.get("class") == "cl":
                    clause_rule = group.get("rule")
                    break
    return roles, clause_rule


def corpus_usage(
    lemma: str,
    morph: str,
    limit: int = 3,
    *,
    previous_lemma: str | None = None,
    next_lemma: str | None = None,
    target_oshb_id: str | None = None,
) -> dict:
    rows = list(_corpus_index().get(normalized_lemma(lemma), []))
    exact = [row for row in rows if row["morph"] == morph]
    previous = normalized_lemma(previous_lemma or "") or None
    following = normalized_lemma(next_lemma or "") or None
    previous_matches = [
        row for row in rows
        if row["oshbId"] != target_oshb_id
        and previous is not None
        and row.get("previousLemma") == previous
    ]
    previous_ids = {row["oshbId"] for row in previous_matches}
    next_matches = [
        row for row in rows
        if row["oshbId"] != target_oshb_id
        and row["oshbId"] not in previous_ids
        and following is not None
        and row.get("nextLemma") == following
    ]
    parallels = previous_matches + next_matches
    selected = parallels[:limit]
    if len(selected) < limit:
        used = {row["oshbId"] for row in selected}
        selected += _spread(
            [row for row in exact if row["oshbId"] not in used],
            limit - len(selected),
        )
    if len(selected) < limit:
        used = {row["oshbId"] for row in selected}
        selected += _spread([row for row in rows if row["oshbId"] not in used], limit - len(selected))
    samples = []
    for row in selected:
        roles, clause_rule = _corpus_role(row)
        samples.append(
            {
                "reference": row["reference"],
                "surface": row["surface"],
                "lemma": row["lemma"],
                "morph": row["morph"],
                "syntaxRoles": roles,
                "clauseRule": clause_rule,
                "oshbId": row["oshbId"],
                "originalContext": row["context"],
            }
        )
    return {
        "source": "OSHB/WLC-corpus",
        "selection": "exact-neighbor-collocation-then-morph-then-lemma-spread",
        "lemma": normalized_lemma(lemma),
        "totalOccurrences": len(rows),
        "exactMorphOccurrences": len(exact),
        "samples": samples,
    }


def assert_no_forbidden_macula_fields(value: object) -> None:
    if isinstance(value, dict):
        overlap = FORBIDDEN_MACULA_ATTRS & {str(key).lower() for key in value}
        if overlap:
            raise ValueError(f"forbidden MACULA fields leaked: {sorted(overlap)}")
        for child in value.values():
            assert_no_forbidden_macula_fields(child)
    elif isinstance(value, list):
        for child in value:
            assert_no_forbidden_macula_fields(child)
