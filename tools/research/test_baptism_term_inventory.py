import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "tools/research/baptism_term_inventory.py"
SPEC = importlib.util.spec_from_file_location("baptism_term_inventory", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class BaptismTermInventoryTests(unittest.TestCase):
    def test_committed_inventory_matches_reproducible_build(self):
        actual = json.loads((ROOT / "notes/research/inventories/baptism-terms.json").read_text("utf-8"))
        self.assertEqual(actual, MODULE.build())
        self.assertEqual(actual["semanticJudgment"], "none-source-inventory-only")

    def test_families_are_not_merged(self):
        inventory = MODULE.build()
        self.assertEqual(
            set(inventory["families"]),
            {"G907", "G908", "G909", "G910", "G911", "G3067", "G2512", "H2881", "H7364", "H3526"},
        )


if __name__ == "__main__":
    unittest.main()
