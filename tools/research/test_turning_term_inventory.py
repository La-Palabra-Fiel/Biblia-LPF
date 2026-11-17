import importlib.util
import unittest
from pathlib import Path


PATH = Path(__file__).with_name("turning_term_inventory.py")
SPEC = importlib.util.spec_from_file_location("turning_term_inventory", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class TurningTermInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = MODULE.build()

    def test_inventory_is_source_only(self):
        self.assertEqual(
            self.payload["semanticJudgment"],
            "none-source-inventory-only",
        )

    def test_expected_nt_counts(self):
        counts = {
            key: row["occurrenceCount"]
            for key, row in self.payload["families"].items()
        }
        self.assertEqual(counts["G1994"], 39)
        self.assertEqual(counts["G1995"], 1)
        self.assertEqual(counts["G4762"], 19)
        self.assertEqual(counts["G654"], 10)

    def test_acts_uses_distinct_turning_and_mind_change_tokens(self):
        references = {
            row["reference"]
            for row in self.payload["families"]["G1994"]["occurrences"]
        }
        self.assertIn("ACT.3.19", references)
        self.assertIn("ACT.26.20", references)
        self.assertEqual(
            self.payload["comparisonFamiliesDocumentedElsewhere"],
            ["G3340", "G3341", "G3338", "H5162"],
        )

    def test_shuv_inventory_is_not_a_selected_gloss(self):
        row = self.payload["families"]["H7725"]
        self.assertGreater(row["occurrenceCount"], 1000)
        self.assertTrue(all("spanish" not in item for item in row["occurrences"]))


if __name__ == "__main__":
    unittest.main()
