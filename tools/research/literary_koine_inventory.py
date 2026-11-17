#!/usr/bin/env python3
"""Build a reviewable lexical concordance from pinned Greek literary TEI.

This tool reads only allowlisted Greek edition XML. It deliberately ignores
translations, notes, apparatus readings and automatic linguistic annotation.
It finds surface forms by normalized prefix; it does not assign lemmas or
meanings.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = (
    REPO_ROOT / "source/greek/literary-koine/LITERARY_KOINE_MANIFEST.json"
)
TEI = "{http://www.tei-c.org/ns/1.0}"
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
GREEK_WORD = re.compile(r"[\u0300-\u036f\u0370-\u03ff\u1f00-\u1fff]+")
SKIP_TAGS = {"note", "app", "rdg", "del", "fw", "teiHeader"}
CHOICE_PREFERENCE = ("corr", "reg", "expan", "orig", "sic", "abbr")


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def normalize_greek(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.casefold())
    plain = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return plain.replace("ς", "σ")


def exact_greek(value: str) -> str:
    """Preserve diacritics that distinguish lexical forms such as ᾅδην/ἄδην."""
    return unicodedata.normalize("NFC", value.casefold())


def compact(value: str) -> str:
    return " ".join(value.split())


def source_text(element: ET.Element) -> str:
    """Extract edited Greek text while excluding apparatus and translations."""
    name = local_name(element.tag)
    if name in SKIP_TAGS:
        return ""
    if name == "choice":
        children = list(element)
        for preferred in CHOICE_PREFERENCE:
            chosen = next((x for x in children if local_name(x.tag) == preferred), None)
            if chosen is not None:
                return source_text(chosen)
    parts = [element.text or ""]
    for child in element:
        parts.append(source_text(child))
        parts.append(child.tail or "")
    return "".join(parts)


def run_git(checkout: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(checkout), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return proc.stdout.strip()


def file_set_hash(checkout: Path, paths: list[Path]) -> str:
    lines = []
    for path in paths:
        relative = path.relative_to(checkout).as_posix()
        blob = run_git(checkout, "rev-parse", f"HEAD:{relative}")
        lines.append(f"{blob}  {relative}\n")
    return hashlib.sha256("".join(lines).encode()).hexdigest()


def verify_source(checkout: Path, source: dict) -> list[Path]:
    actual_commit = run_git(checkout, "rev-parse", "HEAD")
    if actual_commit != source["commit"]:
        raise ValueError(f"{source['id']} commit mismatch: {actual_commit}")
    actual_tree = run_git(checkout, "rev-parse", f"HEAD:{source['root']}")
    if actual_tree != source["tree"]:
        raise ValueError(f"{source['id']} tree mismatch: {actual_tree}")
    if run_git(checkout, "status", "--porcelain"):
        raise ValueError(f"{source['id']} checkout contains local changes")

    root = checkout / source["root"]
    paths = sorted(root.glob(source["greekGlob"]))
    if source.get("oneEditionPerWork"):
        by_work: dict[Path, list[Path]] = {}
        for path in paths:
            by_work.setdefault(path.parent, []).append(path)
        # CTS work directories may contain parallel Greek editions. Select the
        # first edition identifier deterministically so a work is not counted
        # twice; the exact resulting file set is pinned by hash.
        paths = [sorted(candidates)[0] for _, candidates in sorted(by_work.items())]
    if len(paths) != source["expectedGreekFileCount"]:
        raise ValueError(f"{source['id']} Greek file count mismatch: {len(paths)}")
    for path in paths:
        lower = path.as_posix().lower()
        if any(marker.lower() in lower for marker in source["excludedPathMarkers"]):
            raise ValueError(f"excluded translation path selected: {path}")
        if "grc" not in path.name.lower():
            raise ValueError(f"non-Greek edition path selected: {path}")
    actual_hash = file_set_hash(checkout, paths)
    if actual_hash != source["greekFileSetSha256"]:
        raise ValueError(f"{source['id']} Greek file set mismatch: {actual_hash}")
    return paths


def title_for(root: ET.Element) -> str:
    titles = root.findall(f"./{TEI}teiHeader/{TEI}fileDesc/{TEI}titleStmt/{TEI}title")
    for language in ("grc", "lat"):
        for title in titles:
            if title.get(XML_LANG) == language:
                return compact("".join(title.itertext()))
    return compact("".join(titles[0].itertext())) if titles else ""


def edition_urn(root: ET.Element) -> str:
    for div in root.findall(f".//{TEI}div"):
        if div.get("type") == "edition":
            return div.get("n") or div.get("{http://www.w3.org/XML/1998/namespace}base", "")
    return ""


def passage_reference(section: ET.Element, parent_map: dict[ET.Element, ET.Element]) -> str:
    components = []
    node: ET.Element | None = section
    while node is not None:
        if local_name(node.tag) == "div" and node.get("type") == "textpart":
            number = node.get("n")
            if number:
                components.append(number)
        node = parent_map.get(node)
    return ".".join(reversed(components))


def immediate_context(text: str, start: int, end: int) -> str:
    boundaries = ".;·;·?!\n"
    left = max((text.rfind(mark, 0, start) for mark in boundaries), default=-1)
    rights = [text.find(mark, end) for mark in boundaries]
    rights = [position for position in rights if position >= 0]
    right = min(rights) + 1 if rights else len(text)
    context = compact(text[left + 1 : right])
    if len(context) <= 700:
        return context
    window_start = max(0, start - 280)
    window_end = min(len(text), end + 280)
    return compact(text[window_start:window_end])


def scan_file(
    path: Path,
    checkout: Path,
    prefixes: list[str],
    source_id: str,
    exact_forms: set[str] | None = None,
    exact_surfaces: set[str] | None = None,
) -> list[dict]:
    root = ET.parse(path).getroot()
    if not any(
        node.get(XML_LANG) == "grc"
        for node in root.findall(f".//{TEI}div")
        if node.get("type") == "edition"
    ) and root.find(f"./{TEI}text").get(XML_LANG, "grc") != "grc":
        raise ValueError(f"edition does not declare Greek: {path}")
    parent_map = {child: parent for parent in root.iter() for child in parent}
    title = title_for(root)
    urn = edition_urn(root)
    relative = path.relative_to(checkout).as_posix()
    hits = []
    textparts = [
        div
        for div in root.findall(f".//{TEI}div")
        if div.get("type") == "textpart"
    ]
    passages = [
        div
        for div in textparts
        if not any(
            child.get("type") == "textpart"
            for child in div.findall(f".//{TEI}div")
        )
    ]
    for passage in passages:
        text = compact(source_text(passage))
        for match in GREEK_WORD.finditer(text):
            normalized = normalize_greek(match.group())
            matched_prefix = (
                normalized if exact_greek(match.group()) in (exact_surfaces or set())
                else normalized if normalized in (exact_forms or set())
                else next((p for p in prefixes if normalized.startswith(p)), None)
            )
            if not matched_prefix:
                continue
            hits.append(
                {
                    "source": source_id,
                    "work": title,
                    "editionUrn": urn,
                    "passage": passage_reference(passage, parent_map),
                    "path": relative,
                    "surface": match.group(),
                    "normalizedSurface": normalized,
                    "matchedNormalizedPrefix": matched_prefix,
                    "immediateContext": immediate_context(text, match.start(), match.end()),
                }
            )
    return hits


def build_inventory(manifest: dict, source: dict, checkout: Path, family: dict) -> dict:
    paths = verify_source(checkout, source)
    prefixes = [normalize_greek(value) for value in family["normalizedPrefixes"]]
    exact_forms = {
        normalize_greek(value) for value in family.get("normalizedExactForms") or []
    }
    exact_surfaces = {
        exact_greek(value) for value in family.get("exactForms") or []
    }
    exact_surface_queries = sorted({normalize_greek(value) for value in exact_surfaces})
    queries = prefixes + sorted(exact_forms) + exact_surface_queries
    occurrences = []
    for path in paths:
        occurrences.extend(
            scan_file(
                path, checkout, prefixes, source["id"], exact_forms,
                exact_surfaces,
            )
        )
    prefix_counts = {
        prefix: sum(hit["matchedNormalizedPrefix"] == prefix for hit in occurrences)
        for prefix in queries
    }
    return {
        "schema": "lpf-literary-koine-inventory-v1",
        "sourceManifest": "source/greek/literary-koine/LITERARY_KOINE_MANIFEST.json",
        "authorizationScope": manifest["authorizationScope"],
        "modelExposed": False,
        "semanticJudgment": "none-surface-concordance-only",
        "source": {
            key: source[key]
            for key in (
                "id", "author", "register", "repository", "commit", "tree",
                "root", "expectedGreekFileCount", "greekFileSetSha256", "license"
            )
        },
        "query": family,
        "summary": {
            "occurrenceCount": len(occurrences),
            "workCountWithOccurrences": len({hit["editionUrn"] for hit in occurrences}),
            "countsByNormalizedPrefix": prefix_counts,
        },
        "occurrences": occurrences,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--source", required=True)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--family", default="metano-family")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if manifest.get("schema") != "lpf-literary-koine-manifest-v1":
        raise ValueError("unexpected literary Koine manifest schema")
    source = next(item for item in manifest["sources"] if item["id"] == args.source)
    family = next(item for item in manifest["targetFamilies"] if item["id"] == args.family)
    inventory = build_inventory(manifest, source, args.checkout, family)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(inventory["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
