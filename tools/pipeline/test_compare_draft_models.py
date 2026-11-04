"""No-cost tests for the GPT-5.6/GPT-6.1 draft evaluation harness."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import compare_draft_models as comparison


class DraftModelComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = comparison.build_manifest()

    def test_sample_is_balanced_and_approved(self) -> None:
        categories = [item["category"] for item in self.manifest["sample"]]
        self.assertEqual(len(categories), 12)
        self.assertEqual(categories.count("accepted-unchanged"), 4)
        self.assertEqual(categories.count("spanish-correction"), 4)
        self.assertEqual(categories.count("alignment-correction"), 4)
        self.assertTrue(all(item["goldSha256"] for item in self.manifest["sample"]))

    def test_cost_ceiling_covers_twenty_four_calls(self) -> None:
        cost = self.manifest["cost"]
        self.assertEqual(sum(row["calls"] for row in cost["byModel"].values()), 24)
        self.assertGreater(cost["maximumUsd"], cost["likelyUsd"])

    def test_post_run_verification_allows_only_prompt_drift(self) -> None:
        comparison.verify_manifest(self.manifest, before_paid_calls=False)

    def test_source_order_units_fail_reconstruction(self) -> None:
        packet = {"tokens": [
            {"sourceTokenId": "h5", "morphExpanded": "Hebrew; conjunction; verb"},
            {"sourceTokenId": "h6", "morphExpanded": "Hebrew; noun proper"},
        ]}
        candidate = {"spanish": "y Moisés subió", "units": [
            {"es": "y subió", "sourceTokenIds": ["h5"]},
            {"es": "Moisés", "sourceTokenIds": ["h6"]},
        ]}
        codes = {row["code"] for row in comparison.structural_findings(packet, candidate)}
        self.assertIn("spanish-reconstruction", codes)

    def test_discontinuous_correct_order_passes(self) -> None:
        packet = {"tokens": [
            {"sourceTokenId": "h5", "morphExpanded": "Hebrew; conjunction; verb"},
            {"sourceTokenId": "h6", "morphExpanded": "Hebrew; noun proper"},
        ]}
        candidate = {"spanish": "y Moisés subió", "units": [
            {"es": "y", "sourceTokenIds": ["h5"]},
            {"es": "Moisés", "sourceTokenIds": ["h6"]},
            {"es": "subió", "sourceTokenIds": ["h5"]},
        ]}
        self.assertEqual(comparison.structural_findings(packet, candidate), [])


if __name__ == "__main__":
    unittest.main()
