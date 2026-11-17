#!/usr/bin/env python3
"""Verify a controlled lexical candidate set against pinned DDbDP/HGV XML.

The input cache is research evidence only. It is intentionally outside the
canonical packet loader and fails closed unless its aggregate hashes match the
recorded evaluation manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = (
    ROOT
    / "source"
    / "greek"
    / "documentary-koine"
    / "DDbDP_QUERY_MANIFEST.json"
)
TEI = "{http://www.tei-c.org/ns/1.0}"
GREEK_WORD = re.compile(r"[\u0370-\u03ff\u1f00-\u1fff\u0300-\u036f]+")
NO_BREAK_LB = re.compile(r'\s*<lb\b(?=[^>]*\bbreak="no")[^>]*/>\s*')


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def aggregate_xml(root: Path, subdirectory: str) -> tuple[int, str]:
    rows = []
    for path in sorted((root / subdirectory).rglob("*.xml")):
        rows.append((path.relative_to(root).as_posix(), sha256(path)))
    digest = hashlib.sha256()
    for relative, file_hash in rows:
        digest.update(f"{relative}\0{file_hash}\n".encode("utf-8"))
    return len(rows), digest.hexdigest()


def load_manifest(path: Path) -> dict:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "lpf-ddbdp-primary-query-manifest-v1":
        raise ValueError("unexpected DDbDP query manifest schema")
    if manifest.get("status") != "authorized-human-lexical-research-only":
        raise ValueError("unexpected DDbDP authorization scope")
    return manifest


def validate_cache(cache_root: Path, manifest: dict) -> None:
    expected = manifest["localEvaluationCache"]
    for key, subdirectory in (
        ("ddbdp", "DDbDP"),
        ("hgvMetadata", "HGV_meta_EpiDoc"),
    ):
        count, digest = aggregate_xml(cache_root, subdirectory)
        row = expected[key]
        if count != row["xmlCount"] or digest != row["aggregateSha256"]:
            raise ValueError(
                f"{subdirectory} cache mismatch: count={count}, sha256={digest}"
            )


def canonical_chunks(element: ET.Element, flags: frozenset[str] = frozenset()):
    name = local_name(element.tag)
    local_flags = set(flags)
    if name == "supplied":
        local_flags.add("supplied")
    elif name == "unclear":
        local_flags.add("unclear")

    if name == "choice":
        preferred = next(
            (
                child
                for preferred_name in ("reg", "corr")
                for child in element
                if local_name(child.tag) == preferred_name
            ),
            None,
        )
        if preferred is not None:
            yield from canonical_chunks(preferred, flags)
            return
    elif name == "app":
        preferred = next(
            (child for child in element if local_name(child.tag) == "lem"),
            None,
        )
        if preferred is not None:
            yield from canonical_chunks(preferred, flags)
            return

    frozen = frozenset(local_flags)
    if element.text:
        yield element.text, frozen
    for child in element:
        yield from canonical_chunks(child, frozen)
        if child.tail:
            yield child.tail, frozen


def canonical_edition(path: Path) -> tuple[str, list[frozenset[str]], ET.Element]:
    raw = path.read_text(encoding="utf-8")
    raw = NO_BREAK_LB.sub("", raw)
    root = ET.fromstring(raw)
    edition = root.find(f'.//{TEI}div[@type="edition"]')
    if edition is None:
        return "", [], root
    characters: list[str] = []
    flags: list[frozenset[str]] = []
    for text, chunk_flags in canonical_chunks(edition):
        characters.extend(text)
        flags.extend([chunk_flags] * len(text))
    return "".join(characters), flags, root


def normalized_greek(value: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFD", value).lower()
        if unicodedata.category(character) != "Mn"
    )


def exact_greek(value: str) -> str:
    """Preserve diacritics that distinguish lexical forms such as ᾅδην/ἄδην."""
    return unicodedata.normalize("NFC", value.casefold())


def year_from_iso(value: str | None) -> int | None:
    if not value:
        return None
    match = re.match(r"(-?\d{4})", value)
    return int(match.group(1)) if match else None


def date_record(element: ET.Element) -> dict:
    when = year_from_iso(element.get("when"))
    not_before = year_from_iso(element.get("notBefore"))
    not_after = year_from_iso(element.get("notAfter"))
    if when is not None:
        not_before = not_after = when
    return {
        "label": " ".join("".join(element.itertext()).split()),
        "notBeforeYear": not_before,
        "notAfterYear": not_after,
        "precision": element.get("precision"),
        "certainty": element.get("cert"),
    }


def classify_dates(dates: list[dict]) -> str:
    if not dates:
        return "undated"
    if any(
        row["notBeforeYear"] is None or row["notAfterYear"] is None
        for row in dates
    ):
        if all(
            (row["notBeforeYear"] is not None and row["notBeforeYear"] > 200)
            or (row["notAfterYear"] is not None and row["notAfterYear"] < -100)
            for row in dates
        ):
            return "diachronic-comparison"
        if any(
            (row["notBeforeYear"] is None or row["notBeforeYear"] <= 100)
            and (row["notAfterYear"] is None or row["notAfterYear"] >= 1)
            for row in dates
        ):
            return "indeterminate-open-range-may-overlap-first-century-ce"
        return "indeterminate-open-range"

    if all(
        row["notBeforeYear"] >= 1 and row["notAfterYear"] <= 100
        for row in dates
    ):
        return "exact-first-century-ce"
    if any(
        row["notBeforeYear"] <= 100 and row["notAfterYear"] >= 1
        for row in dates
    ):
        return "overlaps-first-century-ce"
    if any(
        row["notBeforeYear"] <= 200 and row["notAfterYear"] >= -100
        for row in dates
    ):
        return "near-contemporary-100-bce-to-200-ce"
    return "diachronic-comparison"


def metadata_path(cache_root: Path, hgv_id: str) -> Path:
    numeric = int(re.match(r"\d+", hgv_id).group())
    group = (numeric - 1) // 1000 + 1
    return cache_root / "HGV_meta_EpiDoc" / f"HGV{group}" / f"{hgv_id}.xml"


def metadata(cache_root: Path, hgv_ids: list[str]) -> dict:
    dates = []
    places = []
    keywords = []
    missing = []
    for hgv_id in hgv_ids:
        path = metadata_path(cache_root, hgv_id)
        if not path.is_file():
            missing.append(hgv_id)
            continue
        root = ET.parse(path).getroot()
        dates.extend(date_record(row) for row in root.findall(f".//{TEI}origDate"))
        places.extend(
            " ".join("".join(row.itertext()).split())
            for row in root.findall(f".//{TEI}origPlace")
        )
        keywords.extend(
            " ".join("".join(row.itertext()).split())
            for row in root.findall(f'.//{TEI}keywords[@scheme="hgv"]/{TEI}term')
        )
    return {
        "dates": dates,
        "dateBand": classify_dates(dates),
        "originPlaces": sorted(set(filter(None, places))),
        "hgvKeywords": sorted(set(filter(None, keywords))),
        "missingHgvMetadata": missing,
    }


def context_window(text: str, start: int, end: int, radius: int = 90) -> str:
    return " ".join(text[max(0, start - radius) : min(len(text), end + radius)].split())


def collect_occurrences(
    cache_root: Path,
    stems: tuple[str, ...],
    exact_surfaces: frozenset[str] = frozenset(),
    normalized_forms: frozenset[str] = frozenset(),
) -> list[dict]:
    occurrences = []
    for path in sorted((cache_root / "DDbDP").rglob("*.xml")):
        text, character_flags, root = canonical_edition(path)
        if not text:
            continue
        hgv_ids = []
        for element in root.findall(f'.//{TEI}idno[@type="HGV"]'):
            hgv_ids.extend((element.text or "").split())
        title = root.findtext(f".//{TEI}title")
        matches = []
        for match in GREEK_WORD.finditer(text):
            normalized = normalized_greek(match.group())
            if (
                not normalized.startswith(stems)
                and exact_greek(match.group()) not in exact_surfaces
                and normalized not in normalized_forms
            ):
                continue
            matches.append((match, normalized))
        if not matches:
            continue
        document_metadata = metadata(cache_root, hgv_ids)
        for match, normalized in matches:
            flags = sorted(
                set().union(*character_flags[match.start() : match.end()])
            )
            occurrences.append(
                {
                    "primaryVerificationStatus": "verified-in-pinned-xml",
                    "document": title,
                    "ddbdpPath": path.relative_to(cache_root).as_posix(),
                    "hgvIds": hgv_ids,
                    "surface": match.group(),
                    "normalizedSurface": normalized,
                    "editorialFlags": flags,
                    "context": context_window(text, match.start(), match.end()),
                    **document_metadata,
                }
            )
    return occurrences


def validate_pinned_checkout(repository_root: Path, manifest: dict) -> None:
    expected = manifest["upstream"]["commit"]
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )
    actual = completed.stdout.strip()
    if actual != expected:
        raise ValueError(f"DDbDP checkout commit mismatch: {actual}")
    if not (repository_root / "DDbDP").is_dir():
        raise ValueError("DDbDP directory missing from pinned checkout")
    if not (repository_root / "HGV_meta_EpiDoc").is_dir():
        raise ValueError("HGV metadata directory missing from pinned checkout")
    if subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip():
        raise ValueError("DDbDP checkout contains modified tracked files")
    for key, subdirectory in (
        ("ddbdp", "DDbDP"),
        ("hgvMetadata", "HGV_meta_EpiDoc"),
    ):
        tree = subprocess.run(
            ["git", "rev-parse", f"HEAD:{subdirectory}"],
            cwd=repository_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        expected_tree = manifest["fullConcordance"][key]["gitTreeSha1"]
        if tree != expected_tree:
            raise ValueError(f"{subdirectory} tree mismatch: {tree}")


def build_inventory(cache_root: Path, manifest_path: Path) -> dict:
    manifest = load_manifest(manifest_path)
    validate_cache(cache_root, manifest)
    stems = tuple(manifest["targetNormalizedPrefixes"])
    exact_surfaces = frozenset(
        exact_greek(value) for value in manifest.get("targetExactForms") or []
    )
    normalized_forms = frozenset(
        normalized_greek(value) for value in manifest.get("targetNormalizedForms") or []
    )
    occurrences = collect_occurrences(cache_root, stems, exact_surfaces, normalized_forms)
    counts = Counter(row["dateBand"] for row in occurrences)
    return {
        "schema": "lpf-ddbdp-primary-lexical-inventory-v1",
        "authority": "authorized-human-lexical-research-only",
        "completeness": "controlled-candidate-set-not-full-corpus-concordance",
        "sourceManifest": str(manifest_path.resolve().relative_to(ROOT)),
        "upstreamCommit": manifest["upstream"]["commit"],
        "targetNormalizedPrefixes": list(stems),
        "targetExactForms": sorted(exact_surfaces),
        "targetNormalizedForms": sorted(normalized_forms),
        "occurrenceCount": len(occurrences),
        "countsByDateBand": dict(sorted(counts.items())),
        "occurrences": occurrences,
    }


def build_full_concordance(repository_root: Path, manifest_path: Path) -> dict:
    manifest = load_manifest(manifest_path)
    validate_pinned_checkout(repository_root, manifest)
    stems = tuple(manifest["targetNormalizedPrefixes"])
    exact_surfaces = frozenset(
        exact_greek(value) for value in manifest.get("targetExactForms") or []
    )
    normalized_forms = frozenset(
        normalized_greek(value) for value in manifest.get("targetNormalizedForms") or []
    )
    occurrences = collect_occurrences(
        repository_root, stems, exact_surfaces, normalized_forms
    )
    counts = Counter(row["dateBand"] for row in occurrences)
    return {
        "schema": "lpf-ddbdp-primary-lexical-inventory-v1",
        "authority": "authorized-human-lexical-research-only",
        "completeness": "full-pinned-DDbDP-normalized-concordance",
        "sourceManifest": str(manifest_path.resolve().relative_to(ROOT)),
        "upstreamCommit": manifest["upstream"]["commit"],
        "ddbdpXmlCount": sum(1 for _ in (repository_root / "DDbDP").rglob("*.xml")),
        "targetNormalizedPrefixes": list(stems),
        "targetExactForms": sorted(exact_surfaces),
        "targetNormalizedForms": sorted(normalized_forms),
        "occurrenceCount": len(occurrences),
        "countsByDateBand": dict(sorted(counts.items())),
        "occurrences": occurrences,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    roots = parser.add_mutually_exclusive_group(required=True)
    roots.add_argument("--cache-root", type=Path)
    roots.add_argument("--repository-root", type=Path)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.repository_root:
        payload = build_full_concordance(args.repository_root, args.manifest)
    else:
        payload = build_inventory(args.cache_root, args.manifest)
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
