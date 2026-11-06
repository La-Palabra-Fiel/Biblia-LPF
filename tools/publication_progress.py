#!/usr/bin/env python3
"""Canonical chapter alignment promotion and LPF website progress state.

``LBF`` remains the historical technical identifier used by paths and schemas.
The public/editorial name is LPF.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSE_HEADING = re.compile(r"^###\s+(\d+):(\d+)\s*$")
REF_IN_LINK = re.compile(r"(\d+):(\d+)")
FINISHED_LINK_STATUSES = {"hand", "manual", "manual-realign"}
WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)


def read_json(path: Path, default):
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def object_sha256(payload) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def parse_translation(path: Path) -> dict[tuple[int, int], str]:
    verses: dict[tuple[int, int], str] = {}
    current: tuple[int, int] | None = None
    buffer: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = VERSE_HEADING.match(line.strip())
        if match:
            if current is not None:
                verses[current] = " ".join(buffer).strip()
            current = (int(match.group(1)), int(match.group(2)))
            buffer = []
            continue
        if current is not None and line.strip() and not line.startswith("#") and not line.startswith(">"):
            buffer.append(line.strip())
    if current is not None:
        verses[current] = " ".join(buffer).strip()
    return verses


def normalize_lexical(text: str) -> str:
    return re.sub(r"[^\w]+", "", text, flags=re.UNICODE).casefold()


def words_only_surface(text: str) -> bool:
    """True when a canonical surface contains words separated only by space."""
    return bool(re.fullmatch(r"[^\W_]+(?:\s+[^\W_]+)*", str(text or ""), re.UNICODE))


def alignment_path(book: str, testament: str) -> Path:
    return ROOT / "alignment" / testament / book / f"{book}-reverse-links.json"


def pipeline_dir(book: str, testament: str) -> Path:
    return ROOT / "pipeline" / testament / book


def chapter_review_path(book: str, testament: str, chapter: int) -> Path:
    return pipeline_dir(book, testament) / f"{book}-{chapter}.human-review.json"


def human_candidate_path(book: str, testament: str, chapter: int, verse: int) -> Path:
    return pipeline_dir(book, testament) / f"{book}-{chapter}-{verse}.candidate-human-reviewed.json"


def reference_key(link: dict) -> tuple[int, int] | None:
    match = REF_IN_LINK.search(str(link.get("reference") or ""))
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def canonical_units(spanish: str, units: list[dict], phrase_index: int) -> list[dict]:
    """Bind approved words to exact spans without canonicalizing punctuation."""
    result: list[dict] = []
    cursor = 0
    for unit in units:
        surface = str(unit.get("es") or "")
        ids = [str(value) for value in (unit.get("sourceTokenIds") or []) if str(value)]
        if not surface or not ids:
            raise ValueError("Approved alignment units require Spanish and source token IDs.")
        word_matches: list[tuple[int, int]] = []
        for source_word in WORD_RE.findall(surface):
            pattern = re.compile(
                rf"(?<![^\W_]){re.escape(source_word)}(?![^\W_])", re.IGNORECASE
            )
            match = pattern.search(spanish, cursor)
            if not match:
                raise ValueError(
                    f'Approved word {source_word!r} from unit {surface!r} '
                    f'does not occur in order in {spanish!r}.'
                )
            word_matches.append(match.span())
            cursor = match.end()
        if not word_matches:
            raise ValueError(f"Approved alignment unit {surface!r} has no words.")

        runs: list[tuple[int, int]] = []
        run_start, run_end = word_matches[0]
        for start, end in word_matches[1:]:
            separator = spanish[run_end:start]
            if not separator or separator.isspace():
                run_end = end
            else:
                runs.append((run_start, run_end))
                run_start, run_end = start, end
        runs.append((run_start, run_end))

        for start, end in runs:
            canonical_surface = spanish[start:end]
            if not words_only_surface(canonical_surface):
                raise ValueError(f"Canonical alignment surface is not word-only: {canonical_surface!r}")
            result.append(
                {
                    "unitId": f"{phrase_index}:{len(result)}",
                    "surface": canonical_surface,
                    "charStart": start,
                    "charEnd": end,
                    "sourceTokenIds": ids,
                    "method": "hand",
                    "status": "confirmed",
                }
            )
    if normalize_lexical("".join(unit["surface"] for unit in result)) != normalize_lexical(spanish):
        raise ValueError("Approved alignment units do not reconstruct the canonical Spanish.")
    return result


def _phrase_index(
    key: tuple[int, int], ordered_keys: list[tuple[int, int]], links: list[dict]
) -> int:
    for link in links:
        if reference_key(link) == key:
            return int(link["phraseIndex"])
    preferred = ordered_keys.index(key)
    used = {
        int(link["phraseIndex"])
        for link in links
        if isinstance(link, dict) and isinstance(link.get("phraseIndex"), int)
    }
    if preferred not in used:
        return preferred
    return max(used, default=-1) + 1


def promote_chapter_alignment(
    *, book: str, testament: str, label: str, chapter: int, verses: list[int]
) -> Path:
    """Promote one explicitly approved Team Desk chapter to canonical alignment."""
    translation_file = ROOT / "translation" / testament / f"{book}.md"
    translations = parse_translation(translation_file)
    expected = [(chapter, verse) for verse in verses]
    if [key for key in translations if key[0] == chapter] != expected:
        raise ValueError(f"{label} {chapter} does not match its Protestant verse list.")

    path = alignment_path(book, testament)
    document = read_json(
        path,
        {
            "bookId": book,
            "textualBasis": "OSHB/WLC" if testament == "ot" else "TR",
            "schemaVersion": 1,
            "numbering": "protestant",
            "links": [],
        },
    )
    links = list(document.get("links") or [])
    ordered_keys = list(translations)
    replacements: dict[tuple[int, int], dict] = {}
    for verse in verses:
        key = (chapter, verse)
        artifact_path = human_candidate_path(book, testament, chapter, verse)
        artifact = read_json(artifact_path, {})
        adjudication = artifact.get("adjudication") if isinstance(artifact, dict) else {}
        spanish = " ".join(str(artifact.get("spanish") or "").split())
        if not (
            artifact.get("schema") == "lbf-human-reviewed-candidate-v1"
            and isinstance(adjudication, dict)
            and adjudication.get("humanApprovedInTeamDesk") is True
            and spanish == " ".join(translations.get(key, "").split())
        ):
            raise ValueError(f"{label} {chapter}:{verse} lacks a current human approval.")
        phrase_index = _phrase_index(key, ordered_keys, links)
        replacements[key] = {
            "phraseIndex": phrase_index,
            "reference": f"{label} {chapter}:{verse}",
            "status": "hand",
            "reviewedBy": adjudication.get("reviewedBy") or "",
            "reviewedOn": adjudication.get("reviewedOn") or "",
            "sourceCandidate": artifact_path.name,
            "approvalBindingSha256": object_sha256(artifact.get("approvalBinding") or {}),
            "units": canonical_units(spanish, artifact.get("units") or [], phrase_index),
        }

    retained = [link for link in links if reference_key(link) not in replacements]
    retained.extend(replacements.values())
    retained.sort(key=lambda link: int(link.get("phraseIndex", 0)))
    document.update(
        bookId=book,
        textualBasis=document.get("textualBasis") or ("OSHB/WLC" if testament == "ot" else "TR"),
        schemaVersion=document.get("schemaVersion", 1),
        numbering="protestant",
        links=retained,
    )
    write_json(path, document)
    return path


def demote_chapter_alignment(*, book: str, testament: str, chapter: int) -> None:
    """Preserve links after a revision, but mark the chapter noncanonical-incomplete."""
    path = alignment_path(book, testament)
    document = read_json(path, {})
    changed = False
    for link in document.get("links") or []:
        key = reference_key(link)
        if key and key[0] == chapter:
            link["status"] = "seeded-hand"
            for unit in link.get("units") or []:
                unit["status"] = "seeded"
            changed = True
    if changed:
        write_json(path, document)


def _canonical_links_by_verse(path: Path) -> dict[tuple[int, int], list[dict]]:
    document = read_json(path, {})
    by_verse: dict[tuple[int, int], list[dict]] = {}
    for link in document.get("links") or []:
        key = reference_key(link)
        if key:
            by_verse.setdefault(key, []).append(link)
    return by_verse


def approved_chapter_errors(
    *, book: str, testament: str, chapter: int, translations: dict[tuple[int, int], str]
) -> list[str]:
    verse_keys = [key for key in translations if key[0] == chapter]
    verses = [verse for _, verse in verse_keys]
    review = read_json(chapter_review_path(book, testament, chapter), {})
    errors: list[str] = []
    if not (
        review.get("schema") == "lbf-human-chapter-review-v1"
        and review.get("invalidated") is not True
        and review.get("continuityVoiceFlowConfirmed") is True
        and review.get("verseWordingConfirmed") == verses
        and review.get("alignmentSeedsConfirmed") == verses
    ):
        return [f"chapter {chapter} lacks a current complete human review"]

    links_by_verse = _canonical_links_by_verse(alignment_path(book, testament))
    for key in verse_keys:
        verse = key[1]
        artifact = read_json(human_candidate_path(book, testament, chapter, verse), {})
        adjudication = artifact.get("adjudication") if isinstance(artifact, dict) else {}
        spanish = " ".join(str(artifact.get("spanish") or "").split())
        if not (
            artifact.get("schema") == "lbf-human-reviewed-candidate-v1"
            and isinstance(adjudication, dict)
            and adjudication.get("humanApprovedInTeamDesk") is True
            and spanish == " ".join(translations[key].split())
        ):
            errors.append(f"chapter {chapter}:{verse} human approval is stale")
            continue
        links = links_by_verse.get(key) or []
        if not links or any(str(link.get("status") or "") not in FINISHED_LINK_STATUSES for link in links):
            errors.append(f"chapter {chapter}:{verse} canonical alignment is not human-confirmed")
            continue
        reconstructed = "".join(
            str(unit.get("surface") or "")
            for link in links
            for unit in (link.get("units") or [])
        )
        if normalize_lexical(reconstructed) != normalize_lexical(translations[key]):
            errors.append(f"chapter {chapter}:{verse} canonical alignment does not reconstruct Spanish")
    return errors


def publication_progress(
    *, book: str, testament: str, book_finished: bool, source_commit: str = ""
) -> dict:
    translations = parse_translation(ROOT / "translation" / testament / f"{book}.md")
    chapters = sorted({chapter for chapter, _ in translations})
    chapter_statuses: dict[str, str] = {}
    chapter_errors: dict[str, list[str]] = {}
    for chapter in chapters:
        errors = [] if book_finished else approved_chapter_errors(
            book=book,
            testament=testament,
            chapter=chapter,
            translations=translations,
        )
        chapter_statuses[str(chapter)] = "approved" if not errors else "draft-only"
        if errors:
            chapter_errors[str(chapter)] = errors
    approved = [int(chapter) for chapter, status in chapter_statuses.items() if status == "approved"]
    drafts = [int(chapter) for chapter, status in chapter_statuses.items() if status == "draft-only"]
    return {
        "schema": "lpf-website-progress-v1",
        "technicalBibleId": "LBF",
        "displayName": "LPF",
        "bookId": book,
        "bookStatus": "approved" if book_finished else "unfinished",
        "bookStatusLabel": None if book_finished else "Libro sin terminar",
        "chapterStatuses": chapter_statuses,
        "chapterLabels": {chapter: None if status == "approved" else "Solo borrador" for chapter, status in chapter_statuses.items()},
        "approvedChapters": approved,
        "draftChapters": drafts,
        "approvedChapterCount": len(approved),
        "chapterCount": len(chapters),
        "sourceCommit": source_commit,
        "validationErrors": chapter_errors,
    }
