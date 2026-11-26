#!/usr/bin/env python3
"""Create or replace a production review link stored in Cloudflare D1."""
from __future__ import annotations

import argparse
import hashlib
import json
import secrets
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path
from urllib.parse import urlencode

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "tools" / "pipeline"))

from books import get_book  # noqa: E402


def clean_name(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value).split())


def sql(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def upsert(book: str, reviewer: str, token: str) -> str:
    reviewer_key = reviewer.casefold()
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return (
        "INSERT INTO review_links (book, reviewer, reviewer_key, token_hash, created_on, revoked_on) "
        f"VALUES ({sql(book)}, {sql(reviewer)}, {sql(reviewer_key)}, {sql(token_hash)}, datetime('now'), NULL) "
        "ON CONFLICT(book, reviewer_key) DO UPDATE SET "
        "reviewer=excluded.reviewer, token_hash=excluded.token_hash, created_on=excluded.created_on, revoked_on=NULL;\n"
    )


def execute(statements: str) -> None:
    if not statements:
        return
    with tempfile.NamedTemporaryFile("w", suffix=".sql", encoding="utf-8", delete=False) as handle:
        handle.write(statements)
        sql_path = Path(handle.name)
    try:
        subprocess.run(
            ["npx", "wrangler", "d1", "execute", "lpf-peer-review", "--remote", "--file", str(sql_path)],
            cwd=HERE,
            check=True,
        )
    finally:
        sql_path.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("book", nargs="?", help="libro canónico, por ejemplo romanos")
    parser.add_argument("reviewer", nargs="?", help="nombre completo de la persona")
    parser.add_argument("--base-url", default="https://revision.lapalabrafiel.org/revision-libros")
    parser.add_argument(
        "--import-local",
        action="store_true",
        help="importa sin mostrarlos los enlaces existentes de apps/team/var",
    )
    args = parser.parse_args()
    if args.import_local:
        path = ROOT / "apps" / "team" / "var" / "book-review-links.json"
        values = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
        statements: list[str] = []
        for slug, reviewers in values.items():
            get_book(slug)
            if not isinstance(reviewers, dict):
                continue
            for name, token in reviewers.items():
                reviewer = clean_name(str(name))
                if reviewer and isinstance(token, str) and len(token) >= 24:
                    statements.append(upsert(slug, reviewer, token))
        execute("".join(statements))
        print(f"Enlaces locales importados: {len(statements)}")
        return
    if not args.book or not args.reviewer:
        parser.error("indica el libro y el nombre completo")
    book = get_book(args.book)
    reviewer = clean_name(args.reviewer)
    if not reviewer:
        raise SystemExit("Escribe el nombre completo de la persona.")
    token = secrets.token_urlsafe(32)
    execute(upsert(book.slug, reviewer, token))
    query = urlencode({"book": book.slug, "key": token})
    print(f"{args.base_url}?{query}")


if __name__ == "__main__":
    main()

