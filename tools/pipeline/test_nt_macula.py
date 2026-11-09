"""Tests for the closed MACULA Greek structure mapping gate."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from books import get_book
from nt_macula import (
    assert_allowed_projection,
    load_macula_words,
    map_verse,
    project_chapter_candidate,
    robinson_token_key,
    validate_candidate,
    validate_mapping_ledger,
)


class NtMaculaTests(unittest.TestCase):
    def test_philippians_1_1_holds_on_christ_jesus_order(self) -> None:
        book = get_book("filipenses")
        row = map_verse(book, 1, 1, load_macula_words(book)["PHP.1.1"])
        self.assertEqual(row["status"], "hold-token-disagreement")
        self.assertEqual(row["trSurfaceBeta"][4:6], ["ihsou", "cristou"])
        self.assertEqual(row["maculaSurface"][4:6], ["Χριστοῦ", "Ἰησοῦ"])
        self.assertGreaterEqual(row["mappedTrTokenCount"], 18)
        self.assertIn("PHP.1.1.w005", row["unmatchedTrTokenIds"])

    def test_macula_mapping_requires_three_source_token_agreement(self) -> None:
        book = get_book("mateo")
        row = map_verse(book, 2, 23, load_macula_words(book)["MAT.2.23"])
        self.assertEqual(row["status"], "hold-token-disagreement")
        self.assertIn("MAT.2.23.w007", row["nonAgreeingRobinsonTokenIds"])
        self.assertNotIn(
            "MAT.2.23.w007",
            {item["trTokenId"] for item in row["mapping"]},
        )
        self.assertTrue(all(
            item["basis"] == "scv-robinson-macula-normalized-surface-order"
            for item in row["mapping"]
        ))

    def test_robinson_merge_cannot_anchor_macula_structure(self) -> None:
        token = {
            "surfaceBeta": "kan",
            "morphology": {
                "sourceOrdinals": [1, 2],
                "sourceSurfaceBeta": "kai+an",
            },
        }
        self.assertIsNone(robinson_token_key(token))

    def test_forbidden_macula_fields_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "forbidden MACULA Greek field"):
            assert_allowed_projection({"category": "np", "gloss": "servants"})

    def test_allowed_structure_fields_pass(self) -> None:
        assert_allowed_projection({
            "category": "cl",
            "rule": "S-IO",
            "function": "s",
            "children": [{"maculaTerminalId": "n50001001001"}],
        })

    def test_philippians_candidate_never_exports_forbidden_fields(self) -> None:
        import json
        from books import ROOT

        ledger = json.loads(
            (ROOT / "source/greek/TR1894/macula-structure-mapping.json").read_text()
        )
        candidate = project_chapter_candidate(get_book("filipenses"), 1, ledger)
        encoded = json.dumps(candidate).lower()
        self.assertNotIn('"gloss"', encoded)
        self.assertNotIn('"lemma"', encoded)
        self.assertGreater(candidate["summary"]["exactGroups"], 0)
        self.assertGreater(candidate["summary"]["holdGroups"], 0)
        validate_candidate(candidate)

    def test_persisted_mapping_proves_three_source_agreement(self) -> None:
        import json
        from books import ROOT

        ledger = json.loads(
            (ROOT / "source/greek/TR1894/macula-structure-mapping.json").read_text()
        )
        validate_mapping_ledger(ledger)


if __name__ == "__main__":
    unittest.main()
