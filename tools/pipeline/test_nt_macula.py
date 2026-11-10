"""Tests for the closed MACULA Greek structure mapping gate."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from books import get_book
from nt_macula import (
    apply_structure_adjudications,
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

    def test_philippians_human_adjudications_use_native_tr_tokens(self) -> None:
        import json
        from books import ROOT

        ledger = json.loads(
            (ROOT / "source/greek/TR1894/macula-structure-mapping.json").read_text()
        )
        decisions = json.loads(
            (ROOT / "source/greek/TR1894/MACULA_STRUCTURE_ADJUDICATIONS.json").read_text()
        )
        candidate = project_chapter_candidate(get_book("filipenses"), 1, ledger)
        apply_structure_adjudications(candidate, decisions)
        native_words = []

        def collect(node):
            if node.get("kind") == "tr-word":
                native_words.append(node)
            for child in node.get("children") or []:
                collect(child)

        for sentence in candidate["sentences"]:
            for root in sentence["roots"]:
                collect(root)
        self.assertEqual(
            [word["trTokenId"] for word in native_words],
            [
                "PHP.1.1.w005",
                "PHP.1.1.w006",
                "PHP.1.6.w012",
                "PHP.1.6.w014",
                "PHP.1.6.w015",
                "PHP.1.7.w030",
            ],
        )
        self.assertTrue(all("maculaTerminalId" not in word for word in native_words))
        self.assertEqual(candidate["summary"]["humanAdjudicatedWords"], 6)
        self.assertEqual(candidate["summary"]["trOnlyTokens"], 34)
        validate_candidate(candidate)


if __name__ == "__main__":
    unittest.main()
