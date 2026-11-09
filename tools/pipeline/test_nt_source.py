"""Tests for the canonical TR1894 + Robinson source layer."""

from __future__ import annotations

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from books import get_book
from nt_source import RobinsonToken, load_reconciled_verse, reconcile_verse, tokenize_tr_verse


class NtSourceTests(unittest.TestCase):
    def test_tokenization_reconstructs_punctuation_and_whitespace(self) -> None:
        text = "Βίβλος λόγου, ἐπ’ αὐτόν."
        tokens = tokenize_tr_verse("MAT.1.1", text)
        self.assertEqual("".join(row["surface"] + row["after"] for row in tokens), text)
        self.assertEqual(tokens[1]["surface"], "λόγου")
        self.assertEqual(tokens[1]["after"], ", ")
        self.assertEqual(tokens[2]["surface"], "ἐπ’")

    def test_philippians_1_1_binds_robinson_without_owning_surface(self) -> None:
        result = load_reconciled_verse(get_book("filipenses"), 1, 1)
        self.assertEqual(result["status"], "exact")
        self.assertEqual(result["trTokens"][0]["surfaceBeta"], "paulov")
        self.assertEqual(result["trTokens"][0]["surfaceGreek"], "παυλος")
        self.assertEqual(result["trTokens"][0]["morphology"]["rawTag"], "N-NSM")
        self.assertEqual(result["trTokens"][0]["morphology"]["sourceSurfaceBeta"], "paulov")

    def test_textual_difference_is_hold_and_has_no_bound_morphology(self) -> None:
        result = reconcile_verse(
            "MAT.1.1",
            ["a"],
            [RobinsonToken(1, "b", (1,), "N-NSM")],
        )
        self.assertEqual(result["status"], "hold")
        self.assertTrue(result["scrivenerTokens"])
        self.assertTrue(result["robinsonTokens"])

    def test_human_approved_boundary_preserves_upstream_morph_reference(self) -> None:
        result = load_reconciled_verse(get_book("mateo"), 15, 5)
        self.assertEqual(result["status"], "human-approved-verse-boundary")
        moved = result["trTokens"][17]
        self.assertEqual(moved["surfaceBeta"], "kai")
        self.assertEqual(moved["morphology"]["sourceReference"], "MAT.15.6")
        self.assertEqual(moved["morphology"]["sourceOrdinal"], 1)

    def test_individually_approved_scv_surface_keeps_robinson_morphology(self) -> None:
        result = load_reconciled_verse(get_book("mateo"), 2, 23)
        self.assertEqual(result["status"], "human-approved-scv-surface")
        token = result["trTokens"][6]
        self.assertEqual(token["surfaceBeta"], "nazarey")
        self.assertEqual(token["surfaceGreek"], "ναζαρεθ")
        self.assertEqual(token["morphology"]["rawTag"], "N-PRI")

    def test_unique_utr_variant_path_requires_human_review(self) -> None:
        result = load_reconciled_verse(get_book("mateo"), 2, 11)
        self.assertEqual(result["status"], "human-approved-variant-path")
        self.assertEqual(result["omittedRobinsonTokens"][0]["surfaceBeta"], "euron")
        self.assertTrue(result["proposedRobinsonOrdinals"])
        self.assertEqual(result["adjudication"]["reviewer"], "John Wry")


if __name__ == "__main__":
    unittest.main()
