#!/usr/bin/env python3
"""Create or display one private review link per Bible book."""
from __future__ import annotations

import argparse
import secrets
import sys
from pathlib import Path
from urllib.parse import urlencode

sys.path.insert(0, str(Path(__file__).resolve().parent))
import desk  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("book", help="canonical book slug, for example romanos")
    parser.add_argument("reviewer", help="reviewer's full name")
    parser.add_argument("--base-url", default="http://127.0.0.1:1435/revision-libros")
    parser.add_argument("--renew", action="store_true", help="replace the current link")
    args = parser.parse_args()
    book = desk.book_or_raise(args.book)
    reviewer = desk.clean_name(args.reviewer)
    links = desk.load_book_review_links()
    reviewers = links.get(book.slug)
    if not isinstance(reviewers, dict):
        reviewers = {}
        links[book.slug] = reviewers
    known = next((name for name in reviewers if name.casefold() == reviewer.casefold()), reviewer)
    if args.renew or not reviewers.get(known):
        reviewers[known] = secrets.token_urlsafe(24)
        desk.secure_private_storage()
        desk.write_json(desk.BOOK_REVIEW_LINKS, links)
    query = urlencode({"book": book.slug, "key": reviewers[known]})
    print(f"{args.base_url}?{query}")


if __name__ == "__main__":
    main()
