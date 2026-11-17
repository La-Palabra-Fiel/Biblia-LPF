import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools/research/salvation_term_inventory.py"
SPEC = importlib.util.spec_from_file_location("salvation_term_inventory", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class SalvationTermInventoryTests(unittest.TestCase):
    def test_canonical_counts_and_research_roles(self):
        inventory = MODULE.build()
        self.assertEqual(inventory["semanticJudgment"], "none-source-inventory-only")
        counts = {
            key: value["occurrenceCount"]
            for key, value in inventory["families"].items()
        }
        self.assertEqual(counts, {
            "G4982": 110,
            "G4991": 45,
            "G4992": 5,
            "G4990": 24,
            "G1295": 8,
            "G4506": 18,
            "G1807": 8,
            "G3084": 3,
            "H3444": 77,
            "H3467": 206,
            "H3468": 36,
            "H8668": 34,
            "H4422": 95,
            "H6403": 25,
            "H5337": 213,
        })
        core = {"G4982", "G4991", "G4992", "G4990", "H3444", "H3467", "H3468", "H8668"}
        self.assertTrue(all(
            inventory["families"][key]["researchRole"] == ("core-family" if key in core else "contrast-family")
            for key in inventory["families"]
        ))

    def test_inventory_contains_no_spanish_gloss(self):
        inventory = MODULE.build()
        for family in inventory["families"].values():
            for occurrence in family["occurrences"]:
                self.assertNotIn("gloss", occurrence)
                self.assertNotIn("translation", occurrence)

    def test_core_families_keep_distinct_canonical_scenarios_visible(self):
        inventory = MODULE.build()
        h3444 = {row["reference"] for row in inventory["families"]["H3444"]["occurrences"]}
        g4982 = {row["reference"] for row in inventory["families"]["G4982"]["occurrences"]}
        g4991 = {row["reference"] for row in inventory["families"]["G4991"]["occurrences"]}
        self.assertTrue({"Exod.14.13", "Jonah.2.9"}.issubset(h3444))
        self.assertTrue({"MAT.8.25", "MAT.9.22", "ACT.27.20", "JAS.5.15"}.issubset(g4982))
        self.assertTrue({"LUK.1.71", "ACT.27.34", "HEB.11.7"}.issubset(g4991))


if __name__ == "__main__":
    unittest.main()
