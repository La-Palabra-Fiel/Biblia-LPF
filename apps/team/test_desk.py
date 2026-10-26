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
        self.assertEqual(desk.model_name(),"gpt-5.6-sol")
        self.assertEqual(desk.reasoning_effort(),"medium")
        self.assertEqual(desk.SPANISH_GATE_MODEL,"deterministic-local")
        self.assertFalse(desk.audit_required({"uncertainties":[]},{"verdict":"pass"}))
        self.assertTrue(desk.audit_required({"uncertainties":[{"issue":"open"}]},{"verdict":"pass"}))
        self.assertTrue(desk.audit_required({"uncertainties":[]},{"verdict":"fail"}))
    def test_divine_name_is_locked(self):
        packet={"tokens":[{"sourceTokenId":"h1","lemma":"c/3068"}]}
        self.assertEqual(desk.lint_divine_name("Y dijo Yahvé",packet),[])
        self.assertTrue(desk.lint_divine_name("Y dijo el SEÑOR",packet))
        self.assertTrue(desk.lint_spanish("Y dijo Jehová"))
    def test_supplied_word_markup_is_well_formed(self):
        self.assertEqual(desk.lint_spanish("Yo *soy* Yahvé"),[])
        self.assertTrue(desk.lint_spanish("Yo *soy Yahvé"))
        self.assertTrue(desk.lint_spanish("Yo **soy** Yahvé"))
        self.assertTrue(desk.lint_spanish("Él, Aarón y Moisés, a quienes Yahvé dijo."))
        self.assertEqual(desk.lint_spanish("Estos *son* Aarón y Moisés."),[])
    def test_claim_is_per_chapter(self):
        with patch.object(desk,"chapter_or_raise",side_effect=lambda s,c:(type("B",(),{"slug":s,"label":"Éxodo"})(),int(c),[1])):
            desk.claim("Ana","exodo",3,"11111111");desk.claim("Luis","exodo",4,"22222222")
            with self.assertRaises(ValueError):desk.claim("Luis","exodo",3,"22222222")
            self.assertIn("exodo:3",desk.load_claims());self.assertIn("exodo:4",desk.load_claims())
    def test_nt_is_blocked(self):
        with self.assertRaises(ValueError):desk.book_or_raise("mateo")
    def test_alignment_requires_complete_token_coverage(self):
        packet={"tokens":[{"sourceTokenId":"h1"},{"sourceTokenId":"h2"}]}
        with self.assertRaises(ValueError):desk.validate_units(packet,[{"es":"Uno","sourceTokenIds":["h1"]}])
        self.assertEqual(len(desk.validate_units(packet,[{"es":"Uno","sourceTokenIds":["h1"]},{"es":"dos","sourceTokenIds":["h2"]}],"Uno, dos.")),2)
        with self.assertRaises(ValueError):desk.validate_units(packet,[{"es":"Uno","sourceTokenIds":["h1"]},{"es":"tres","sourceTokenIds":["h2"]}],"Uno, dos.")
    def test_verse_scanner(self):
        text="# Éxodo\n\n## Capítulo 3\n\n### 3:1\n\nTexto.\n\n### 3:2\n\n"
        self.assertEqual(desk.verse_body(text,3,1),"Texto.");self.assertEqual(desk.verse_body(text,3,2),"");self.assertIsNone(desk.verse_body(text,3,9))
    def test_recovered_review_is_noncanonical_app_state(self):
        self.assertEqual(desk.recovered_path("exodo",3),desk.RECOVERED/"exodo-3.json")
    def test_failed_review_attempt_can_be_recovered_before_validation(self):
        book=type("B",(),{"slug":"exodo"})()
        payload={"spanish":"Texto revisado","units":[{"es":"Texto revisado","sourceTokenIds":["h1"]}],"decision":"","sourceConfirmed":True,"alignmentConfirmed":True,"suppliedConfirmed":True,"auditOverrideConfirmed":True}
        desk.save_review_attempt(book,3,1,"Ana",payload)
        saved=desk.read_json(desk.recovered_path("exodo",3),{})["verses"]["1"]
        self.assertEqual(saved["spanish"],"Texto revisado")
        self.assertEqual(saved["lastAttemptedBy"],"Ana")
        self.assertTrue(saved["suppliedConfirmed"])
        self.assertTrue(saved["auditOverrideConfirmed"])
    def test_current_human_review_must_match_canonical_spanish(self):
        root=Path(self.tmp.name); human=root/"human.json"; translation=root/"exodo.md"
        translation.write_text("# Éxodo\n\n## Capítulo 6\n\n### 6:26\n\nEstos *son* Aarón y Moisés.\n",encoding="utf-8")
        human.write_text('{"schema":"lbf-human-reviewed-candidate-v1","spanish":"Estos *son* Aarón y Moisés.","adjudication":{"humanApprovedInTeamDesk":true}}\n',encoding="utf-8")
        with patch.object(desk,"human_path",return_value=human),patch.object(desk,"translation_file",return_value=translation):
            self.assertTrue(desk.human_review_is_current("exodo",6,26))
            translation.write_text("# Éxodo\n\n## Capítulo 6\n\n### 6:26\n\nTexto cambiado.\n",encoding="utf-8")
            self.assertFalse(desk.human_review_is_current("exodo",6,26))
    def test_prepare_estimate_skips_current_human_approval(self):
        book=type("B",(),{"slug":"exodo","label":"Éxodo"})()
        with patch.object(desk,"authorize",return_value="Ana"),patch.object(desk,"chapter_or_raise",return_value=(book,6,[1,2])),patch.object(desk,"assert_holder"),patch.object(desk,"human_review_is_current",return_value=True):
            estimate=desk.prepare_estimate("Ana","exodo",6,"11111111")
        self.assertEqual(estimate["humanReviewedSkipped"],2)
        self.assertEqual(estimate["maximumPaidCalls"],0)
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
    def test_notification_ui_is_accessible_and_explains_credentials(self):
        html=(Path(desk.__file__).resolve().parent/"public"/"index.html").read_text(encoding="utf-8")
        self.assertIn('id="notifications" aria-live="polite"',html)
        self.assertIn("no la clave OpenAI",html)
        self.assertIn("Tu trabajo permanece guardado en este navegador",html)
        self.assertIn("/api/prepare-estimate",html)
        self.assertIn("La revisión mecánica local es gratuita",html)
        self.assertIn("/api/audit-verse",html)
        self.assertIn("Nunca habrá más de",html)
        self.assertIn("La auditoría encontró problemas",html)
        self.assertIn('class="override"',html)
        self.assertIn("la aplicación ya no la redacta",html)
        self.assertIn('class="supplied"',html)
        self.assertIn("toda palabra suplida",html)
        self.assertIn("Español alineado",html)
        self.assertIn("morphologySpanish",html)
        self.assertIn("refreshTokenSpanish",html)
        self.assertIn("mergeSeedUnits",html)
        self.assertIn("Añadir unidad",html)
    def test_prepare_requires_explicit_cost_confirmation(self):
        book=type("B",(),{"slug":"exodo","label":"Éxodo"})()
        with patch.object(desk,"chapter_or_raise",return_value=(book,5,[1])):
            with self.assertRaisesRegex(ValueError,"cost estimate"):
                desk.prepare("Ana","exodo",5,"11111111",False)

if __name__=="__main__":unittest.main()
