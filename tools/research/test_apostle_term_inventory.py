import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("apostle_term_inventory.py")
SPEC = importlib.util.spec_from_file_location("apostle_term_inventory", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class ApostleTermInventoryTests(unittest.TestCase):
    def test_inventory_keeps_sending_and_messenger_families_separate(self):
        payload = MODULE.build()
        self.assertEqual(payload["schema"], "lpf-biblical-apostle-term-inventory-v1")
        self.assertEqual(
            set(payload["families"]),
            {"G652", "G649", "G3992", "G32", "H7971", "H4397"},
        )
        for strong, family in payload["families"].items():
            self.assertGreater(family["occurrenceCount"], 0, strong)
            self.assertEqual(family["occurrenceCount"], len(family["occurrences"]))
        self.assertNotEqual(
            payload["families"]["G652"]["researchRole"],
            payload["families"]["G32"]["researchRole"],
        )


if __name__ == "__main__":
    unittest.main()
