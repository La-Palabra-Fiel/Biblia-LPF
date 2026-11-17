import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("ddbdp_primary_inventory.py")
SPEC = importlib.util.spec_from_file_location("ddbdp_primary_inventory", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DDbDPPrimaryInventoryTests(unittest.TestCase):
    def test_manifest_rejects_broader_or_missing_authorization(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(
                '{"schema":"lpf-ddbdp-primary-query-manifest-v1",'
                '"status":"authorized-for-all-model-input"}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "authorization scope"):
                MODULE.load_manifest(path)

    def test_committed_inventory_matches_authorized_manifest(self):
        manifest = MODULE.load_manifest(MODULE.DEFAULT_MANIFEST)
        inventory_path = (
            MODULE.ROOT
            / "source"
            / "greek"
            / "documentary-koine"
            / "inventories"
            / "metano-family.json"
        )
        self.assertEqual(
            MODULE.sha256(inventory_path),
            manifest["fullConcordance"]["result"]["artifactSha256"],
        )
        payload = json.loads(inventory_path.read_text(encoding="utf-8"))
        self.assertEqual(
            payload["authority"], "authorized-human-lexical-research-only"
        )
        self.assertEqual(payload["occurrenceCount"], 57)
        allowed = {
            "primaryVerificationStatus",
            "document",
            "ddbdpPath",
            "hgvIds",
            "surface",
            "normalizedSurface",
            "editorialFlags",
            "context",
            "dates",
            "dateBand",
            "originPlaces",
            "hgvKeywords",
            "missingHgvMetadata",
        }
        for occurrence in payload["occurrences"]:
            self.assertEqual(set(occurrence), allowed)
            self.assertFalse(occurrence["missingHgvMetadata"])

    def test_consultation_log_binds_inventory_and_disclosure(self):
        log_path = (
            MODULE.ROOT
            / "source"
            / "greek"
            / "documentary-koine"
            / "CONSULTATIONS.json"
        )
        payload = json.loads(log_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["schema"], "lpf-ddbdp-consultation-log-v1")
        ids = [row["consultationId"] for row in payload["consultations"]]
        self.assertEqual(len(ids), len(set(ids)))
        required = {
            "consultationId",
            "date",
            "performedBy",
            "purpose",
            "queryScope",
            "primarySource",
            "method",
            "resultArtifact",
            "resultSha256",
            "resultSummary",
            "dossier",
            "modelExposed",
            "canonicalPacketChanged",
            "humanAdjudication",
        }
        for row in payload["consultations"]:
            self.assertEqual(set(row), required)
            artifact = MODULE.ROOT / row["resultArtifact"]
            self.assertTrue(artifact.is_file())
            self.assertEqual(MODULE.sha256(artifact), row["resultSha256"])
            self.assertIsInstance(row["modelExposed"], bool)
            self.assertIsInstance(row["canonicalPacketChanged"], bool)

    def test_diatheke_candidate_inventory_preserves_scope_and_dates(self):
        base = MODULE.ROOT / "source/greek/documentary-koine"
        manifest = MODULE.load_manifest(base / "DIATHEKE_QUERY_MANIFEST.json")
        self.assertEqual(manifest["targetNormalizedPrefixes"], ["διαθηκ"])
        self.assertEqual(manifest["selection"]["resultCount"], 12)
        payload = json.loads(
            (base / "inventories/diatheke-family.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            payload["completeness"],
            "controlled-candidate-set-not-full-corpus-concordance",
        )
        self.assertEqual(payload["occurrenceCount"], 45)
        self.assertEqual(
            payload["countsByDateBand"],
            {
                "diachronic-comparison": 28,
                "near-contemporary-100-bce-to-200-ce": 17,
            },
        )
        self.assertTrue(all(not row["missingHgvMetadata"] for row in payload["occurrences"]))

    def test_turning_inventory_is_full_and_preserves_date_limits(self):
        base = MODULE.ROOT / "source/greek/documentary-koine"
        manifest = MODULE.load_manifest(base / "TURNING_QUERY_MANIFEST.json")
        payload = json.loads(
            (base / "inventories/turning-family.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["status"], "authorized-human-lexical-research-only")
        self.assertEqual(payload["completeness"], "full-pinned-DDbDP-normalized-concordance")
        self.assertEqual(payload["ddbdpXmlCount"], 67981)
        self.assertEqual(payload["occurrenceCount"], 131)
        self.assertEqual(payload["countsByDateBand"]["overlaps-first-century-ce"], 3)
        overlap = [
            row for row in payload["occurrences"]
            if row["dateBand"] == "overlaps-first-century-ce"
        ]
        self.assertTrue(all(row["dates"][0]["notBeforeYear"] == 98 for row in overlap))
        self.assertTrue(all(row["dates"][0]["notAfterYear"] == 117 for row in overlap))

    def test_destination_inventory_is_full_bounded_negative_result(self):
        base = MODULE.ROOT / "source/greek/documentary-koine"
        manifest = MODULE.load_manifest(base / "DESTINATION_QUERY_MANIFEST.json")
        payload = json.loads(
            (base / "inventories/destination-family.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["status"], "authorized-human-lexical-research-only")
        self.assertEqual(payload["completeness"], "full-pinned-DDbDP-normalized-concordance")
        self.assertEqual(payload["ddbdpXmlCount"], 67981)
        self.assertEqual(payload["occurrenceCount"], 0)
        self.assertEqual(payload["countsByDateBand"], {})
        self.assertEqual(
            set(payload["targetExactForms"]),
            {MODULE.exact_greek(value) for value in manifest["targetExactForms"]},
        )

    def test_psyche_inventory_uses_exact_inflectional_forms(self):
        base = MODULE.ROOT / "source/greek/documentary-koine"
        manifest = MODULE.load_manifest(base / "PSYCHE_QUERY_MANIFEST.json")
        payload = json.loads(
            (base / "inventories/psyche-family.json").read_text(encoding="utf-8")
        )
        self.assertEqual(payload["completeness"], "full-pinned-DDbDP-normalized-concordance")
        self.assertEqual(payload["ddbdpXmlCount"], 67981)
        self.assertEqual(payload["occurrenceCount"], 284)
        self.assertEqual(payload["countsByDateBand"]["exact-first-century-ce"], 2)
        self.assertEqual(payload["countsByDateBand"]["overlaps-first-century-ce"], 5)
        self.assertEqual(payload["countsByDateBand"]["near-contemporary-100-bce-to-200-ce"], 7)
        self.assertEqual(
            set(payload["targetNormalizedForms"]),
            {MODULE.normalized_greek(value) for value in manifest["targetNormalizedForms"]},
        )
        allowed = set(payload["targetNormalizedForms"])
        self.assertTrue(all(row["normalizedSurface"] in allowed for row in payload["occurrences"]))

    def test_salvation_inventory_uses_exact_forms_and_keeps_homographs_visible(self):
        base = MODULE.ROOT / "source/greek/documentary-koine"
        manifest = MODULE.load_manifest(base / "SALVATION_QUERY_MANIFEST.json")
        payload = json.loads(
            (base / "inventories/salvation-family.json").read_text(encoding="utf-8")
        )
        self.assertEqual(payload["completeness"], "full-pinned-DDbDP-normalized-concordance")
        self.assertEqual(payload["ddbdpXmlCount"], 67981)
        self.assertEqual(payload["occurrenceCount"], 1154)
        self.assertEqual(payload["countsByDateBand"]["exact-first-century-ce"], 121)
        self.assertEqual(payload["countsByDateBand"]["overlaps-first-century-ce"], 27)
        self.assertEqual(payload["countsByDateBand"]["near-contemporary-100-bce-to-200-ce"], 283)
        allowed = {
            MODULE.normalized_greek(value)
            for value in manifest["targetNormalizedForms"]
        }
        self.assertEqual(set(payload["targetNormalizedForms"]), allowed)
        self.assertTrue(all(
            row["normalizedSurface"] in allowed for row in payload["occurrences"]
        ))
        self.assertTrue(any(
            row["surface"] == "Σωσᾶς" for row in payload["occurrences"]
        ))

    def test_worship_inventory_uses_exact_scrivener_robinson_forms(self):
        base = MODULE.ROOT / "source/greek/documentary-koine"
        manifest = MODULE.load_manifest(base / "WORSHIP_QUERY_MANIFEST.json")
        payload = json.loads(
            (base / "inventories/worship-families.json").read_text(encoding="utf-8")
        )
        self.assertEqual(payload["completeness"], "full-pinned-DDbDP-normalized-concordance")
        self.assertEqual(payload["occurrenceCount"], 196)
        self.assertEqual(payload["countsByDateBand"]["near-contemporary-100-bce-to-200-ce"], 28)
        allowed = {
            MODULE.normalized_greek(value)
            for value in manifest["targetNormalizedForms"]
        }
        self.assertEqual(set(payload["targetNormalizedForms"]), allowed)
        self.assertTrue(all(
            row["normalizedSurface"] in allowed for row in payload["occurrences"]
        ))

    def test_church_inventory_preserves_assembly_controls(self):
        base = MODULE.ROOT / "source/greek/documentary-koine"
        manifest = MODULE.load_manifest(base / "CHURCH_QUERY_MANIFEST.json")
        payload = json.loads(
            (base / "inventories/church-assembly-families.json").read_text("utf-8")
        )
        self.assertEqual(payload["occurrenceCount"], 971)
        self.assertEqual(payload["countsByDateBand"]["near-contemporary-100-bce-to-200-ce"], 14)
        allowed = {MODULE.normalized_greek(x) for x in manifest["targetNormalizedForms"]}
        self.assertEqual(set(payload["targetNormalizedForms"]), allowed)
        self.assertTrue(all(x["normalizedSurface"] in allowed for x in payload["occurrences"]))

    def test_baptism_inventory_is_exact_form_and_date_bounded(self):
        base = MODULE.ROOT / "source/greek/documentary-koine"
        manifest = MODULE.load_manifest(base / "BAPTISM_QUERY_MANIFEST.json")
        payload = json.loads(
            (base / "inventories/baptism-washing-families.json").read_text("utf-8")
        )
        self.assertEqual(payload["occurrenceCount"], 82)
        self.assertEqual(
            payload["countsByDateBand"],
            {
                "diachronic-comparison": 81,
                "near-contemporary-100-bce-to-200-ce": 1,
            },
        )
        allowed = {
            MODULE.normalized_greek(value)
            for value in manifest["targetNormalizedForms"]
        }
        self.assertEqual(set(payload["targetNormalizedForms"]), allowed)
        self.assertTrue(all(
            row["normalizedSurface"] in allowed for row in payload["occurrences"]
        ))

    def test_apostle_inventory_uses_only_canonical_exact_forms(self):
        base = MODULE.ROOT / "source/greek/documentary-koine"
        manifest = MODULE.load_manifest(base / "APOSTLE_QUERY_MANIFEST.json")
        payload = json.loads(
            (base / "inventories/apostle-family.json").read_text("utf-8")
        )
        self.assertEqual(payload["occurrenceCount"], 152)
        self.assertEqual(
            payload["countsByDateBand"]["near-contemporary-100-bce-to-200-ce"],
            13,
        )
        allowed = {
            MODULE.normalized_greek(value)
            for value in manifest["targetNormalizedForms"]
        }
        self.assertEqual(set(payload["targetNormalizedForms"]), allowed)
        self.assertTrue(all(
            row["normalizedSurface"] in allowed for row in payload["occurrences"]
        ))

    def test_date_bands_preserve_open_range_uncertainty(self):
        self.assertEqual(
            MODULE.classify_dates(
                [
                    {
                        "notBeforeYear": None,
                        "notAfterYear": 139,
                    }
                ]
            ),
            "indeterminate-open-range-may-overlap-first-century-ce",
        )
        self.assertEqual(
            MODULE.classify_dates(
                [
                    {
                        "notBeforeYear": 542,
                        "notAfterYear": None,
                    }
                ]
            ),
            "diachronic-comparison",
        )
        self.assertEqual(
            MODULE.classify_dates(
                [
                    {
                        "notBeforeYear": 25,
                        "notAfterYear": 75,
                    }
                ]
            ),
            "exact-first-century-ce",
        )

    def test_epidoc_no_break_and_editorial_flags(self):
        xml = """\
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader><fileDesc><titleStmt><title>sample</title></titleStmt></fileDesc></teiHeader>
  <text><body><div type="edition"><ab>
    <lb n="1"/>οὐ <choice><reg>με</reg><orig>μαι</orig></choice><supplied reason="lost">τ</supplied>α
    <lb n="2" break="no"/>νοήσει, ἀμετανοήτως.
  </ab></div></body></text>
</TEI>"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.xml"
            path.write_text(xml, encoding="utf-8")
            text, flags, _ = MODULE.canonical_edition(path)
        tokens = []
        for match in MODULE.GREEK_WORD.finditer(text):
            normalized = MODULE.normalized_greek(match.group())
            if normalized.startswith("μετανο"):
                token_flags = sorted(set().union(*flags[match.start() : match.end()]))
                tokens.append((match.group(), token_flags))
        self.assertEqual(tokens, [("μετανοήσει", ["supplied"])])

    def test_cache_validation_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "DDbDP").mkdir()
            (root / "HGV_meta_EpiDoc").mkdir()
            (root / "DDbDP" / "one.xml").write_text("<x/>", encoding="utf-8")
            ddb_count, ddb_hash = MODULE.aggregate_xml(root, "DDbDP")
            hgv_count, hgv_hash = MODULE.aggregate_xml(root, "HGV_meta_EpiDoc")
            manifest = {
                "localEvaluationCache": {
                    "ddbdp": {
                        "xmlCount": ddb_count,
                        "aggregateSha256": ddb_hash,
                    },
                    "hgvMetadata": {
                        "xmlCount": hgv_count,
                        "aggregateSha256": hgv_hash,
                    },
                }
            }
            MODULE.validate_cache(root, manifest)
            (root / "DDbDP" / "one.xml").write_text("<changed/>", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "cache mismatch"):
                MODULE.validate_cache(root, manifest)


if __name__ == "__main__":
    unittest.main()
