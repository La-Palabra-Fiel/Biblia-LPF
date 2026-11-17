from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("papyri_lexical_inventory.py")
SPEC = importlib.util.spec_from_file_location("papyri_lexical_inventory", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class PapyriLexicalInventoryTests(unittest.TestCase):
    def test_date_bands_do_not_conflate_overlap_with_exact_century(self) -> None:
        self.assertEqual(
            MODULE.classify_date(1, 1), "exact-first-century-ce"
        )
        self.assertEqual(
            MODULE.classify_date(1, 2), "overlaps-first-century-ce"
        )
        self.assertEqual(
            MODULE.classify_date(-1, -1),
            "near-contemporary-100-bce-to-200-ce",
        )
        self.assertEqual(
            MODULE.classify_date(2, 2),
            "near-contemporary-100-bce-to-200-ce",
        )
        self.assertEqual(
            MODULE.classify_date(4, 4), "diachronic-comparison"
        )
        self.assertEqual(MODULE.classify_date(0, 0), "undated")
        with self.assertRaisesRegex(ValueError, "invalid documentary period"):
            MODULE.classify_date(2, 1)

    def test_manifest_validation_fails_closed_on_changed_xml(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            corpus = Path(directory)
            xml_dir = corpus / "xml"
            xml_dir.mkdir()
            source = xml_dir / "fixture.xml"
            source.write_text("<treebank/>", encoding="utf-8")
            manifest = {
                "files": [
                    {
                        "path": "xml/fixture.xml",
                        "sha256": "0" * 64,
                    }
                ]
            }
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                MODULE.validate_corpus(corpus, manifest)

    def test_collects_each_matching_token_and_rejects_semantic_labels(self) -> None:
        xml = """<treebank>
          <sentence id="1" document_id="42" filename="p.test.1"
                    period_min="1" period_max="1" genre="letter" place="Egypt">
            <word id="1" wordid="a" row="1" regularized="εἰ" form="εἰ"
                  completeness="complete" lemma="εἰ" postag="c--------"/>
            <word id="2" wordid="b" row="1" regularized="μετανοεῖς"
                  form="μετανοεῖς" completeness="complete" lemma="μετανοέω"
                  postag="v2spia---" head="1" relation="ADV"
                  semanticRole="cause"/>
            <word id="3" wordid="c" row="1" regularized="μετάνοια"
                  form="μετάνοια" completeness="complete" lemma="μετάνοια"
                  postag="n-s---fn-"/>
          </sentence>
        </treebank>"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.xml"
            path.write_text(xml, encoding="utf-8")
            rows = MODULE.collect_occurrences(
                [path], {"μετανοέω", "μετάνοια"}
            )
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["dateBand"], "exact-first-century-ce")
        self.assertEqual(rows[0]["primaryVerificationStatus"], "pending")
        self.assertNotIn("head", rows[0])
        self.assertNotIn("relation", rows[0])
        self.assertNotIn("semanticRole", rows[0])
        self.assertEqual(
            rows[0]["regularizedSentence"], "εἰ μετανοεῖς μετάνοια"
        )


if __name__ == "__main__":
    unittest.main()

