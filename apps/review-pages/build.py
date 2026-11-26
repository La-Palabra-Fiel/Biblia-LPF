#!/usr/bin/env python3
"""Build the read-only book payloads and Cloudflare Pages application."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DIST = HERE / "dist"
sys.path.insert(0, str(ROOT / "tools" / "pipeline"))

from books import BOOKS  # noqa: E402

HEADING = re.compile(r"^###\s+(\d+):(\d+)\s*$")
CHAPTER = re.compile(r"^##\s+Cap[ií]tulo\s+(\d+)\s*$", re.IGNORECASE)
STATUS_COLUMNS = (
    "book", "testament", "translation", "alignment", "translation_by",
    "translation_on", "alignment_by", "alignment_on", "notes",
)


def translation_statuses() -> dict[str, str]:
    result: dict[str, str] = {}
    for line in (ROOT / "STATUS.md").read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == len(STATUS_COLUMNS) and cells[0] in BOOKS:
            result[cells[0]] = cells[2]
    return result


def readable_chapters(text: str) -> list[dict]:
    chapters: list[dict] = []
    current: dict | None = None
    for line in text.splitlines():
        chapter_match = CHAPTER.match(line.strip())
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
        verse = current["verses"][-1]
        verse["text"] = " ".join(part for part in (verse["text"], line.strip()) if part)
    return [chapter for chapter in chapters if chapter["verses"]]


def main() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    (DIST / "books").mkdir(parents=True)
    (DIST / "revision-libros").mkdir()
    shutil.copy2(HERE / "public" / "revision-libros.html", DIST / "revision-libros" / "index.html")
    shutil.copy2(HERE / "src" / "_worker.js", DIST / "_worker.js")
    (DIST / "_redirects").write_text("/ /revision-libros 302\n", encoding="utf-8")
    (DIST / "_headers").write_text(
        "/*\n"
        "  X-Content-Type-Options: nosniff\n"
        "  Referrer-Policy: no-referrer\n"
        "  Permissions-Policy: camera=(), microphone=(), geolocation=()\n"
        "  Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'\n",
        encoding="utf-8",
    )

    statuses = translation_statuses()
    manifest: list[dict] = []
    for slug, book in BOOKS.items():
        path = ROOT / "translation" / book.testament / f"{slug}.md"
        if not path.is_file():
            continue
        raw = path.read_bytes()
        chapters = readable_chapters(raw.decode("utf-8"))
        if not chapters:
            continue
        fingerprint = hashlib.sha256(raw).hexdigest()
        payload = {
            "book": slug,
            "label": book.label,
            "status": statuses.get(slug, "none"),
            "translationSha256": fingerprint,
            "chapters": chapters,
        }
        (DIST / "books" / f"{slug}.json").write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        manifest.append({"book": slug, "translationSha256": fingerprint})
    (DIST / "build-manifest.json").write_text(
        json.dumps({"schema": "lpf-review-pages-build-v1", "books": manifest}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Built {len(manifest)} readable books in {DIST}")


if __name__ == "__main__":
    main()

