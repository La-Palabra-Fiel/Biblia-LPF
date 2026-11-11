"""Tests for the closed MACULA Greek structure mapping gate."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from books import get_book
from nt_macula import (
    APPROVED_ROBINSON_BINDING_RULE,
    apply_structure_adjudications,
    apply_tr_authority_adaptations,
    apply_tr_authority_fallbacks,
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

    def test_isolated_one_to_one_gaps_adapt_to_native_tr_without_macula_identity(self) -> None:
        import json
        from books import ROOT

        ledger = json.loads(
            (ROOT / "source/greek/TR1894/macula-structure-mapping.json").read_text()
        )
        adjudications = {
            "schema": "tr1894-native-structure-adjudications-v1",
            "decisions": [],
        }
        candidate = project_chapter_candidate(get_book("mateo"), 1, ledger)
        apply_tr_authority_adaptations(candidate, ledger, adjudications)
        self.assertEqual(candidate["summary"]["trAuthorityAdaptedWords"], 21)
        self.assertEqual(len(candidate["trAuthorityAdaptations"]), 21)
        self.assertLess(candidate["summary"]["holdGroups"], 82)
        adapted_words = []

        def collect(node):
            if node.get("status") == "tr-authority-adapted" and node.get("kind") == "tr-word":
                adapted_words.append(node)
            for child in node.get("children") or []:
                collect(child)

        for sentence in candidate["sentences"]:
            for root in sentence["roots"]:
                collect(root)
        self.assertEqual(len(adapted_words), 21)
        self.assertTrue(all("maculaTerminalId" not in word for word in adapted_words))
        self.assertTrue(all(row.get("replacedMaculaTerminalId") for row in candidate["trAuthorityAdaptations"]))
        validate_candidate(candidate)

    def test_human_approved_scv_robinson_binding_is_reused_as_native_tr(self) -> None:
        import json
        from books import ROOT

        ledger = json.loads(
            (ROOT / "source/greek/TR1894/macula-structure-mapping.json").read_text()
        )
        candidate = project_chapter_candidate(get_book("mateo"), 2, ledger)
        apply_tr_authority_adaptations(candidate, ledger, {
            "schema": "tr1894-native-structure-adjudications-v1",
            "decisions": [],
        })
        adapted = {
            row["trTokenId"]: row["ruleId"]
            for row in candidate["trAuthorityAdaptations"]
            if row.get("trTokenId")
        }
        self.assertEqual(adapted["MAT.2.23.w007"], APPROVED_ROBINSON_BINDING_RULE)
        self.assertNotIn("MAT.2.23.w007", candidate["trOnlyTokenIds"])

    def test_isolated_macula_only_terminal_promotes_the_sole_group_child(self) -> None:
        import json
        from books import ROOT

        ledger = json.loads(
            (ROOT / "source/greek/TR1894/macula-structure-mapping.json").read_text()
        )
        candidate = project_chapter_candidate(get_book("mateo"), 2, ledger)
        apply_tr_authority_adaptations(candidate, ledger, {
            "schema": "tr1894-native-structure-adjudications-v1",
            "decisions": [],
        })
        repairs = [
            row for row in candidate["trAuthorityAdaptations"]
            if row["ruleId"] == "tr-authority-macula-only-promote-child-v1"
        ]
        self.assertEqual(len(repairs), 2)
        self.assertTrue(all(row.get("targetCandidateNodeId") for row in repairs))
        self.assertTrue(all(row.get("replacedMaculaTerminalId") for row in repairs))
        validate_candidate(candidate)

    def test_flat_permutation_rebuilds_only_the_complete_terminal_group(self) -> None:
        import json
        from books import ROOT

        ledger = json.loads(
            (ROOT / "source/greek/TR1894/macula-structure-mapping.json").read_text()
        )
        candidate = project_chapter_candidate(
            get_book("1tesalonicenses"), 2, ledger
        )
        apply_tr_authority_adaptations(candidate, ledger, {
            "schema": "tr1894-native-structure-adjudications-v1",
            "decisions": [],
        })
        repairs = [
            row for row in candidate["trAuthorityAdaptations"]
            if row["ruleId"] == "tr-authority-flat-permutation-v1"
        ]
        self.assertEqual(len(repairs), 1)
        self.assertEqual(repairs[0]["reference"], "1TH.2.13")
        self.assertEqual(
            repairs[0]["trTokenIds"],
            ["1TH.2.13.w023", "1TH.2.13.w024"],
        )
        self.assertEqual(len(repairs[0]["replacedMaculaTerminalIds"]), 2)
        validate_candidate(candidate)

    def test_tr_fallback_covers_every_remaining_disagreement_without_syntax_claims(self) -> None:
        import json
        from books import ROOT

        ledger = json.loads(
            (ROOT / "source/greek/TR1894/macula-structure-mapping.json").read_text()
        )
        candidate = project_chapter_candidate(get_book("mateo"), 1, ledger)
        adjudications = {
            "schema": "tr1894-native-structure-adjudications-v1",
            "decisions": [],
        }
        apply_tr_authority_adaptations(candidate, ledger, adjudications)
        apply_structure_adjudications(candidate, adjudications)
        apply_tr_authority_fallbacks(candidate, ledger)
        fallback_tokens = {
            token_id
            for row in candidate["trAuthorityFallbacks"]
            for token_id in row["trTokenIds"]
        }
        self.assertEqual(fallback_tokens, set(candidate["trOnlyTokenIds"]))
        self.assertGreater(candidate["summary"]["trAuthorityFallbackVerses"], 0)
        self.assertTrue(all(
            row["structuralClaim"] == "none-beyond-canonical-tr-order"
            for row in candidate["trAuthorityFallbacks"]
        ))
        validate_candidate(candidate)

    def test_noncanonical_macula_verse_is_retired_without_reassigning_it(self) -> None:
        import json
        from books import ROOT

        ledger = json.loads(
            (ROOT / "source/greek/TR1894/macula-structure-mapping.json").read_text()
        )
        candidate = project_chapter_candidate(get_book("marcos"), 16, ledger)
        adjudications = {
            "schema": "tr1894-native-structure-adjudications-v1",
            "decisions": [],
        }
        apply_tr_authority_adaptations(candidate, ledger, adjudications)
        apply_structure_adjudications(candidate, adjudications)
        apply_tr_authority_fallbacks(candidate, ledger)
        retired = candidate["retiredNoncanonicalMaculaTerminalIds"]
        self.assertEqual(len(retired), 33)
        self.assertTrue(all(token_id.startswith("n41016099") for token_id in retired))
        self.assertNotIn(
            "MRK.16.99",
            {row["reference"] for row in candidate["trAuthorityFallbacks"]},
        )
        validate_candidate(candidate)

    def test_every_nontriple_robinson_surface_is_already_human_resolved(self) -> None:
        import json
        from books import ROOT
        from nt_source import BOOK_BY_TR_CODE, load_reconciled_verse

        ledger = json.loads(
            (ROOT / "source/greek/TR1894/macula-structure-mapping.json").read_text()
        )
        reconciliations = []
        for row in ledger["verses"]:
            if not row.get("nonAgreeingRobinsonTokenIds"):
                continue
            code, chapter, verse = row["reference"].split(".")
            tokens = {
                token["tokenId"]: token
                for token in load_reconciled_verse(
                    BOOK_BY_TR_CODE[code], int(chapter), int(verse)
                )["trTokens"]
            }
            reconciliations.extend(
                str((tokens[token_id].get("morphology") or {}).get("reconciliation") or "")
                for token_id in row["nonAgreeingRobinsonTokenIds"]
            )
        self.assertEqual(len(reconciliations), 44)
        self.assertTrue(all(value.startswith("human-approved-") for value in reconciliations))

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
        native_ids = {word["trTokenId"] for word in native_words}
        self.assertTrue(
            {
                "PHP.1.1.w005",
                "PHP.1.1.w006",
                "PHP.1.6.w012",
                "PHP.1.6.w014",
                "PHP.1.6.w015",
                "PHP.1.7.w030",
                "PHP.1.8.w004",
                "PHP.1.8.w013",
                "PHP.1.8.w014",
                "PHP.1.11.w002",
                "PHP.1.11.w004",
                "PHP.1.16.w001",
                "PHP.1.16.w015",
                "PHP.1.17.w001",
                "PHP.1.17.w011",
                "PHP.1.23.w002",
                "PHP.1.24.w004",
                "PHP.1.25.w008",
                "PHP.1.27.w016",
                "PHP.1.28.w010",
                "PHP.1.28.w015",
                "PHP.1.30.w006",
            }.issubset(native_ids)
        )
        self.assertTrue(all("maculaTerminalId" not in word for word in native_words))
        self.assertEqual(candidate["summary"]["humanAdjudicatedWords"], 46)
        self.assertEqual(candidate["summary"]["trOnlyTokens"], 0)
        self.assertEqual(candidate["summary"]["unmatchedMaculaWords"], 0)
        self.assertEqual(candidate["summary"]["holdGroups"], 0)
        validate_candidate(candidate)


if __name__ == "__main__":
    unittest.main()
