import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools/research/life_person_term_inventory.py"
SPEC = importlib.util.spec_from_file_location("life_person_term_inventory", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class LifePersonTermInventoryTests(unittest.TestCase):
    def test_canonical_counts_and_research_roles(self):
        inventory = MODULE.build()
        self.assertEqual(inventory["semanticJudgment"], "none-source-inventory-only")
        counts = {
            key: value["occurrenceCount"]
            for key, value in inventory["families"].items()
        }
        self.assertEqual(counts, {
            "G5590": 105,
            "G4151": 386,
            "G2222": 134,
            "H5315": 754,
            "H5397": 24,
            "H7307": 378,
        })
        self.assertEqual(inventory["families"]["H5315"]["researchRole"], "core-family")
        self.assertEqual(inventory["families"]["G5590"]["researchRole"], "core-family")
        self.assertTrue(all(
            inventory["families"][key]["researchRole"] == "contrast-family"
            for key in ("H5397", "H7307", "G4151", "G2222")
        ))

    def test_inventory_contains_no_spanish_gloss(self):
        inventory = MODULE.build()
        for family in inventory["families"].values():
            for occurrence in family["occurrences"]:
                self.assertNotIn("gloss", occurrence)
                self.assertNotIn("translation", occurrence)

    def test_core_families_keep_key_canonical_contexts_visible(self):
        inventory = MODULE.build()
        ot_refs = {
            row["reference"] for row in inventory["families"]["H5315"]["occurrences"]
        }
        nt_refs = {
            row["reference"] for row in inventory["families"]["G5590"]["occurrences"]
        }
        self.assertTrue({"Gen.1.20", "Gen.2.7", "Lev.17.11"}.issubset(ot_refs))
        self.assertTrue({"MAT.10.28", "JHN.10.11", "ACT.27.37"}.issubset(nt_refs))


if __name__ == "__main__":
    unittest.main()
