"""Tests for the pinned, positive-allowlist TBESG loader."""

from __future__ import annotations

import unittest

from books import NT
from greek_lexicon import AUTHORITY, SHA256, load, lookup, validate_coverage
from nt_source import load_robinson_book


class GreekLexiconTests(unittest.TestCase):
    def test_pinned_tbesg_entry_is_allowlisted(self) -> None:
        entry = lookup(26)[0]
        self.assertEqual(entry["strong"], "G0026")
        self.assertEqual(entry["sourceSha256"], SHA256)
        self.assertEqual(entry["authority"], AUTHORITY)
        self.assertIn("ἀγάπη", entry["greek"])
        self.assertTrue(entry["meaning"])
        self.assertNotIn("<b>", entry["meaning"])

    def test_tbesg_covers_every_robinson_lexical_identifier(self) -> None:
        strongs = {
            strong
            for book in NT
            for verse in load_robinson_book(book).values()
            for token in verse
            for strong in token.strongs
        }
        validate_coverage(strongs)
        self.assertGreater(len(load()), 10_000)

    def test_morphology_and_synonym_codes_are_not_lexical_entries(self) -> None:
        self.assertEqual(lookup(5627), [])
        self.assertEqual(lookup(5800), [])


if __name__ == "__main__":
    unittest.main()
