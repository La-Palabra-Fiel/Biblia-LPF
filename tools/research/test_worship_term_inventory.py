import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools/research/worship_term_inventory.py"
SPEC = importlib.util.spec_from_file_location("worship_term_inventory", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class WorshipTermInventoryTests(unittest.TestCase):
    def test_committed_inventory_matches_reproducible_build(self):
        expected = MODULE.build()
        path = ROOT / "notes/research/inventories/worship-terms.json"
        actual = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(actual, expected)
        self.assertEqual(actual["semanticJudgment"], "none-source-inventory-only")

    def test_protestant_numbering_and_source_families_are_explicit(self):
        inventory = MODULE.build()
        self.assertEqual(
            set(inventory["families"]),
            {"H7812", "H5647", "H5456", "H6915", "G4352", "G3000", "G4576", "G2151", "G2356", "G1479", "G1392"},
        )
        for key, family in inventory["families"].items():
            self.assertTrue(all("reference" in row for row in family["occurrences"]))
            if key.startswith("G"):
                self.assertTrue(all(
                    row["strong"] == key for row in family["occurrences"]
                ))
            else:
                self.assertTrue(all(
                    key[1:] in row["lemma"] for row in family["occurrences"]
                ))


if __name__ == "__main__":
    unittest.main()
