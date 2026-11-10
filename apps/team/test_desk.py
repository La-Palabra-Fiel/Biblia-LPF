#!/usr/bin/env python3
"""Safety tests for the named-human chapter desk. No model calls."""
from __future__ import annotations
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
import desk

class DeskTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); root=Path(self.tmp.name)
        self.old=(desk.VAR,desk.CLAIMS,desk.PEOPLE,desk.RECOVERED)
        desk.VAR=root;desk.CLAIMS=root/"claims.json";desk.PEOPLE=root/"people.json";desk.RECOVERED=root/"recovered-reviews"
        desk.PEOPLE.write_text('{"Ana":"11111111","Luis":"22222222"}\n',encoding="utf-8")
    def tearDown(self):
        desk.VAR,desk.CLAIMS,desk.PEOPLE,desk.RECOVERED=self.old;self.tmp.cleanup()
    def test_model_is_fixed_to_sol(self):
        self.assertEqual(desk.model_name(),"gpt-6.1-sol")
        self.assertEqual(desk.reasoning_effort(),"low")
        self.assertEqual(desk.board()["modelReviewOn"],"2026-11-30")
        self.assertEqual(desk.SPANISH_GATE_MODEL,"deterministic-local")
        self.assertFalse(desk.audit_required({"uncertainties":[]},{"verdict":"pass"}))
        self.assertTrue(desk.audit_required({"uncertainties":[{"issue":"open"}]},{"verdict":"pass"}))
        self.assertTrue(desk.audit_required({"uncertainties":[]},{"verdict":"fail"}))
        self.assertEqual(desk.board()["draftSpecVersion"],desk.DRAFT_SPEC_VERSION)

    def test_current_and_historical_paid_models_are_compatible(self):
        packet={"sourcePolicy":"lbf-source-policy-v4","tokens":[]}
        common={"reasoningEffort":"low","packetSha256":desk.packet_fingerprint(packet),"draftSpecVersion":desk.DRAFT_SPEC_VERSION}
        self.assertTrue(desk.compatible_paid_draft({**common,"model":"gpt-6.1-sol"},packet))
        self.assertTrue(desk.compatible_paid_draft({**common,"model":"gpt-5.6-sol"},packet))
        self.assertFalse(desk.compatible_paid_draft({**common,"model":"gpt-5.5-sol"},packet))
    def test_divine_name_is_locked(self):
        packet={"tokens":[{"sourceTokenId":"h1","lemma":"c/3068"}]}
        self.assertEqual(desk.lint_divine_name("Y dijo Yahvé",packet),[])
        self.assertTrue(desk.lint_divine_name("Y dijo el SEÑOR",packet))
        self.assertTrue(desk.lint_spanish("Y dijo Jehová"))
        self.assertTrue(desk.lint_spanish("el faraón dijo"))
        self.assertEqual(desk.lint_spanish("Faraón dijo"),[])
    def test_supplied_word_markup_is_well_formed(self):
        self.assertEqual(desk.lint_spanish("Yo *soy* Yahvé"),[])
        self.assertTrue(desk.lint_spanish("Yo *soy Yahvé"))
        self.assertTrue(desk.lint_spanish("Yo **soy** Yahvé"))
        self.assertTrue(desk.lint_spanish("Él, Aarón y Moisés, a quienes Yahvé dijo."))
        self.assertEqual(desk.lint_spanish("Estos *son* Aarón y Moisés."),[])
    def test_para_que_viva_is_not_a_global_spanish_error(self):
        spanish="Trata con generosidad a Tu siervo, para que viva y guarde Tu palabra."
        packet={"tokens":[
            {"sourceTokenId":"h19119017004","lemma":"2421","morph":"HVqh1cs","morphExpanded":"Hebrew; qal cohortative 1st common singular"},
            {"sourceTokenId":"h19119017005","lemma":"c/8104","morph":"HC/Vqh1cs"},
        ]}
        self.assertEqual(desk.lint_spanish(spanish),[])
        self.assertEqual(desk.lint_spanish(spanish,packet),[])
    def test_exodus_life_rule_is_bound_to_its_source(self):
        packet={"tokens":[{"sourceTokenId":"h02001016016","lemma":"c/2425","morph":"HC/Vqq3fs"}]}
        findings=desk.lint_spanish("Si ella es hija, que viva.",packet)
        self.assertEqual(len(findings),1)
        self.assertEqual(findings[0]["sourceTokenIds"],["h02001016016"])
        self.assertEqual(desk.lint_spanish("Si ella es hija, vivirá.",packet),[])
        other={"tokens":[{"sourceTokenId":"other","lemma":"2421","morph":"HVqj3ms"}]}
        self.assertEqual(desk.lint_spanish("Que viva.",other),[])
    def test_gate_rechecks_cached_local_lint_without_erasing_audit(self):
        root=Path(self.tmp.name); path=root/"draft.json"; packet_file=root/"packet.json"
        candidate={"label":"team-gpt","spanish":"Trata con generosidad a Tu siervo, para que viva y guarde Tu palabra.","units":[]}
        packet={"tokens":[{"sourceTokenId":"h19119017004","lemma":"2421","morph":"HVqh1cs"}]}
        desk.write_json(path,candidate);desk.write_json(packet_file,packet)
        historical={"model":"deterministic-local","candidateSha256":desk.object_fingerprint(candidate),"verdict":"fail","findings":[{"issue":"jussive que viva; qal is vivirá"}]}
        check_path=root/"salmos-119-17.spanish-check-team-gpt.json"
        desk.write_json(check_path,historical)
        with patch.object(desk,"pipeline_dir",return_value=root),patch.object(desk,"packet_path",return_value=packet_file):
            gate=desk.gate_for("salmos",119,17,path,candidate)
            self.assertEqual(gate["spanish"],"pass")
            self.assertEqual(gate["spanishFindings"],[])
            self.assertFalse(gate["auditRequired"])
            self.assertEqual(desk.read_json(check_path),historical)
            audit={"model":"independent-auditor","candidateSha256":desk.object_fingerprint(candidate),"verdict":"fail","findings":[{"issue":"Needs human fidelity review"}]}
            desk.write_json(root/"salmos-119-17.audit-gpt-team-gpt.json",audit)
            gate=desk.gate_for("salmos",119,17,path,candidate)
            self.assertEqual(gate["fidelity"],"fail")
            self.assertEqual(gate["fidelityFindings"],audit["findings"])
    def test_claim_is_per_chapter(self):
        with patch.object(desk,"chapter_or_raise",side_effect=lambda s,c:(type("B",(),{"slug":s,"label":"Éxodo"})(),int(c),[1])):
            desk.claim("Ana","exodo",3,"11111111");desk.claim("Luis","exodo",4,"22222222")
            with self.assertRaises(ValueError):desk.claim("Luis","exodo",3,"22222222")
            self.assertIn("exodo:3",desk.load_claims());self.assertIn("exodo:4",desk.load_claims())
    def test_nt_is_blocked(self):
        with self.assertRaises(ValueError):desk.book_or_raise("mateo")
    def test_nt_syntax_pilot_is_review_only_and_does_not_unblock_translation(self):
        board=desk.nt_syntax_board()
        self.assertFalse(board["translationEnabled"])
        self.assertFalse(board["approvalEnabled"])
        self.assertEqual(board["mappingPolicy"],desk.NT_MACULA_MAPPING_POLICY)
        self.assertEqual([(row["book"],row["chapter"]) for row in board["candidates"]],[('filipenses',1)])
        view=desk.nt_syntax_view("filipenses",1)
        self.assertEqual(view["status"],"review-only-not-canonical")
        self.assertEqual(len(view["verses"]),30)
        self.assertEqual(sum(len(row["tokens"]) for row in view["verses"]),499)
        self.assertEqual(sum(token["tripleAgreement"] for row in view["verses"] for token in row["tokens"]),459)
        first=view["verses"][0]
        self.assertEqual(first["status"],"human-adjudicated-tr")
        resolved=[token for token in first["tokens"] if token["structurallyResolved"]]
        self.assertEqual([token["tokenId"] for token in resolved],["PHP.1.1.w005","PHP.1.1.w006"])
        self.assertTrue(all(token["structureDecisionId"]=="PHP.1.1.jesus-christ-order" for token in resolved))
        sixth=view["verses"][5]
        self.assertEqual(sixth["status"],"human-adjudicated-tr")
        resolved=[token for token in sixth["tokens"] if token["structurallyResolved"]]
        self.assertEqual([token["tokenId"] for token in resolved],["PHP.1.6.w012","PHP.1.6.w014","PHP.1.6.w015"])
        with self.assertRaisesRegex(ValueError,"No review-only structural candidate"):
            desk.nt_syntax_view("mateo",1)
    def test_alignment_requires_complete_token_coverage(self):
        packet={"tokens":[{"sourceTokenId":"h1"},{"sourceTokenId":"h2"}]}
        with self.assertRaises(ValueError):desk.validate_units(packet,[{"es":"Uno","sourceTokenIds":["h1"]}])
        self.assertEqual(len(desk.validate_units(packet,[{"es":"Uno","sourceTokenIds":["h1"]},{"es":"dos","sourceTokenIds":["h2"]}],"Uno, dos.")),2)
        with self.assertRaises(ValueError):desk.validate_units(packet,[{"es":"Uno","sourceTokenIds":["h1"]},{"es":"tres","sourceTokenIds":["h2"]}],"Uno, dos.")
    def test_alignment_preflight_reports_direct_object_marker_before_approval(self):
        packet={"tokens":[{"sourceTokenId":"h1"},{"sourceTokenId":"h2","morphExpanded":"Hebrew; direct object marker"},{"sourceTokenId":"h3"}]}
        units,findings=desk.alignment_preflight_findings(packet,[
            {"es":"extendió","sourceTokenIds":["h1"]},
            {"es":"su mano","sourceTokenIds":["h3"]},
        ],"Extendió su mano.")
        self.assertEqual([unit["es"] for unit in units],["extendió","su mano"])
        self.assertEqual(findings[-1]["code"],"missing-source-tokens")
        self.assertEqual(findings[-1]["sourceTokenIds"],["h2"])
    def test_alignment_preflight_preserves_supplied_markup_but_ignores_punctuation(self):
        packet={"tokens":[{"sourceTokenId":"h1"},{"sourceTokenId":"h2"}]}
        units=[{"es":"Yo","sourceTokenIds":["h1"]},{"es":"*soy* Yahvé","sourceTokenIds":["h2"]}]
        self.assertEqual(desk.alignment_preflight_findings(packet,units,"Yo *soy* Yahvé.")[1],[])
        wrong=[{"es":"Yo","sourceTokenIds":["h1"]},{"es":"soy Yahvé","sourceTokenIds":["h2"]}]
        findings=desk.alignment_preflight_findings(packet,wrong,"Yo *soy* Yahvé.")[1]
        self.assertEqual(findings[-1]["code"],"supplied-markup-mismatch")
        with self.assertRaisesRegex(ValueError,"Supplied-word italics differ"):
            desk.validate_units(packet,wrong,"Yo *soy* Yahvé.")
    def test_alignment_preflight_allows_legitimate_repeated_source_id(self):
        packet={"tokens":[{"sourceTokenId":"h1"},{"sourceTokenId":"h2"}]}
        units=[{"es":"Y","sourceTokenIds":["h1"]},{"es":"el rey","sourceTokenIds":["h2"]},{"es":"dijo","sourceTokenIds":["h1"]}]
        self.assertEqual(desk.alignment_preflight_findings(packet,units,"Y el rey dijo.")[1],[])
    def test_alignment_consolidates_repeated_source_ids(self):
        packet={"tokens":[{"sourceTokenId":"h1"},{"sourceTokenId":"h2"}]}
        units=desk.validate_units(packet,[
            {"es":"Y","sourceTokenIds":["h1"]},
            {"es":"dijo","sourceTokenIds":["h1"]},
            {"es":"Moisés","sourceTokenIds":["h2"]},
        ],"Y dijo Moisés.")
        self.assertEqual(units,[
            {"es":"Y dijo","sourceTokenIds":["h1"]},
            {"es":"Moisés","sourceTokenIds":["h2"]},
        ])
    def test_alignment_rejects_obviously_broad_units(self):
        packet={"tokens":[{"sourceTokenId":f"h{i}","morphExpanded":"Hebrew; noun common"} for i in range(1,6)]}
        with self.assertRaisesRegex(ValueError,"too broad"):
            desk.validate_units(packet,[{"es":"Entonces el rey mandó llamar","sourceTokenIds":["h1","h2","h3","h4","h5"]}])
        precise=[{"es":"Entonces","sourceTokenIds":["h1"]},{"es":"el rey","sourceTokenIds":["h2"]},{"es":"mandó llamar","sourceTokenIds":["h3","h4"]},{"es":"hoy","sourceTokenIds":["h5"]}]
        self.assertEqual(len(desk.validate_units(packet,precise,"Entonces el rey mandó llamar hoy.")),4)
    def test_alignment_separates_proper_names(self):
        packet={"tokens":[
            {"sourceTokenId":"h1","morphExpanded":"Hebrew; noun proper"},
            {"sourceTokenId":"h2","morphExpanded":"Hebrew; conjunction; noun proper"},
        ]}
        with self.assertRaisesRegex(ValueError,"proper names"):
            desk.validate_units(packet,[{"es":"Moisés y Aarón","sourceTokenIds":["h1","h2"]}])
        precise=[{"es":"Moisés","sourceTokenIds":["h1"]},{"es":"y Aarón","sourceTokenIds":["h2"]}]
        self.assertEqual(len(desk.validate_units(packet,precise,"Moisés y Aarón")),2)
    def test_alignment_accepts_oshb_compound_name_betel(self):
        packet={"tokens":[
            {"sourceTokenId":"h01012008005","lemma":"l/1008+","morphExpanded":"Hebrew; preposition; noun proper"},
            {"sourceTokenId":"h01012008006","lemma":"1008","morphExpanded":"Hebrew; noun proper"},
            {"sourceTokenId":"h01012008007","lemma":"c/5186","morphExpanded":"Hebrew; conjunction; verb"},
            {"sourceTokenId":"h01012008009","lemma":"1008+","morphExpanded":"Hebrew; noun proper"},
            {"sourceTokenId":"h01012008010","lemma":"1008","morphExpanded":"Hebrew; noun proper"},
        ]}
        units=[
            {"es":"de Betel","sourceTokenIds":["h01012008005","h01012008006"]},
            {"es":"y extendió","sourceTokenIds":["h01012008007"]},
            {"es":"con Betel","sourceTokenIds":["h01012008009","h01012008010"]},
        ]
        self.assertEqual(desk.alignment_preflight_findings(packet,units)[1],[])
        self.assertEqual(desk.validate_units(packet,units),units)
        with self.assertRaisesRegex(ValueError,"proper names"):
            desk.validate_units(packet,[{"es":"Betel y Betel","sourceTokenIds":[t["sourceTokenId"] for t in packet["tokens"] if "noun proper" in t["morphExpanded"]]}])
    def test_compound_name_does_not_absorb_an_independent_name(self):
        packet={"tokens":[
            {"sourceTokenId":"h1","lemma":"1008+","morphExpanded":"Hebrew; noun proper"},
            {"sourceTokenId":"h2","lemma":"1008","morphExpanded":"Hebrew; noun proper"},
            {"sourceTokenId":"h3","lemma":"c/d/5857","morphExpanded":"Hebrew; conjunction; noun proper"},
        ]}
        with self.assertRaisesRegex(ValueError,"proper names"):
            desk.validate_units(packet,[{"es":"Betel y Hai","sourceTokenIds":["h1","h2","h3"]}])
    def test_repeated_unmarked_lemmas_are_independent_names(self):
        packet={"tokens":[
            {"sourceTokenId":"h1","lemma":"1008","morphExpanded":"Hebrew; noun proper"},
            {"sourceTokenId":"h2","lemma":"1008","morphExpanded":"Hebrew; noun proper"},
        ]}
        with self.assertRaisesRegex(ValueError,"proper names"):
            desk.validate_units(packet,[{"es":"Betel Betel","sourceTokenIds":["h1","h2"]}])
    def test_compound_continuation_must_be_adjacent_and_match(self):
        for second in (
            {"sourceTokenId":"h2","lemma":"5857","morphExpanded":"Hebrew; noun proper"},
            {"sourceTokenId":"h2","lemma":"c/1008","morphExpanded":"Hebrew; conjunction; noun proper"},
        ):
            with self.subTest(second=second):
                packet={"tokens":[{"sourceTokenId":"h1","lemma":"1008+","morphExpanded":"Hebrew; noun proper"},second]}
                self.assertTrue(desk.alignment_precision_findings(packet,[{"es":"Dos nombres","sourceTokenIds":["h1","h2"]}]))
        packet={"tokens":[
            {"sourceTokenId":"h1","lemma":"1008+","morphExpanded":"Hebrew; noun proper"},
            {"sourceTokenId":"verb","lemma":"5186","morphExpanded":"Hebrew; verb"},
            {"sourceTokenId":"h2","lemma":"1008","morphExpanded":"Hebrew; noun proper"},
        ]}
        self.assertTrue(desk.alignment_precision_findings(packet,[{"es":"Dos nombres","sourceTokenIds":["h1","h2"]}]))
    def test_verse_scanner(self):
        text="# Éxodo\n\n## Capítulo 3\n\n### 3:1\n\nTexto.\n\n### 3:2\n\n"
        self.assertEqual(desk.verse_body(text,3,1),"Texto.");self.assertEqual(desk.verse_body(text,3,2),"");self.assertIsNone(desk.verse_body(text,3,9))
    def test_recovered_review_is_noncanonical_app_state(self):
        self.assertEqual(desk.recovered_path("exodo",3),desk.RECOVERED/"exodo-3.json")
    def test_failed_review_attempt_can_be_recovered_before_validation(self):
        book=type("B",(),{"slug":"exodo"})()
        payload={"spanish":"Texto revisado","units":[{"es":"Texto revisado","sourceTokenIds":["h1"]}],"unitsComplete":True,"decision":"","sourceConfirmed":True,"alignmentConfirmed":True,"suppliedConfirmed":True,"auditOverrideConfirmed":True}
        desk.save_review_attempt(book,3,1,"Ana",payload)
        saved=desk.read_json(desk.recovered_path("exodo",3),{})["verses"]["1"]
        self.assertEqual(saved["spanish"],"Texto revisado")
        self.assertEqual(saved["lastAttemptedBy"],"Ana")
        self.assertTrue(saved["suppliedConfirmed"])
        self.assertTrue(saved["auditOverrideConfirmed"])
        self.assertTrue(saved["unitsComplete"])
    def test_current_human_review_must_match_canonical_spanish(self):
        root=Path(self.tmp.name); human=root/"human.json"; translation=root/"exodo.md"
        translation.write_text("# Éxodo\n\n## Capítulo 6\n\n### 6:26\n\nEstos *son* Aarón y Moisés.\n",encoding="utf-8")
        human.write_text('{"schema":"lbf-human-reviewed-candidate-v1","spanish":"Estos *son* Aarón y Moisés.","adjudication":{"humanApprovedInTeamDesk":true}}\n',encoding="utf-8")
        with patch.object(desk,"human_path",return_value=human),patch.object(desk,"translation_file",return_value=translation):
            self.assertTrue(desk.human_review_is_current("exodo",6,26))
            translation.write_text("# Éxodo\n\n## Capítulo 6\n\n### 6:26\n\nTexto cambiado.\n",encoding="utf-8")
            self.assertFalse(desk.human_review_is_current("exodo",6,26))
    def test_existing_human_review_is_grandfathered_across_packet_changes(self):
        root=Path(self.tmp.name); human=root/"human.json"; translation=root/"exodo.md"
        translation.write_text("# Éxodo\n\n## Capítulo 1\n\n### 1:1\n\nTexto aprobado.\n",encoding="utf-8")
        human.write_text('{"schema":"lbf-human-reviewed-candidate-v1","packetSha256":"old","spanish":"Texto aprobado.","adjudication":{"humanApprovedInTeamDesk":true}}\n',encoding="utf-8")
        with patch.object(desk,"human_path",return_value=human),patch.object(desk,"translation_file",return_value=translation):
            self.assertTrue(desk.human_review_is_current("exodo",1,1))
    def test_chapter_review_is_current_only_with_all_bound_verses(self):
        root=Path(self.tmp.name);manifest=root/"exodo-16.human-review.json"
        desk.write_json(manifest,{"schema":"lbf-human-chapter-review-v1","continuityVoiceFlowConfirmed":True,"verseWordingConfirmed":[1,2],"alignmentSeedsConfirmed":[1,2]})
        with patch.object(desk,"pipeline_dir",return_value=root),patch.object(desk,"human_review_is_current",return_value=True),patch.object(desk,"revision_is_open",return_value=False):
            self.assertTrue(desk.chapter_review_is_current("exodo",16,[1,2]))
            self.assertFalse(desk.chapter_review_is_current("exodo",16,[1,2,3]))
        with patch.object(desk,"pipeline_dir",return_value=root),patch.object(desk,"human_review_is_current",return_value=True),patch.object(desk,"revision_is_open",side_effect=lambda s,c,v:v==2):
            self.assertFalse(desk.chapter_review_is_current("exodo",16,[1,2]))
    def test_reopen_verse_seeds_a_local_revision_without_model_call(self):
        root=Path(self.tmp.name);human=root/"human.json"
        artifact={"schema":"lbf-human-reviewed-candidate-v1","spanish":"Texto aprobado.","units":[{"es":"Texto aprobado","sourceTokenIds":["h1"]}],"adjudication":{"humanApprovedInTeamDesk":True}}
        desk.write_json(human,artifact);book=type("B",(),{"slug":"exodo","label":"Éxodo"})();claims={"exodo:3":{"name":"Ana"}}
        with patch.object(desk,"authorize",return_value="Ana"),patch.object(desk,"chapter_or_raise",return_value=(book,3,[1])),patch.object(desk,"assert_holder",return_value=(claims,"exodo:3")),patch.object(desk,"human_review_is_current",return_value=True),patch.object(desk,"human_path",return_value=human),patch.object(desk,"load_claims",return_value=claims),patch.object(desk,"save_claims"),patch.object(desk,"chapter_view",return_value={"verses":[]}),patch.object(desk,"_run") as run:
            desk.reopen_verse({"name":"Ana","token":"x","book":"exodo","chapter":3,"verse":1})
        run.assert_not_called()
        saved=desk.read_json(desk.recovered_path("exodo",3),{})["verses"]["1"]
        self.assertTrue(saved["revisionOpen"])
        self.assertEqual(saved["spanish"],"Texto aprobado.")
        self.assertFalse(saved["sourceConfirmed"])
        self.assertEqual(saved["reopenedFromApprovalSha256"],desk.object_fingerprint(artifact))
    def test_revised_approval_archives_prior_and_invalidates_chapter(self):
        root=Path(self.tmp.name);human=root/"human.json";packet_file=root/"packet.json";translation=root/"exodo.md"
        prior={"schema":"lbf-human-reviewed-candidate-v1","spanish":"Texto anterior.","units":[{"es":"Texto anterior","sourceTokenIds":["h1"]}],"approvalBinding":{"spanishSha256":"old"},"adjudication":{"humanApprovedInTeamDesk":True,"reviewedBy":"Ana"}}
        packet={"sourcePolicy":"lbf-source-policy-v4","evidenceStatus":"READY_FOR_MODEL","tokens":[{"sourceTokenId":"h1"}]}
        desk.write_json(human,prior);desk.write_json(packet_file,packet);translation.write_text("# Éxodo\n\n## Capítulo 3\n\n### 3:1\n\nTexto anterior.\n",encoding="utf-8")
        book=type("B",(),{"slug":"exodo","label":"Éxodo"})();claims={"exodo:3":{"name":"Ana"}}
        payload={"name":"Ana","token":"x","book":"exodo","chapter":3,"verse":1,"spanish":"Texto revisado.","units":[{"es":"Texto revisado","sourceTokenIds":["h1"]}],"unitsComplete":True,"decision":"Se corrigió el texto.","decisionCategory":"lexical","sourceConfirmed":True,"alignmentConfirmed":True,"suppliedConfirmed":True}
        with patch.object(desk,"authorize",return_value="Ana"),patch.object(desk,"chapter_or_raise",return_value=(book,3,[1])),patch.object(desk,"assert_holder",return_value=(claims,"exodo:3")),patch.object(desk,"human_review_is_current",return_value=True),patch.object(desk,"revision_is_open",return_value=True),patch.object(desk,"human_path",return_value=human),patch.object(desk,"packet_path",return_value=packet_file),patch.object(desk,"candidate_path",return_value=human),patch.object(desk,"translation_file",return_value=translation),patch.object(desk,"invalidate_status") as invalidate_status,patch.object(desk,"invalidate_chapter_review") as invalidate_chapter,patch.object(desk,"write_verse"),patch.object(desk,"load_claims",return_value=claims),patch.object(desk,"save_claims"),patch.object(desk,"chapter_view",return_value={"verses":[]}):
            desk.approve_verse(payload)
        saved=desk.read_json(human,{})
        self.assertEqual(saved["spanish"],"Texto revisado.")
        self.assertEqual(saved["approvalHistory"][0]["spanish"],"Texto anterior.")
        invalidate_status.assert_called_once_with("exodo")
        invalidate_chapter.assert_called_once_with(book,3,1,"Ana")
    def test_material_revision_invalidates_chapter_manifests(self):
        root=Path(self.tmp.name);book=type("B",(),{"slug":"exodo"})()
        review=root/"exodo-3.human-review.json";seed=root/"exodo-3.alignment-seed.json"
        desk.write_json(review,{"schema":"lbf-human-chapter-review-v1","verseWordingConfirmed":[1]})
        desk.write_json(seed,{"schema":"lbf-alignment-seed-manifest-v1","status":"seeded-hand","verses":[{"verse":1,"confirmed":True}]})
        with patch.object(desk,"pipeline_dir",return_value=root):desk.invalidate_chapter_review(book,3,1,"Ana")
        self.assertTrue(desk.read_json(review,{})["invalidated"])
        saved_seed=desk.read_json(seed,{})
        self.assertEqual(saved_seed["status"],"seeded-hand-incomplete")
        self.assertFalse(saved_seed["verses"][0]["confirmed"])
    def test_new_approval_binding_records_provenance_without_approving_status(self):
        packet={"sourcePolicy":"lbf-source-policy-v4","tokens":[{"sourceTokenId":"h1"}]}
        units=[{"es":"Texto","sourceTokenIds":["h1"]}]
        binding=desk.approval_binding("Texto",units,packet)
        self.assertEqual(binding["reviewSpecVersion"],desk.REVIEW_SPEC_VERSION)
        self.assertEqual(binding["sourcePolicy"],"lbf-source-policy-v4")
        self.assertIn("packetSha256",binding)
        self.assertIn("rulesSha256",binding)
    def test_prepare_estimate_skips_current_human_approval(self):
        book=type("B",(),{"slug":"exodo","label":"Éxodo"})()
        with patch.object(desk,"authorize",return_value="Ana"),patch.object(desk,"chapter_or_raise",return_value=(book,6,[1,2])),patch.object(desk,"assert_holder"),patch.object(desk,"human_review_is_current",return_value=True):
            estimate=desk.prepare_estimate("Ana","exodo",6,"11111111")
        self.assertEqual(estimate["humanReviewedSkipped"],2)
        self.assertEqual(estimate["maximumPaidCalls"],0)
    def test_prepare_estimate_does_not_reuse_unverified_legacy_seed(self):
        book=type("B",(),{"slug":"exodo","label":"Éxodo"})()
        candidate=Path(self.tmp.name)/"existing.json";candidate.write_text('{"spanish":"Texto","units":[{"es":"Texto","sourceTokenIds":["h1"]}]}\n',encoding="utf-8")
        packet={"sourcePolicy":"lbf-source-policy-v4","tokens":[{"sourceTokenId":"h1"}]}
        with patch.object(desk,"authorize",return_value="Ana"),patch.object(desk,"chapter_or_raise",return_value=(book,6,[1])),patch.object(desk,"assert_holder"),patch.object(desk,"human_review_is_current",return_value=False),patch.object(desk,"reusable_candidate",return_value=(candidate,{"spanish":"Texto"})),patch.object(desk,"build_packet",return_value=packet) as build,patch.object(desk,"load_draft_system",return_value="system"),patch.object(desk,"build_draft_prompt",return_value="prompt"),patch.object(desk,"build_audit_prompt",return_value="audit"):
            estimate=desk.prepare_estimate("Ana","exodo",6,"11111111")
        build.assert_called_once_with("exodo",6,1)
        self.assertEqual(estimate["reusedCandidates"],0)
        self.assertEqual(estimate["maximumPaidCalls"],1)
        self.assertEqual(estimate["auditCalls"],0)
    def test_existing_medium_draft_remains_compatible(self):
        packet={"sourcePolicy":"lbf-source-policy-v4","tokens":[]}
        candidate={"model":"gpt-5.6-sol","reasoningEffort":"medium","packetSha256":desk.packet_fingerprint(packet),"draftSpecVersion":"lbf-full-reverse-interlinear-v5"}
        self.assertTrue(desk.compatible_paid_draft(candidate,packet))
    def test_clean_chapter_gate_keeps_uncertainty_on_hold(self):
        root=Path(self.tmp.name); candidate_path=root/"draft.json"; packet_path=root/"packet.json"
        packet={"sourcePolicy":"lbf-source-policy-v4","evidenceStatus":"READY_FOR_MODEL","tokens":[{"sourceTokenId":"h1"}]}
        candidate={"schema":"lbf-gpt-draft-v1","model":"gpt-5.6-sol","reasoningEffort":"low","packetSha256":desk.packet_fingerprint(packet),"draftSpecVersion":desk.DRAFT_SPEC_VERSION,"spanish":"Texto","units":[{"es":"Texto","sourceTokenIds":["h1"]}],"uncertainties":[],"addedConcepts":[],"droppedUncitedUnits":0,"alignmentPrecisionFindings":[]}
        desk.write_json(candidate_path,candidate);desk.write_json(packet_path,packet)
        gate={"promptCurrent":True,"spanish":"pass","fidelity":"not-required","auditRequired":False,"fidelityFindings":[],"spanishFindings":[],"alignmentFindings":[]}
        with patch.object(desk,"candidate_path",return_value=candidate_path),patch.object(desk,"packet_path",return_value=packet_path),patch.object(desk,"gate_for",return_value=gate):
            clean,reasons=desk.clean_candidate_for_chapter_approval("exodo",1,1)
            self.assertEqual(clean["spanish"],"Texto");self.assertEqual(reasons,[])
            candidate["uncertainties"]=[{"issue":"choice"}];desk.write_json(candidate_path,candidate)
            clean,reasons=desk.clean_candidate_for_chapter_approval("exodo",1,1)
            self.assertIsNone(clean);self.assertIn("el candidato declaró incertidumbre",reasons)
    def test_clean_chapter_rechecks_historical_precision_findings(self):
        root=Path(self.tmp.name); candidate_path=root/"draft.json"; packet_path=root/"packet.json"
        packet={"sourcePolicy":"lbf-source-policy-v4","evidenceStatus":"READY_FOR_MODEL","tokens":[
            {"sourceTokenId":"h1","lemma":"1008+","morphExpanded":"Hebrew; noun proper"},
            {"sourceTokenId":"h2","lemma":"1008","morphExpanded":"Hebrew; noun proper"},
        ]}
        historical=[{"severity":"fail","issue":"The alignment unit combines independently alignable proper names; put each name in its own unit.","spanishSpan":"Betel","sourceTokenIds":["h1","h2"]}]
        candidate={"schema":"lbf-gpt-draft-v1","model":"gpt-6.1-sol","reasoningEffort":"low","packetSha256":desk.packet_fingerprint(packet),"draftSpecVersion":desk.DRAFT_SPEC_VERSION,"spanish":"Betel","units":[{"es":"Betel","sourceTokenIds":["h1","h2"]}],"alignmentPrecisionFindings":historical}
        desk.write_json(candidate_path,candidate);desk.write_json(packet_path,packet)
        gate={"promptCurrent":True,"spanish":"pass","fidelity":"not-required","auditRequired":False,"alignmentFindings":[]}
        with patch.object(desk,"candidate_path",return_value=candidate_path),patch.object(desk,"packet_path",return_value=packet_path),patch.object(desk,"gate_for",return_value=gate):
            clean,reasons=desk.clean_candidate_for_chapter_approval("genesis",12,8)
            self.assertIsNotNone(clean);self.assertEqual(reasons,[])
            self.assertEqual(desk.read_json(candidate_path)["alignmentPrecisionFindings"],historical)
            # Recomputing precision must still block independently alignable names.
            packet["tokens"].append({"sourceTokenId":"h3","lemma":"c/d/5857","morphExpanded":"Hebrew; conjunction; noun proper"})
            candidate.update(packetSha256=desk.packet_fingerprint(packet),spanish="Betel y Hai",units=[{"es":"Betel y Hai","sourceTokenIds":["h1","h2","h3"]}])
            desk.write_json(candidate_path,candidate);desk.write_json(packet_path,packet)
            clean,reasons=desk.clean_candidate_for_chapter_approval("genesis",12,8)
            self.assertIsNone(clean);self.assertTrue(any("proper names" in reason for reason in reasons))
    def test_whole_chapter_approval_approves_clean_and_leaves_hold(self):
        root=Path(self.tmp.name); translation=root/"exodo.md";translation.write_text("# Éxodo\n\n## Capítulo 1\n\n### 1:1\n\nTexto.\n\n### 1:2\n\nPendiente.\n",encoding="utf-8")
        book=type("B",(),{"slug":"exodo","label":"Éxodo"})();packet={"sourcePolicy":"lbf-source-policy-v4","tokens":[{"sourceTokenId":"h1"}]};clean={"spanish":"Texto.","units":[{"es":"Texto","sourceTokenIds":["h1"]}],"packet":packet,"candidate":{}}
        claims={"exodo:1":{"name":"Ana"}}
        def human_current(slug,chapter,verse): return (root/f"human-{verse}.json").is_file()
        def clean_for(slug,chapter,verse): return (clean,[]) if verse==1 else (None,["incertidumbre"])
        with patch.object(desk,"authorize",return_value="Ana"),patch.object(desk,"chapter_or_raise",return_value=(book,1,[1,2])),patch.object(desk,"assert_holder",return_value=(claims,"exodo:1")),patch.object(desk,"load_claims",return_value=claims),patch.object(desk,"save_claims"),patch.object(desk,"translation_file",return_value=translation),patch.object(desk,"human_path",side_effect=lambda s,c,v:root/f"human-{v}.json"),patch.object(desk,"human_review_is_current",side_effect=human_current),patch.object(desk,"clean_candidate_for_chapter_approval",side_effect=clean_for),patch.object(desk,"chapter_view",return_value={"verses":[]}):
            result=desk.approve_clean_chapter({"name":"Ana","token":"x","book":"exodo","chapter":1,"contextConfirmed":True,"cleanCandidatesConfirmed":True})
        self.assertEqual(result["chapterApproval"]["approvedNow"],[1])
        self.assertEqual(result["chapterApproval"]["missing"],[2])
        saved=desk.read_json(root/"human-1.json",{})
        self.assertEqual(saved["adjudication"]["approvalMode"],"whole-chapter-clean-candidate")
        self.assertFalse((root/"exodo-1.human-review.json").exists())
    def test_candidate_path_never_treats_request_json_as_draft(self):
        root=Path(self.tmp.name)
        (root/"exodo-2-1.draft-team-gpt.request.json").write_text('{"spanish":"wrong request"}\n',encoding="utf-8")
        (root/"exodo-2-1.draft-auto.json").write_text('{"spanish":"usable auto seed"}\n',encoding="utf-8")
        with patch.object(desk,"pipeline_dir",return_value=root),patch.object(desk,"human_review_is_current",return_value=False):
            self.assertEqual(desk.candidate_path("exodo",2,1).name,"exodo-2-1.draft-auto.json")
    def test_single_verse_prepare_rejects_nonexistent_verse(self):
        book=type("B",(),{"slug":"exodo","label":"Éxodo"})()
        with patch.object(desk,"authorize",return_value="Ana"),patch.object(desk,"chapter_or_raise",return_value=(book,1,[1,2])),patch.object(desk,"assert_holder"):
            with self.assertRaisesRegex(ValueError,"not in this Protestant chapter"):
                desk.prepare_estimate("Ana","exodo",1,"11111111",14)
    def test_prepare_worker_makes_no_calls_for_current_human_approval(self):
        key="exodo:6"; claims={key:{"name":"Ana"}}
        with patch.object(desk,"list_verses",return_value=[1]),patch.object(desk,"human_review_is_current",return_value=True),patch.object(desk,"_run") as run,patch.object(desk,"load_claims",return_value=claims),patch.object(desk,"save_claims"):
            desk._prepare("exodo",6,threading.Event())
        run.assert_not_called()
    def test_failed_audit_cannot_pass_silently(self):
        prior={"spanish":"Él, Aarón y Moisés.","uncertainties":[]}
        gate={"fidelity":"fail","spanish":"pass"}
        with self.assertRaisesRegex(ValueError,"will not manufacture"):
            desk.enforce_human_adjudication(prior,gate,prior["spanish"],"",False)
        with self.assertRaisesRegex(ValueError,"failed this unchanged wording"):
            desk.enforce_human_adjudication(prior,gate,prior["spanish"],"Explicación humana",False)
        desk.enforce_human_adjudication(prior,gate,"Estos *son* Aarón y Moisés.","Corregí la cláusula nominal.",False)
        desk.enforce_human_adjudication(prior,gate,prior["spanish"],"Rechazo fundamentado del fallo.",True)
    def test_cost_estimator_does_not_count_bytes_as_tokens(self):
        sample="א"*1000
        self.assertEqual(len(sample.encode("utf-8")),2000)
        self.assertEqual(desk.estimate_input_tokens(sample),720)
    def test_prompt_rejects_fragmentary_identification(self):
        prompt=(Path(desk.__file__).resolve().parents[2]/"tools"/"pipeline"/"draft_prompt.md").read_text(encoding="utf-8")
        self.assertIn("Él, Aarón y Moisés",prompt)
        self.assertIn("smallest continuous Spanish unit",prompt)
        self.assertIn("full reverse interlinear",prompt)
        self.assertIn("discontinuous",prompt)
        self.assertIn("Y dijo ← s1",prompt)
        self.assertIn("unambiguously God, Jesus Christ, or the Holy Spirit",prompt)
        self.assertIn("Él, Tú, Ti",prompt)
        self.assertRegex(prompt,r"יַהֲלֹם H3095 =\s+diamante")
        self.assertIn("לֶשֶׁם H3958 = rubí",prompt)
        self.assertIn("שָׁמִיר H8068 names the hard engraving point",prompt)
        self.assertIn("LBF HOUSE STYLE",desk.AUDIT_SYSTEM)
        self.assertRegex(desk.AUDIT_SYSTEM,r"יַהֲלֹם H3095 =\s+diamante")
        self.assertIn("the fixed rendering is\npedernal, not diamante",desk.AUDIT_SYSTEM)
        self.assertNotIn("doctrinal capitalization not in the tokens",desk.AUDIT_SYSTEM)
    def test_notification_ui_is_accessible_and_explains_credentials(self):
        html=(Path(desk.__file__).resolve().parent/"public"/"index.html").read_text(encoding="utf-8")
        self.assertIn('id="notifications" aria-live="polite"',html)
        self.assertIn("no la clave OpenAI",html)
        self.assertIn("Tu trabajo permanece guardado en este navegador",html)
        self.assertIn("/api/prepare-estimate",html)
        self.assertIn("Revisión humana local:</b> sin costo",html)
        self.assertIn("/api/audit-verse",html)
        self.assertIn("Máximo calculado",html)
        self.assertIn("La revisión encontró problemas",html)
        self.assertIn("g.alignmentFindings",html)
        self.assertIn("reglas anteriores",html)
        self.assertIn("Preparación requerida",html)
        self.assertIn("lbf-review-draft-v4:${current.book}",html)
        self.assertIn("legacyDraftKey",html)
        self.assertIn("Generar solo candidatos faltantes con Sol (pagado y opcional)",html)
        self.assertIn("/api/prepare-verse-estimate",html)
        self.assertIn("/api/prepare-verse",html)
        self.assertIn("open().catch",html)
        self.assertIn("La tarjeta se actualizará automáticamente",html)
        self.assertIn('class="override"',html)
        self.assertIn("la aplicación ya no la redacta",html)
        self.assertIn('class="supplied"',html)
        self.assertIn("toda palabra suplida",html)
        self.assertIn("Español alineado",html)
        self.assertIn("morphologySpanish",html)
        self.assertIn("refreshTokenSpanish",html)
        self.assertIn("refreshPreflight",html)
        self.assertIn("Comprobación local completa",html)
        self.assertIn('class="decision-category"',html)
        self.assertIn("EXPECTED_REVIEW_SPEC",html)
        self.assertIn("Patrones para evaluación humana",html)
        self.assertIn("no los convierte automáticamente en reglas",html)
        self.assertIn("mergeSeedUnits",html)
        self.assertIn("mergeUnitsBySourceId",html)
        self.assertIn("EXPECTED_DRAFT_SPEC",html)
        self.assertIn("server is out of date",html)
        self.assertIn("Añadir unidad",html)
        self.assertIn('class="insert-unit"',html)
        self.assertIn('class="drag-handle"',html)
        self.assertIn('class="move-up"',html)
        self.assertIn('class="move-down"',html)
        self.assertIn('className="token-link"',html)
        self.assertIn("function linkToken",html)
        self.assertIn("Alt+flecha",html)
        self.assertIn("Ctrl/⌘+Enter",html)
        self.assertIn("function setupApprovedCard",html)
        self.assertIn("Capítulo aprobado ✓",html)
        self.assertIn("chapterReviewed",html)
        self.assertIn("Quitar esta unidad de alineación",html)
        self.assertIn("¿Seguro que quieres quitar esta unidad de alineación?",html)
        self.assertIn("unitsComplete:true",html)
        self.assertIn("Puedes cancelar y revisar localmente sin pagar",html)
        self.assertIn('g.source!=="canonical-local-seed"',html)
        self.assertIn("Reabrir para revisión",html)
        self.assertIn("/api/reopen-verse",html)
        self.assertIn("/api/cancel-revision",html)
        self.assertIn("Ninguna llamada GPT se hará al guardar",html)
        self.assertIn("Lectura continua del capítulo",html)
        self.assertIn("Siguiente excepción",html)
        self.assertIn("Ir a aprobación de limpios",html)
        self.assertIn('reviewFilter="exceptions"',html)
        self.assertIn("function reviewStatus",html)
        self.assertIn("function enhanceReviewQueue",html)
        self.assertIn("la aprobación sigue siendo una acción humana separada",html)
        self.assertIn("Siguiente alineación",html)
        self.assertIn("Trabajo de alineación requerido",html)
        self.assertIn("function splitUnitAtCursor",html)
        self.assertIn("Dividir esta unidad en el cursor",html)
        self.assertIn("La segunda queda sin enlaces",html)
        self.assertIn("function unresolvedBoundaryFindings",html)
        self.assertIn("La cobertura está completa; solo falta dividir",html)
    def test_prepare_requires_explicit_cost_confirmation(self):
        book=type("B",(),{"slug":"exodo","label":"Éxodo"})()
        with patch.object(desk,"chapter_or_raise",return_value=(book,5,[1])):
            with self.assertRaisesRegex(ValueError,"cost estimate"):
                desk.prepare("Ana","exodo",5,"11111111",False)
    def test_prepare_rejects_missing_confirmed_maximum(self):
        book=type("B",(),{"slug":"exodo","label":"Éxodo"})()
        with patch.object(desk,"authorize",return_value="Ana"),patch.object(desk,"chapter_or_raise",return_value=(book,5,[1])),patch.object(desk,"prepare_estimate",return_value={"estimatedMaximumUsd":0.25}):
            with self.assertRaisesRegex(ValueError,"displayed maximum"):
                desk.prepare("Ana","exodo",5,"11111111",True)

if __name__=="__main__":unittest.main()
