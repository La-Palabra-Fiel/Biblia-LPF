#!/usr/bin/env python3
"""Inventory lexical candidates in a pinned duke-nlp papyrus snapshot.

This is a research tool, not a canonical source-packet loader. Automatic
lemmas discover candidates only. Every hit must later be verified against the
pinned primary Papyri.info DDbDP transcription.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = (
    ROOT
    / "source"
    / "greek"
    / "documentary-koine"
    / "DUKE_NLP_MANIFEST.json"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(path: Path) -> dict:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "lpf-documentary-koine-discovery-manifest-v1":
        raise ValueError("unexpected documentary Koine manifest schema")
    if manifest.get("status") != "research-only-not-authorized-for-source-packets":
        raise ValueError("discovery corpus must remain research-only")
    return manifest


def validate_corpus(corpus_root: Path, manifest: dict) -> list[Path]:
    expected = {row["path"]: row["sha256"] for row in manifest.get("files") or []}
    if not expected:
        raise ValueError("manifest contains no discovery files")
    paths = []
    for relative, expected_hash in sorted(expected.items()):
        path = corpus_root / relative
        if not path.is_file():
            raise ValueError(f"discovery corpus file missing: {relative}")
        actual = sha256(path)
        if actual != expected_hash:
            raise ValueError(
                f"discovery corpus checksum mismatch: {relative}: {actual}"
            )
        paths.append(path)
    return paths


def classify_date(period_min: int, period_max: int) -> str:
    if not period_min or not period_max:
        return "undated"
    if period_min > period_max:
        raise ValueError(f"invalid documentary period: {period_min}..{period_max}")
    if period_min == 1 and period_max == 1:
        return "exact-first-century-ce"
    if period_min <= 1 <= period_max:
        return "overlaps-first-century-ce"
    if period_max >= -1 and period_min <= 2:
        return "near-contemporary-100-bce-to-200-ce"
    return "diachronic-comparison"


def sentence_text(sentence: ET.Element) -> str:
    return " ".join(
        word.get("regularized") or ""
        for word in sentence.findall("word")
        if not word.get("artificial") and (word.get("regularized") or "")
    )


def collect_occurrences(paths: list[Path], lemmas: set[str]) -> list[dict]:
    occurrences = []
    for path in paths:
        for _, sentence in ET.iterparse(path, events=("end",)):
            if sentence.tag != "sentence":
                continue
            words = sentence.findall("word")
            hits = [word for word in words if word.get("lemma") in lemmas]
            if hits:
                period_min = int(sentence.get("period_min") or 0)
                period_max = int(sentence.get("period_max") or 0)
                context = sentence_text(sentence)
                for word in hits:
                    occurrences.append(
                        {
                            "discoveryStatus": "automatic-lemma-candidate",
                            "primaryVerificationStatus": "pending",
                            "lemma": word.get("lemma"),
                            "regularized": word.get("regularized"),
                            "form": word.get("form"),
                            "completeness": word.get("completeness"),
                            "postag": word.get("postag"),
                            "wordId": word.get("wordid"),
                            "row": word.get("row"),
                            "documentId": sentence.get("document_id"),
                            "filename": sentence.get("filename"),
                            "periodMin": period_min,
                            "periodMax": period_max,
                            "dateBand": classify_date(period_min, period_max),
                            "genre": sentence.get("genre"),
                            "place": sentence.get("place"),
                            "regularizedSentence": context,
                            "discoveryFile": path.name,
                        }
                    )
            sentence.clear()
    return occurrences


def build_inventory(corpus_root: Path, manifest_path: Path, lemmas: set[str]) -> dict:
    manifest = load_manifest(manifest_path)
    paths = validate_corpus(corpus_root, manifest)
    occurrences = collect_occurrences(paths, lemmas)
    bands = Counter(row["dateBand"] for row in occurrences)
    return {
        "schema": "lpf-documentary-koine-lexical-inventory-v1",
        "authority": "discovery-only-primary-verification-required",
        "sourceManifest": str(manifest_path.relative_to(ROOT)),
        "upstreamCommit": manifest["upstream"]["commit"],
        "lemmas": sorted(lemmas),
        "occurrenceCount": len(occurrences),
        "countsByDateBand": dict(sorted(bands.items())),
        "occurrences": occurrences,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--corpus-root",
        required=True,
        type=Path,
        help="Extracted duke-nlp repository root containing xml/",
    )
    parser.add_argument(
        "--manifest", type=Path, default=DEFAULT_MANIFEST
    )
    parser.add_argument(
        "--lemma", action="append", required=True, dest="lemmas"
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    payload = build_inventory(args.corpus_root, args.manifest, set(args.lemmas))
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

