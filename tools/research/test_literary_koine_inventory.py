import hashlib
import importlib.util
import json
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools/research/literary_koine_inventory.py"
SPEC = importlib.util.spec_from_file_location("literary_koine_inventory", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class LiteraryKoineInventoryTests(unittest.TestCase):
    def setUp(self):
        self.base = ROOT / "source/greek/literary-koine"
        self.manifest = json.loads(
            (self.base / "LITERARY_KOINE_MANIFEST.json").read_text(encoding="utf-8")
        )

    def test_manifest_is_closed_and_excludes_translation_paths(self):
        self.assertEqual(self.manifest["schema"], "lpf-literary-koine-manifest-v1")
        self.assertEqual(
            self.manifest["authorizationScope"], "named-human-lexical-research-only"
        )
        self.assertFalse(self.manifest["modelExposure"])
        self.assertEqual(self.manifest["canonicalPacketPolicy"], "lbf-source-policy-v4")
        self.assertEqual({x["id"] for x in self.manifest["sources"]}, {
            "ogl-philo", "perseus-josephus", "perseus-plutarch",
            "perseus-dio-chrysostom", "perseus-epictetus",
        })
        for source in self.manifest["sources"]:
            self.assertIn("grc", source["greekGlob"])
            self.assertIn("-eng", source["excludedPathMarkers"])
            self.assertRegex(source["commit"], r"^[0-9a-f]{40}$")
            self.assertRegex(source["tree"], r"^[0-9a-f]{40}$")
            self.assertRegex(source["greekFileSetSha256"], r"^[0-9a-f]{64}$")

    def test_committed_inventories_are_surface_only(self):
        expected = {
            "philo-metano-family.json": (59, 57, 2),
            "josephus-metano-family.json": (84, 70, 14),
            "plutarch-metano-family.json": (96, 59, 37),
            "dio-chrysostom-metano-family.json": (7, 6, 1),
            "epictetus-metano-family.json": (2, 2, 0),
        }
        banned_keys = {"lemma", "morphology", "gloss", "translation", "semanticRole"}
        for filename, counts in expected.items():
            inventory = json.loads((self.base / "inventories" / filename).read_text("utf-8"))
            self.assertFalse(inventory["modelExposed"])
            self.assertEqual(inventory["semanticJudgment"], "none-surface-concordance-only")
            self.assertEqual(inventory["summary"]["occurrenceCount"], counts[0])
            self.assertEqual(
                inventory["summary"]["countsByNormalizedPrefix"],
                {"μετανο": counts[1], "μεταμελ": counts[2]},
            )
            for hit in inventory["occurrences"]:
                self.assertIn("grc", hit["path"])
                self.assertTrue(
                    hit["normalizedSurface"].startswith(hit["matchedNormalizedPrefix"])
                )
                self.assertTrue(hit["immediateContext"])
                self.assertFalse(banned_keys.intersection(hit))

        diatheke_expected = {
            "philo-diatheke-family.json": 23,
            "josephus-diatheke-family.json": 34,
            "plutarch-diatheke-family.json": 16,
            "dio-chrysostom-diatheke-family.json": 1,
            "epictetus-diatheke-family.json": 1,
        }
        for filename, count in diatheke_expected.items():
            inventory = json.loads((self.base / "inventories" / filename).read_text("utf-8"))
            self.assertEqual(inventory["summary"]["occurrenceCount"], count)
            self.assertEqual(
                inventory["summary"]["countsByNormalizedPrefix"], {"διαθηκ": count}
            )
            self.assertFalse(inventory["modelExposed"])

        turning_expected = {
            "philo-turning-family.json": 118,
            "josephus-turning-family.json": 104,
            "plutarch-turning-family.json": 246,
            "dio-chrysostom-turning-family.json": 19,
            "epictetus-turning-family.json": 66,
        }
        for filename, count in turning_expected.items():
            inventory = json.loads((self.base / "inventories" / filename).read_text("utf-8"))
            self.assertEqual(inventory["summary"]["occurrenceCount"], count)
            self.assertFalse(inventory["modelExposed"])

        destination_expected = {
            "philo-destination-family.json": 12,
            "josephus-destination-family.json": 6,
            "plutarch-destination-family.json": 79,
            "dio-chrysostom-destination-family.json": 6,
            "epictetus-destination-family.json": 3,
        }
        for filename, count in destination_expected.items():
            inventory = json.loads((self.base / "inventories" / filename).read_text("utf-8"))
            self.assertEqual(inventory["summary"]["occurrenceCount"], count)
            self.assertEqual(
                inventory["summary"]["countsByNormalizedPrefix"]["γεενν"], 0
            )
            self.assertFalse(inventory["modelExposed"])

        psyche_expected = {
            "philo-psyche-family.json": 1749,
            "josephus-psyche-family.json": 224,
            "plutarch-psyche-family.json": 998,
            "dio-chrysostom-psyche-family.json": 127,
            "epictetus-psyche-family.json": 63,
        }
        for filename, count in psyche_expected.items():
            inventory = json.loads((self.base / "inventories" / filename).read_text("utf-8"))
            self.assertEqual(inventory["summary"]["occurrenceCount"], count)
            self.assertFalse(inventory["modelExposed"])
            self.assertTrue(all(
                hit["surface"].casefold() != "ψύχη" for hit in inventory["occurrences"]
            ))

        salvation_expected = {
            "philo-salvation-family.json": 206,
            "josephus-salvation-family.json": 302,
            "plutarch-salvation-family.json": 401,
            "dio-chrysostom-salvation-family.json": 70,
            "epictetus-salvation-family.json": 27,
        }
        family = next(
            row for row in self.manifest["targetFamilies"]
            if row["id"] == "salvation-family"
        )
        expected_forms = {
            MODULE.normalize_greek(form)
            for form in family["normalizedExactForms"]
        }
        for filename, count in salvation_expected.items():
            inventory = json.loads((self.base / "inventories" / filename).read_text("utf-8"))
            self.assertEqual(inventory["summary"]["occurrenceCount"], count)
            self.assertFalse(inventory["modelExposed"])
            self.assertTrue(all(
                hit["normalizedSurface"] in expected_forms
                for hit in inventory["occurrences"]
            ))

        worship_expected = {
            "philo-worship-families.json": 36,
            "josephus-worship-families.json": 107,
            "plutarch-worship-families.json": 96,
            "dio-chrysostom-worship-families.json": 6,
            "epictetus-worship-families.json": 2,
        }
        family = next(
            row for row in self.manifest["targetFamilies"]
            if row["id"] == "worship-families"
        )
        expected_forms = {
            MODULE.normalize_greek(form)
            for form in family["normalizedExactForms"]
        }
        for filename, count in worship_expected.items():
            inventory = json.loads((self.base / "inventories" / filename).read_text("utf-8"))
            self.assertEqual(inventory["summary"]["occurrenceCount"], count)
            self.assertTrue(all(
                hit["normalizedSurface"] in expected_forms
                for hit in inventory["occurrences"]
            ))

        church_expected = {
            "philo-church-assembly-families.json": 31,
            "josephus-church-assembly-families.json": 87,
            "plutarch-church-assembly-families.json": 173,
            "dio-chrysostom-church-assembly-families.json": 17,
            "epictetus-church-assembly-families.json": 3,
        }
        family = next(x for x in self.manifest["targetFamilies"] if x["id"] == "church-assembly-families")
        expected_forms = {MODULE.normalize_greek(x) for x in family["normalizedExactForms"]}
        for filename, count in church_expected.items():
            inventory = json.loads((self.base / "inventories" / filename).read_text("utf-8"))
            self.assertEqual(inventory["summary"]["occurrenceCount"], count)
            self.assertTrue(all(x["normalizedSurface"] in expected_forms for x in inventory["occurrences"]))

        baptism_expected = {
            "philo-baptism-washing-families.json": 2,
            "josephus-baptism-washing-families.json": 8,
            "plutarch-baptism-washing-families.json": 13,
            "dio-chrysostom-baptism-washing-families.json": 0,
            "epictetus-baptism-washing-families.json": 0,
        }
        family = next(x for x in self.manifest["targetFamilies"] if x["id"] == "baptism-washing-families")
        expected_forms = {MODULE.normalize_greek(x) for x in family["normalizedExactForms"]}
        for filename, count in baptism_expected.items():
            inventory = json.loads((self.base / "inventories" / filename).read_text("utf-8"))
            self.assertEqual(inventory["summary"]["occurrenceCount"], count)
            self.assertTrue(all(x["normalizedSurface"] in expected_forms for x in inventory["occurrences"]))

        apostle_expected = {
            "philo-apostle-family.json": 0,
            "josephus-apostle-family.json": 1,
            "plutarch-apostle-family.json": 3,
            "dio-chrysostom-apostle-family.json": 0,
            "epictetus-apostle-family.json": 0,
        }
        family = next(x for x in self.manifest["targetFamilies"] if x["id"] == "apostle-family")
        expected_forms = {MODULE.normalize_greek(x) for x in family["normalizedExactForms"]}
        for filename, count in apostle_expected.items():
            inventory = json.loads((self.base / "inventories" / filename).read_text("utf-8"))
            self.assertEqual(inventory["summary"]["occurrenceCount"], count)
            self.assertTrue(all(x["normalizedSurface"] in expected_forms for x in inventory["occurrences"]))

    def test_consultation_hashes_bind_results(self):
        log = json.loads((self.base / "CONSULTATIONS.json").read_text("utf-8"))
        self.assertEqual(log["schema"], "lpf-literary-koine-consultations-v1")
        self.assertEqual(len(log["consultations"]), 50)
        for record in log["consultations"]:
            artifact = ROOT / record["resultArtifact"]
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
            self.assertEqual(digest, record["resultSha256"])
            self.assertFalse(record["canonicalTranslationModelExposed"])
            self.assertIsInstance(record["researchAssistantReviewedPrimaryContexts"], bool)
            if not record["researchAssistantReviewedPrimaryContexts"]:
                self.assertIn(
                    record["dossier"],
                    {"notes/research/conversion.md", "notes/research/alma.md"},
                )
            self.assertFalse(record["canonicalPacketChanged"])

    def test_text_extraction_excludes_notes_and_prefers_correction(self):
        element = ET.fromstring(
            '<p xmlns="http://www.tei-c.org/ns/1.0">uno '
            '<note>TRADUCCIÓN</note>dos '
            '<choice><sic>errado</sic><corr>μετάνοια</corr></choice> tres</p>'
        )
        text = MODULE.compact(MODULE.source_text(element))
        self.assertEqual(text, "uno dos μετάνοια tres")
        self.assertNotIn("TRADUCCIÓN", text)
        self.assertNotIn("errado", text)

    def test_normalization_is_discovery_only(self):
        self.assertEqual(MODULE.normalize_greek("Μετάνοιας"), "μετανοιασ")
        self.assertEqual(MODULE.normalize_greek("μεταμέλεια"), "μεταμελεια")
        self.assertNotEqual(MODULE.normalize_greek("ᾅδην"), MODULE.normalize_greek("ἄδην"))
        self.assertNotEqual(MODULE.exact_greek("ᾅδην"), MODULE.exact_greek("ἄδην"))


if __name__ == "__main__":
    unittest.main()
