import hashlib
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools/research/clementine_latin_inventory.py"
SPEC = importlib.util.spec_from_file_location("clementine_latin_inventory", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class ClementineLatinInventoryTests(unittest.TestCase):
    def setUp(self):
        self.base = ROOT / "source/latin/clementine-vulgate"
        self.manifest = json.loads(
            (self.base / "CLEMENTINE_MANIFEST.json").read_text(encoding="utf-8")
        )

    def test_manifest_is_closed(self):
        self.assertEqual(self.manifest["schema"], "lpf-clementine-latin-manifest-v1")
        self.assertEqual(
            self.manifest["authorizationScope"],
            "named-human-historical-reception-research-only",
        )
        self.assertFalse(self.manifest["modelExposure"])
        self.assertEqual(self.manifest["canonicalPacketPolicy"], "lbf-source-policy-v4")
        source = self.manifest["source"]
        self.assertEqual(source["expectedLatinFileCount"], 73)
        self.assertRegex(source["commit"], r"^[0-9a-f]{40}$")
        self.assertRegex(source["tree"], r"^[0-9a-f]{40}$")
        self.assertRegex(source["latinFileSetSha256"], r"^[0-9a-f]{64}$")

    def test_normalization_handles_ligatures(self):
        self.assertEqual(MODULE.normalize_latin("FŒDERIS"), "foederis")
        self.assertEqual(MODULE.normalize_latin("præceptum"), "praeceptum")

    def test_inventory_is_surface_only_and_bound_to_consultation(self):
        inventory_path = self.base / "inventories/clementine-covenant-families.json"
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        self.assertFalse(inventory["modelExposed"])
        self.assertEqual(inventory["semanticJudgment"], "none-surface-concordance-only")
        self.assertEqual(
            inventory["summary"]["countsByNormalizedPrefix"],
            {"testament": 103, "pact": 109, "foedus": 83, "foeder": 137},
        )
        banned = {"lemma", "gloss", "translation", "semanticRole"}
        for hit in inventory["occurrences"]:
            self.assertFalse(banned.intersection(hit))
            self.assertTrue(hit["immediateContext"])

        log = json.loads((self.base / "CONSULTATIONS.json").read_text(encoding="utf-8"))
        self.assertEqual(log["schema"], "lpf-clementine-consultations-v1")
        self.assertEqual(len(log["consultations"]), 8)
        for record in log["consultations"]:
            artifact = ROOT / record["resultArtifact"]
            self.assertEqual(
                hashlib.sha256(artifact.read_bytes()).hexdigest(),
                record["resultSha256"],
            )
            self.assertFalse(record["canonicalTranslationModelExposed"])
            self.assertFalse(record["canonicalPacketChanged"])

    def test_destination_inventory_preserves_latin_surfaces(self):
        manifest = json.loads(
            (self.base / "CLEMENTINE_DESTINATION_MANIFEST.json").read_text("utf-8")
        )
        self.assertEqual(manifest["targetFamilies"][0]["normalizedPrefixes"], ["infern"])
        inventory = json.loads(
            (self.base / "inventories/clementine-destination-family.json").read_text("utf-8")
        )
        self.assertEqual(inventory["summary"]["occurrenceCount"], 69)
        self.assertEqual(inventory["summary"]["verseCountWithOccurrences"], 68)
        self.assertEqual(
            inventory["summary"]["countsByNormalizedPrefix"], {"infern": 69}
        )
        self.assertTrue(all(hit["immediateContext"] for hit in inventory["occurrences"]))

    def test_anima_inventory_uses_exact_forms_not_animal_derivatives(self):
        manifest = json.loads(
            (self.base / "CLEMENTINE_PSYCHE_MANIFEST.json").read_text("utf-8")
        )
        inventory = json.loads(
            (self.base / "inventories/clementine-anima-family.json").read_text("utf-8")
        )
        self.assertEqual(inventory["summary"]["occurrenceCount"], 911)
        self.assertEqual(inventory["summary"]["verseCountWithOccurrences"], 848)
        expected = {
            MODULE.normalize_latin(form)
            for form in manifest["targetFamilies"][0]["normalizedExactForms"]
        }
        self.assertEqual(
            set(inventory["summary"]["countsByNormalizedPrefix"]), expected
        )
        self.assertTrue(all(
            hit["normalizedSurface"] in expected for hit in inventory["occurrences"]
        ))

    def test_salvation_inventory_uses_exact_forms_and_keeps_homographs(self):
        manifest = json.loads(
            (self.base / "CLEMENTINE_SALVATION_MANIFEST.json").read_text("utf-8")
        )
        inventory = json.loads(
            (self.base / "inventories/clementine-salvation-family.json").read_text("utf-8")
        )
        self.assertEqual(inventory["summary"]["occurrenceCount"], 684)
        self.assertEqual(inventory["summary"]["verseCountWithOccurrences"], 646)
        expected = {
            MODULE.normalize_latin(form)
            for form in manifest["targetFamilies"][0]["normalizedExactForms"]
        }
        self.assertEqual(
            set(inventory["summary"]["countsByNormalizedPrefix"]), expected
        )
        self.assertTrue(all(
            hit["normalizedSurface"] in expected for hit in inventory["occurrences"]
        ))
        self.assertTrue(any(
            hit["normalizedSurface"] == "salutare"
            and "salutare eum" in hit["immediateContext"]
            for hit in inventory["occurrences"]
        ))

    def test_worship_inventory_preserves_adorare_servire_distinction(self):
        inventory = json.loads(
            (self.base / "inventories/clementine-worship-families.json").read_text("utf-8")
        )
        self.assertEqual(inventory["summary"]["occurrenceCount"], 566)
        self.assertEqual(inventory["summary"]["verseCountWithOccurrences"], 506)
        self.assertEqual(
            inventory["summary"]["countsByNormalizedPrefix"]["ador"], 281
        )
        matthew = [
            hit for hit in inventory["occurrences"]
            if hit["bookFile"] == "Mt.lat" and hit["reference"] == "4:10"
        ]
        self.assertEqual(
            {hit["normalizedSurface"] for hit in matthew},
            {"adorabis", "servies"},
        )

    def test_church_inventory_preserves_multiple_latin_families(self):
        inventory = json.loads(
            (self.base / "inventories/clementine-church-families.json").read_text("utf-8")
        )
        self.assertEqual(inventory["summary"]["occurrenceCount"], 717)
        self.assertEqual(inventory["summary"]["verseCountWithOccurrences"], 689)
        self.assertEqual(
            inventory["summary"]["countsByNormalizedPrefix"],
            {"ecclesi": 170, "congreg": 435, "synagog": 78, "concili": 34},
        )
        acts_19 = [
            x for x in inventory["occurrences"]
            if x["bookFile"] == "Act.lat" and x["reference"] in {"19:32", "19:39", "19:40"}
            and x["matchedNormalizedPrefix"] == "ecclesi"
        ]
        self.assertEqual(len(acts_19), 3)

    def test_baptism_inventory_preserves_transliteration_and_action_families(self):
        inventory = json.loads(
            (self.base / "inventories/clementine-baptism-families.json").read_text("utf-8")
        )
        self.assertEqual(inventory["summary"]["occurrenceCount"], 249)
        self.assertEqual(inventory["summary"]["verseCountWithOccurrences"], 219)
        self.assertEqual(
            inventory["summary"]["countsByNormalizedPrefix"],
            {"bapt": 117, "merg": 6, "ting": 11, "lav": 115},
        )

    def test_apostle_inventory_separates_transliteration_and_controls(self):
        inventory = json.loads(
            (self.base / "inventories/clementine-apostle-families.json").read_text("utf-8")
        )
        self.assertEqual(inventory["summary"]["occurrenceCount"], 523)
        self.assertEqual(inventory["summary"]["verseCountWithOccurrences"], 490)
        counts = inventory["summary"]["countsByNormalizedPrefix"]
        self.assertEqual(sum(counts[x] for x in (
            "apostolatum", "apostolatus", "apostoli", "apostolis",
            "apostolorum", "apostolos", "apostolum", "apostolus",
        )), 85)
        self.assertEqual({key: counts[key] for key in ("legat", "miss", "nunti")}, {
            "legat": 32, "miss": 85, "nunti": 321,
        })


if __name__ == "__main__":
    unittest.main()
