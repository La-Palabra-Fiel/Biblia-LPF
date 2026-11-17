import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "tools/research/covenant_term_inventory.py"
SPEC = importlib.util.spec_from_file_location("covenant_term_inventory", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class CovenantTermInventoryTests(unittest.TestCase):
    def test_canonical_counts(self):
        inventory = MODULE.build()
        counts = {
            key: value["occurrenceCount"]
            for key, value in inventory["families"].items()
        }
        self.assertEqual(counts, {"G1242": 33, "G1303": 7, "H1285": 284})
        self.assertEqual(inventory["semanticJudgment"], "none-source-inventory-only")

    def test_hebrews_sequence_is_preserved(self):
        inventory = MODULE.build()
        diatheke = [
            row["reference"] for row in inventory["families"]["G1242"]["occurrences"]
        ]
        for reference in ("HEB.9.15", "HEB.9.16", "HEB.9.17", "HEB.9.20"):
            self.assertIn(reference, diatheke)

    def test_no_spanish_gloss_is_imported(self):
        inventory = MODULE.build()
        for family in inventory["families"].values():
            for occurrence in family["occurrences"]:
                self.assertNotIn("gloss", occurrence)
                self.assertNotIn("translation", occurrence)


if __name__ == "__main__":
    unittest.main()

