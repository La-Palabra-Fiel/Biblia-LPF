import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools/research/destination_term_inventory.py"
SPEC = importlib.util.spec_from_file_location("destination_term_inventory", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class DestinationTermInventoryTests(unittest.TestCase):
    def test_canonical_counts_and_distinct_families(self):
        inventory = MODULE.build()
        self.assertEqual(inventory["semanticJudgment"], "none-source-inventory-only")
        counts = {
            key: value["occurrenceCount"]
            for key, value in inventory["families"].items()
        }
        self.assertEqual(counts, {"G86": 11, "G1067": 12, "G5020": 1, "H7585": 66})

    def test_inventory_contains_no_spanish_gloss(self):
        inventory = MODULE.build()
        for family in inventory["families"].values():
            for occurrence in family["occurrences"]:
                self.assertNotIn("gloss", occurrence)
                self.assertNotIn("translation", occurrence)

    def test_revelation_keeps_hades_occurrences_visible(self):
        inventory = MODULE.build()
        references = {
            row["reference"] for row in inventory["families"]["G86"]["occurrences"]
        }
        self.assertIn("REV.20.13", references)
        self.assertIn("REV.20.14", references)


if __name__ == "__main__":
    unittest.main()

