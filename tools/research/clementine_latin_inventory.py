#!/usr/bin/env python3
"""Build a surface concordance from the pinned Clementine Latin text."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import unicodedata
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = (
    REPO_ROOT / "source/latin/clementine-vulgate/CLEMENTINE_MANIFEST.json"
)
LATIN_WORD = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿÆæŒœ]+")
VERSE_LINE = re.compile(r"^(?P<reference>\d+:\d+)\s+(?P<text>.*)$")


def run_git(checkout: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(checkout), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return proc.stdout.strip()


def normalize_latin(value: str) -> str:
    value = value.casefold().replace("œ", "oe").replace("æ", "ae")
    decomposed = unicodedata.normalize("NFD", value)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def file_set_hash(checkout: Path, paths: list[Path]) -> str:
    lines = []
    for path in paths:
        relative = path.relative_to(checkout).as_posix()
        blob = run_git(checkout, "rev-parse", f"HEAD:{relative}")
        lines.append(f"{blob}  {relative}\n")
    return hashlib.sha256("".join(lines).encode()).hexdigest()


def verify_source(checkout: Path, source: dict) -> list[Path]:
    if run_git(checkout, "rev-parse", "HEAD") != source["commit"]:
        raise ValueError("Clementine commit mismatch")
    if run_git(checkout, "rev-parse", "HEAD^{tree}") != source["tree"]:
        raise ValueError("Clementine tree mismatch")
    if run_git(checkout, "status", "--porcelain"):
        raise ValueError("Clementine checkout contains local changes")
    paths = sorted(checkout.glob(source["latinGlob"]))
    if len(paths) != source["expectedLatinFileCount"]:
        raise ValueError(f"Clementine Latin file count mismatch: {len(paths)}")
    actual_hash = file_set_hash(checkout, paths)
    if actual_hash != source["latinFileSetSha256"]:
        raise ValueError(f"Clementine Latin file set mismatch: {actual_hash}")
    return paths


def scan_file(
    path: Path,
    checkout: Path,
    prefixes: list[str],
    exact_forms: set[str],
    encoding: str,
) -> list[dict]:
    hits = []
    for line_number, raw_line in enumerate(path.read_text(encoding=encoding).splitlines(), 1):
        line = raw_line.removesuffix("\\").strip()
        parsed = VERSE_LINE.match(line)
        if not parsed:
            raise ValueError(f"unexpected Clementine line at {path.name}:{line_number}")
        text = parsed.group("text")
        for match in LATIN_WORD.finditer(text):
            normalized = normalize_latin(match.group())
            prefix = next((item for item in prefixes if normalized.startswith(item)), None)
            matched_query = prefix or (normalized if normalized in exact_forms else None)
            if matched_query is None:
                continue
            hits.append({
                "bookFile": path.relative_to(checkout).as_posix(),
                "reference": parsed.group("reference"),
                "lineNumber": line_number,
                "surface": match.group(),
                "normalizedSurface": normalized,
                "matchedNormalizedPrefix": matched_query,
                "immediateContext": text,
            })
    return hits


def build_inventory(
    manifest: dict,
    checkout: Path,
    manifest_path: Path = DEFAULT_MANIFEST,
) -> dict:
    source = manifest["source"]
    paths = verify_source(checkout, source)
    families = manifest["targetFamilies"]
    prefixes = [
        normalize_latin(prefix)
        for family in families
        for prefix in family.get("normalizedPrefixes") or []
    ]
    exact_forms = {
        normalize_latin(form)
        for family in families
        for form in family.get("normalizedExactForms") or []
    }
    queries = prefixes + sorted(exact_forms)
    occurrences = []
    for path in paths:
        occurrences.extend(
            scan_file(path, checkout, prefixes, exact_forms, source["encoding"])
        )
    return {
        "schema": "lpf-clementine-latin-inventory-v1",
        "sourceManifest": str(manifest_path.resolve().relative_to(REPO_ROOT)),
        "authorizationScope": manifest["authorizationScope"],
        "modelExposed": False,
        "semanticJudgment": "none-surface-concordance-only",
        "source": source,
        "query": families,
        "summary": {
            "occurrenceCount": len(occurrences),
            "verseCountWithOccurrences": len({
                (hit["bookFile"], hit["reference"]) for hit in occurrences
            }),
            "countsByNormalizedPrefix": {
                prefix: sum(
                    hit["matchedNormalizedPrefix"] == prefix for hit in occurrences
                )
                for prefix in queries
            },
        },
        "occurrences": occurrences,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if manifest.get("schema") != "lpf-clementine-latin-manifest-v1":
        raise ValueError("unexpected Clementine manifest schema")
    inventory = build_inventory(manifest, args.checkout, args.manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(inventory["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

