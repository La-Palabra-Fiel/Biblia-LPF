import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "tools/research/church_term_inventory.py"
SPEC = importlib.util.spec_from_file_location("church_term_inventory", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class ChurchTermInventoryTests(unittest.TestCase):
    def test_committed_inventory_matches_reproducible_build(self):
        actual = json.loads((ROOT / "notes/research/inventories/church-terms.json").read_text("utf-8"))
        self.assertEqual(actual, MODULE.build())
        self.assertEqual(actual["semanticJudgment"], "none-source-inventory-only")

    def test_families_remain_formally_distinct(self):
        inventory = MODULE.build()
        self.assertEqual(
            set(inventory["families"]),
            {"G1577", "G4864", "G4892", "G3831", "H6951", "H5712", "H4150"},
        )
        self.assertEqual(
            {row["reference"] for row in inventory["families"]["G1577"]["occurrences"] if row["reference"].startswith("ACT.19.")},
            {"ACT.19.32", "ACT.19.39", "ACT.19.41"},
        )


if __name__ == "__main__":
    unittest.main()
