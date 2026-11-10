#!/usr/bin/env python3
"""Build the pinned SCV + Robinson + MACULA token-agreement gate."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "pipeline"))

from books import NT  # noqa: E402
from nt_macula import (  # noqa: E402
    MACULA_ATTRIBUTION,
    MACULA_COMMIT,
    MACULA_LICENSE,
    MAPPING_POLICY,
    TR_CODE_BY_STEM,
    load_macula_words,
    lowfat_path,
    map_verse,
    sha256,
    validate_mapping_ledger,
    verify_checkout,
)
from nt_source import load_robinson_book  # noqa: E402

OUT = ROOT / "source" / "greek" / "TR1894"
LEDGER = OUT / "macula-structure-mapping.json"
MANIFEST = OUT / "MACULA_GREEK_MANIFEST.json"


def dump(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    verify_checkout()
    rows = []
    files = []
    exact = hold = mapped_tokens = exact_mapped_tokens = tr_tokens = macula_tokens = 0
    robinson_disagreements = 0
    extra_macula_references = []
    for book in NT:
        path = lowfat_path(book)
        files.append({"path": str(path.relative_to(ROOT)), "sha256": sha256(path)})
        macula = load_macula_words(book)
        source_refs = set(load_robinson_book(book))
        extra_macula_references.extend(sorted(set(macula) - source_refs))
        references = sorted(
            source_refs,
            key=lambda ref: tuple(int(part) for part in ref.split(".")[1:]),
        )
        for reference in references:
            _, chapter, verse = reference.split(".")
            row = map_verse(book, int(chapter), int(verse), macula.get(reference, []))
            rows.append(row)
            tr_tokens += row["trTokenCount"]
            macula_tokens += row["maculaTokenCount"]
            if row["status"] == "exact":
                exact += 1
                exact_mapped_tokens += row["trTokenCount"]
            else:
                hold += 1
            mapped_tokens += row["mappedTrTokenCount"]
            robinson_disagreements += len(row["nonAgreeingRobinsonTokenIds"])
    ledger = {
        "schema": "tr1894-macula-structure-mapping-v2",
        "policy": MAPPING_POLICY,
        "summary": {
            "verses": len(rows),
            "exactVerses": exact,
            "holdVerses": hold,
            "trTokens": tr_tokens,
            "maculaTokens": macula_tokens,
            "mappedTrTokens": mapped_tokens,
            "tripleAgreementTokens": mapped_tokens,
            "exactMappedTrTokens": exact_mapped_tokens,
            "nonAgreeingRobinsonTokens": robinson_disagreements,
            "extraMaculaReferences": extra_macula_references,
        },
        "verses": rows,
    }
    validate_mapping_ledger(ledger)
    dump(LEDGER, ledger)
    manifest = {
        "schema": "macula-greek-structure-manifest-v1",
        "dataset": "Clear-Bible/macula-greek Nestle1904 lowfat",
        "revision": MACULA_COMMIT,
        "license": MACULA_LICENSE,
        "attribution": MACULA_ATTRIBUTION,
        "allowlist": {
            "groups": ["class", "rule", "role", "type", "predication", "head"],
            "terminalsForTransientMappingOnly": ["ref", "xml:id", "surface"],
        },
        "files": files,
        "mapping": {
            "path": str(LEDGER.relative_to(ROOT)),
            "sha256": sha256(LEDGER),
            "policy": MAPPING_POLICY,
            **ledger["summary"],
        },
        "generator": {
            "command": "python3 tools/build_nt_macula_mapping.py",
            "path": "tools/build_nt_macula_mapping.py",
            "sha256": sha256(Path(__file__)),
        },
    }
    dump(MANIFEST, manifest)
    print(
        f"MACULA Greek gate: {len(rows)} verses; {exact} exact; {hold} HOLD; "
        f"{mapped_tokens}/{tr_tokens} triple-agreement token anchors; "
        f"{exact_mapped_tokens} in exact verses; "
        f"{robinson_disagreements} SCV/Robinson token disagreements excluded"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

