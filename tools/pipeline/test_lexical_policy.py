import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lexical_policy


class LexicalPolicyTests(unittest.TestCase):
    def setUp(self):
        lexical_policy.load_policy.cache_clear()

    def test_registry_is_closed_and_review_notes_exist(self):
        policy = lexical_policy.load_policy()
        self.assertEqual(policy["schema"], "lpf-lexical-policy-v1")
        self.assertEqual(policy["authority"], "named-human-editorial-policy")
        self.assertEqual(len(policy["entries"]), 36)

    def test_diatheke_options_and_reference_rule_match_hebrews(self):
        tokens = [
            {"strongsAll": ["G1242"]},
            {"strongsAll": ["G1303"]},
        ]
        model, review = lexical_policy.policies_for_verse("nt", "HEB.9.16", tokens)
        by_id = {entry["id"]: entry for entry in model}
        self.assertEqual(set(by_id), {"nt-diatheke", "nt-diatithemai"})
        self.assertEqual(
            by_id["nt-diatheke"]["activeReferenceRules"][0]["preferred"],
            ["testamento"],
        )
        self.assertTrue(all("researchNote" not in entry for entry in model))
        self.assertEqual(
            {entry["researchNote"] for entry in review},
            {"notes/research/pacto-testamento.md"},
        )

    def test_jesus_christ_requires_adjacent_ordered_tokens(self):
        forward, _ = lexical_policy.policies_for_verse(
            "nt", "PHP.1.2", [{"strongsAll": ["G2424"]}, {"strongsAll": ["G5547"]}]
        )
        separated, _ = lexical_policy.policies_for_verse(
            "nt", "PHP.1.2", [
                {"strongsAll": ["G2424"]},
                {"strongsAll": ["G2532"]},
                {"strongsAll": ["G5547"]},
            ]
        )
        self.assertEqual([entry["id"] for entry in forward], ["nt-jesus-christ-order"])
        self.assertNotIn("nt-jesus-christ-order", [entry["id"] for entry in separated])

    def test_turning_families_keep_conversion_contextual(self):
        model, review = lexical_policy.policies_for_verse(
            "nt", "ACT.15.3", [{"strongsAll": ["G1995"]}]
        )
        self.assertEqual([entry["id"] for entry in model], ["nt-epistrophe"])
        self.assertEqual(
            model[0]["activeReferenceRules"][0]["preferred"],
            ["la conversión de las naciones"],
        )
        self.assertIn("conversión", [option["form"] for option in model[0]["spanishOptions"]])
        self.assertEqual(review[0]["researchNote"], "notes/research/conversion.md")

    def test_epistrepho_does_not_merge_with_faith(self):
        model, _ = lexical_policy.policies_for_verse(
            "nt", "ACT.11.21", [
                {"strongsAll": ["G4100"]},
                {"strongsAll": ["G1994"]},
            ]
        )
        policy = next(entry for entry in model if entry["id"] == "nt-epistrepho")
        self.assertIn("using convertirse as a synonym for creer or fe", policy["avoid"])

    def test_destination_terms_remain_distinct_and_forbid_infierno(self):
        cases = [
            ("ot", "PSA.16.10", "H7585", "ot-sheol", ["Seol"]),
            ("nt", "REV.20.14", "G86", "nt-hades", ["Hades"]),
            ("nt", "MAT.5.22", "G1067", "nt-gehenna", ["Gehena"]),
            (
                "nt", "2PE.2.4", "G5020", "nt-tartaroo",
                ["arrojar al Tártaro", "confinar en el Tártaro"],
            ),
        ]
        for testament, reference, strongs, policy_id, expected_options in cases:
            with self.subTest(policy_id=policy_id):
                model, review = lexical_policy.policies_for_verse(
                    testament, reference, [{"strongsAll": [strongs]}]
                )
                policy = next(entry for entry in model if entry["id"] == policy_id)
                self.assertEqual(
                    [option["form"] for option in policy["spanishOptions"]],
                    expected_options,
                )
                self.assertIn("infierno as the aligned translation", policy["avoid"])
                self.assertEqual(review[0]["researchNote"], "notes/research/infierno.md")

        tartaroo, _ = lexical_policy.policies_for_verse(
            "nt", "2PE.2.4", [{"strongsAll": ["G5020"]}]
        )
        self.assertEqual(
            tartaroo[0]["activeReferenceRules"][0]["strength"], "binding"
        )

    def test_nephesh_and_psyche_offer_contextual_not_automatic_options(self):
        ot_model, ot_review = lexical_policy.policies_for_verse(
            "ot", "Gen.2.7", [{"strongsAll": ["H5315"]}]
        )
        nt_model, nt_review = lexical_policy.policies_for_verse(
            "nt", "MAT.10.28", [{"strongsAll": ["G5590"]}]
        )
        self.assertEqual([entry["id"] for entry in ot_model], ["ot-nephesh"])
        self.assertEqual([entry["id"] for entry in nt_model], ["nt-psyche"])
        self.assertEqual(
            [option["form"] for option in ot_model[0]["spanishOptions"]],
            [
                "ser viviente/criatura viviente",
                "persona/individuo",
                "vida",
                "alma",
                "ánimo/ser/yo/deseo",
            ],
        )
        self.assertEqual(
            [option["form"] for option in nt_model[0]["spanishOptions"]],
            [
                "alma",
                "vida",
                "persona/individuo",
                "ser viviente/criatura viviente",
                "ánimo/ser/yo/deseo",
            ],
        )
        self.assertIn("using alma as an automatic gloss", ot_model[0]["avoid"])
        self.assertIn("using alma as an automatic gloss", nt_model[0]["avoid"])
        self.assertEqual(ot_review[0]["researchNote"], "notes/research/alma.md")
        self.assertEqual(nt_review[0]["researchNote"], "notes/research/alma.md")

    def test_salvation_families_offer_contextual_options(self):
        ot_model, ot_review = lexical_policy.policies_for_verse(
            "ot", "Exod.14.13", [{"strongsAll": ["H3444"]}]
        )
        nt_model, nt_review = lexical_policy.policies_for_verse(
            "nt", "MAT.9.22", [{"strongsAll": ["G4982"]}]
        )
        title_model, title_review = lexical_policy.policies_for_verse(
            "nt", "LUK.2.11", [{"strongsAll": ["G4990"]}]
        )
        self.assertEqual([entry["id"] for entry in ot_model], ["ot-yesha-salvation-family"])
        self.assertEqual([entry["id"] for entry in nt_model], ["nt-sozo-soteria-family"])
        self.assertEqual([entry["id"] for entry in title_model], ["nt-soter-title"])
        self.assertIn(
            "using salvación or salvar as an automatic gloss",
            nt_model[0]["avoid"],
        )
        self.assertIn(
            "sanar/curar/recuperar(se)",
            [option["form"] for option in nt_model[0]["spanishOptions"]],
        )
        self.assertEqual(
            [option["form"] for option in title_model[0]["spanishOptions"]],
            ["Salvador"],
        )
        self.assertEqual(ot_review[0]["researchNote"], "notes/research/salvacion.md")
        self.assertEqual(nt_review[0]["researchNote"], "notes/research/salvacion.md")
        self.assertEqual(title_review[0]["researchNote"], "notes/research/salvacion.md")

    def test_worship_families_remain_distinct(self):
        tokens = [
            {"strongsAll": ["G4352"]},
            {"strongsAll": ["G3000"]},
        ]
        model, review = lexical_policy.policies_for_verse("nt", "MAT.4.10", tokens)
        by_id = {entry["id"]: entry for entry in model}
        self.assertEqual(set(by_id), {"nt-proskyneo", "nt-latreuo"})
        self.assertIn("adorar", [x["form"] for x in by_id["nt-proskyneo"]["spanishOptions"]])
        self.assertNotIn("adorar", [x["form"] for x in by_id["nt-latreuo"]["spanishOptions"]])
        self.assertEqual(
            {entry["researchNote"] for entry in review},
            {"notes/research/adoracion.md"},
        )

        human_bow, _ = lexical_policy.policies_for_verse(
            "ot", "Gen.23.7", [{"strongsAll": ["H7812"]}]
        )
        self.assertEqual(human_bow[0]["id"], "ot-bowing-worship-families")
        self.assertIn("using adorar as an automatic gloss", human_bow[0]["avoid"])

    def test_ekklesia_distinguishes_assembly_congregation_and_church(self):
        model, review = lexical_policy.policies_for_verse(
            "nt", "ACT.19.39", [{"strongsAll": ["G1577"]}]
        )
        self.assertEqual([entry["id"] for entry in model], ["nt-ekklesia"])
        self.assertEqual(
            [option["form"] for option in model[0]["spanishOptions"]],
            ["asamblea", "congregación", "iglesia"],
        )
        self.assertEqual(model[0]["activeReferenceRules"][0]["preferred"], ["asamblea"])
        self.assertEqual(model[0]["activeReferenceRules"][0]["strength"], "binding")
        self.assertIn(
            "using comunidad where it can suggest the town or surrounding population",
            model[0]["avoid"],
        )
        self.assertEqual(review[0]["researchNote"], "notes/research/iglesia.md")

    def test_baptism_families_preserve_rite_washing_and_action_distinctions(self):
        model, review = lexical_policy.policies_for_verse(
            "nt",
            "MRK.7.4",
            [
                {"strongsAll": ["G907"]},
                {"strongsAll": ["G909"]},
                {"strongsAll": ["G911"]},
            ],
        )
        by_id = {entry["id"]: entry for entry in model}
        self.assertEqual(set(by_id), {"nt-baptizo", "nt-baptismos", "nt-bapto"})
        self.assertEqual(
            by_id["nt-baptizo"]["activeReferenceRules"][0]["preferred"],
            ["lavar/lavarse"],
        )
        self.assertEqual(
            by_id["nt-baptizo"]["activeReferenceRules"][0]["strength"],
            "binding",
        )
        self.assertNotIn(
            "bautismo",
            [option["form"] for option in by_id["nt-baptismos"]["spanishOptions"]],
        )
        self.assertEqual(
            {entry["researchNote"] for entry in review},
            {"notes/research/bautismo.md"},
        )

    def test_baptist_title_is_binding_but_does_not_control_cognates(self):
        model, _ = lexical_policy.policies_for_verse(
            "nt", "MAT.3.1", [{"strongsAll": ["G910"]}]
        )
        self.assertEqual([entry["id"] for entry in model], ["nt-baptistes"])
        self.assertEqual(model[0]["status"], "binding")
        self.assertEqual(
            [option["form"] for option in model[0]["spanishOptions"]],
            ["el Bautista"],
        )

    def test_baptisma_loutron_and_katharismos_remain_separate(self):
        model, _ = lexical_policy.policies_for_verse(
            "nt",
            "TIT.3.5",
            [
                {"strongsAll": ["G908"]},
                {"strongsAll": ["G3067"]},
                {"strongsAll": ["G2512"]},
            ],
        )
        by_id = {entry["id"]: entry for entry in model}
        self.assertEqual(
            set(by_id),
            {"nt-baptisma", "nt-loutron", "nt-katharismos"},
        )
        self.assertIn(
            "using bautismo automatically",
            by_id["nt-loutron"]["avoid"],
        )


if __name__ == "__main__":
    unittest.main()
