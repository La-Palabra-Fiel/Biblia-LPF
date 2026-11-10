"""Tests for deterministic TR1894 context and corpus evidence."""

from __future__ import annotations

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from books import get_book
from nt_evidence import corpus_usage, original_language_context, syntax_for_verse
from nt_source import load_reconciled_verse


class NtEvidenceTests(unittest.TestCase):
    def test_context_uses_adjacent_tr1894_verses(self) -> None:
        rows = original_language_context(get_book("filipenses"), 1, 6)
        self.assertEqual([row["role"] for row in rows], ["previous", "current", "next"])
        self.assertEqual(rows[1]["reference"], "PHP.1.6")
        self.assertTrue(all(token["sourceTokenId"].startswith("n50") for row in rows for token in row["tokens"]))

    def test_corpus_preserves_form_morphology_and_structural_disposition(self) -> None:
        rows = corpus_usage(26, "PHP.1.16")
        self.assertTrue(rows)
        self.assertTrue(all(row["surface"] and row["morph"] for row in rows))
        self.assertTrue(all(row["structureStatus"] in {"triple-agreement-anchor", "hold-no-exact-anchor"} for row in rows))

    def test_philippians_structure_is_ready_only_after_adjudication(self) -> None:
        book = get_book("filipenses")
        ids = [row["tokenId"] for row in load_reconciled_verse(book, 1, 1)["trTokens"]]
        self.assertEqual(syntax_for_verse(book, 1, 1, ids)["status"], "READY_TR_STRUCTURE")
        ids = [row["tokenId"] for row in load_reconciled_verse(book, 1, 7)["trTokens"]]
        self.assertEqual(syntax_for_verse(book, 1, 7, ids)["status"], "READY_TR_STRUCTURE")
        ids = [row["tokenId"] for row in load_reconciled_verse(book, 1, 8)["trTokens"]]
        self.assertEqual(syntax_for_verse(book, 1, 8, ids)["status"], "HOLD_STRUCTURE")


if __name__ == "__main__":
    unittest.main()
