"""Tests for the LBF translation source packet."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_lib import normalize_audit
from draft_lib import (
    ACCEPTED_UNVERSIONED_PROMPT_SHA256,
    DRAFT_SPEC_VERSION,
    draft_specification_is_current,
    merge_source_units_by_id,
    normalize_draft,
    prompt_fingerprint,
)
from morph import expand_hebrew_morph
from polish_lib import freeze_from, normalize_polish
from source_packet import build_packet, dump_prompt, packet_for_prompt


class SourcePacketTests(unittest.TestCase):
    def test_exodo_1_16_dual_stones(self) -> None:
        packet = build_packet("exodo", 1, 16)
        self.assertEqual(packet["textualBasis"], "OSHB/WLC")
        self.assertEqual(packet["verse"], 16)
        self.assertGreaterEqual(len(packet["tokens"]), 12)
        self.assertTrue(all("es" not in token for token in packet["tokens"]))
        stones = next(
            token for token in packet["tokens"] if token.get("strongs") == "H70"
        )
        self.assertIn("dual", stones["morphExpanded"])
        self.assertIn("paleo", stones)
        self.assertNotIn("ahrc", stones)

    def test_hebrew_dual_morph(self) -> None:
        self.assertIn("dual", expand_hebrew_morph("HTd/Ncmda"))

    def test_titus_1_1_tr_packet(self) -> None:
        packet = build_packet("titus", 1, 1)
        self.assertEqual(packet["textualBasis"], "TR1894")
        self.assertGreaterEqual(len(packet["tokens"]), 10)
        self.assertTrue(any(token.get("strongs") == "G3972" for token in packet["tokens"]))

    def test_uncited_findings_are_discarded(self) -> None:
        packet = build_packet("exodo", 1, 16)
        raw = {
            "findings": [
                {
                    "severity": "fail",
                    "sourceTokenIds": ["not-a-token"],
                    "issue": "memory of RV1909",
                    "spanishSpan": "",
                },
                {
                    "severity": "warn",
                    "sourceTokenIds": ["h02001016007"],
                    "issue": "dual unmarked",
                    "spanishSpan": "las piedras",
                },
            ]
        }
        audit = normalize_audit(raw, packet, "vean sobre las piedras", "test")
        self.assertEqual(audit["verdict"], "pass")
        self.assertEqual(len(audit["findings"]), 1)
        self.assertEqual(audit["discardedUncitedFindings"], 1)

    def test_uncited_draft_units_are_dropped(self) -> None:
        packet = build_packet("exodo", 1, 16)
        raw = {
            "spanish": "vean sobre las piedras",
            "units": [
                {"es": "from memory", "sourceTokenIds": ["nope"]},
                {"es": "las piedras", "sourceTokenIds": ["h02001016007"]},
            ],
            "addedConcepts": [],
        }
        draft = normalize_draft(raw, packet, "test")
        self.assertEqual(draft["droppedUncitedUnits"], 1)
        self.assertEqual(len(draft["units"]), 1)

    def test_draft_is_bound_to_prompt_and_flags_coarse_alignment(self) -> None:
        packet = {
            "book": "exodo",
            "reference": "Éxodo 9:27",
            "chapter": 9,
            "verse": 27,
            "tokens": [
                {"sourceTokenId": f"h{i}", "morphExpanded": "Hebrew; noun common"}
                for i in range(1, 6)
            ],
        }
        raw = {
            "spanish": "Entonces el rey mandó llamar",
            "units": [{
                "es": "Entonces el rey mandó llamar",
                "sourceTokenIds": ["h1", "h2", "h3", "h4", "h5"],
            }],
        }
        draft = normalize_draft(raw, packet, "test")
        self.assertEqual(draft["promptSha256"], prompt_fingerprint())
        self.assertEqual(draft["draftSpecVersion"], DRAFT_SPEC_VERSION)
        self.assertTrue(draft_specification_is_current(draft))
        self.assertEqual(draft["alignmentPrecisionFindings"][0]["severity"], "fail")

    def test_draft_specification_migrates_current_unversioned_candidates(self) -> None:
        accepted_sha = next(iter(ACCEPTED_UNVERSIONED_PROMPT_SHA256))
        self.assertTrue(draft_specification_is_current({"promptSha256": accepted_sha}))
        self.assertTrue(draft_specification_is_current({"draftSpecVersion": "lbf-full-reverse-interlinear-v1"}))
        self.assertTrue(draft_specification_is_current({"draftSpecVersion": "lbf-full-reverse-interlinear-v2"}))
        self.assertTrue(draft_specification_is_current({"draftSpecVersion": "lbf-full-reverse-interlinear-v3"}))
        self.assertTrue(draft_specification_is_current({"draftSpecVersion": "lbf-full-reverse-interlinear-v4"}))
        self.assertFalse(draft_specification_is_current({"promptSha256": "older-prompt"}))

    def test_repeated_source_ids_are_consolidated_into_one_row(self) -> None:
        units = merge_source_units_by_id([
            {"es": "Y", "sourceTokenIds": ["h02001015001"]},
            {"es": "dijo", "sourceTokenIds": ["h02001015001"]},
            {"es": "el", "sourceTokenIds": ["h02001015002", "h02001015003"]},
            {"es": "rey", "sourceTokenIds": ["h02001015002"]},
            {"es": "de", "sourceTokenIds": ["h02001015002", "h02001015003"]},
            {"es": "Egipto", "sourceTokenIds": ["h02001015003"]},
        ])
        self.assertEqual(units, [
            {"es": "Y dijo", "sourceTokenIds": ["h02001015001"]},
            {"es": "el rey de Egipto", "sourceTokenIds": ["h02001015002", "h02001015003"]},
        ])

    def test_discontinuous_source_id_does_not_absorb_intervening_subject(self) -> None:
        units = merge_source_units_by_id([
            {"es": "Y", "sourceTokenIds": ["h1"]},
            {"es": "el rey", "sourceTokenIds": ["h2"]},
            {"es": "dijo", "sourceTokenIds": ["h1"]},
        ])
        self.assertEqual(units, [
            {"es": "Y", "sourceTokenIds": ["h1"]},
            {"es": "el rey", "sourceTokenIds": ["h2"]},
            {"es": "dijo", "sourceTokenIds": ["h1"]},
        ])

    def test_polish_freeze_keeps_dual_and_vivira(self) -> None:
        draft = {
            "units": [
                {"es": "las dos piedras", "sourceTokenIds": ["h02001016007"]},
                {"es": "vivirá", "sourceTokenIds": ["h02001016016"]},
            ],
            "uncertainties": [],
        }
        audit = {
            "verdict": "pass",
            "findings": [
                {"severity": "warn", "issue": "genitive parto", "spanishSpan": "parto"}
            ],
        }
        freeze = " ".join(freeze_from(draft, audit))
        self.assertIn("las dos piedras", freeze)
        self.assertIn("vivirá", freeze)
        self.assertIn("never a seat", freeze)

    def test_polish_keeps_token_ids(self) -> None:
        packet = build_packet("exodo", 1, 16)
        draft = {"spanish": "vivirá", "units": []}
        raw = {
            "spanish": "y vivirá",
            "units": [{"es": "vivirá", "sourceTokenIds": ["h02001016016"]}],
            "grammarChanges": ["conjunction flow"],
            "meaningChanges": [],
        }
        polish = normalize_polish(raw, packet, draft, "sonnet5")
        self.assertEqual(polish["units"][0]["sourceTokenIds"], ["h02001016016"])
        self.assertEqual(polish["meaningChanges"], [])

    def test_polish_gate_requires_grok_pass(self) -> None:
        from runner import gates
        draft = {"spanish": "vivirá"}
        fail = {"verdict": "fail", "spanish": "vivirá"}
        passed = {"verdict": "pass", "spanish": "vivirá"}
        self.assertFalse(gates(draft, fail, None)["canPolish"])
        self.assertTrue(gates(draft, passed, None)["canPolish"])
        self.assertFalse(gates(draft, {"verdict": "pass", "spanish": "other"}, None)["canPolish"])

    def test_exodo_1_has_twenty_two_protestant_verses(self) -> None:
        from source_packet import list_verses
        self.assertEqual(list_verses("exodo", 1), list(range(1, 23)))

    def test_eclesiastes_cross_chapter_kjv_offset(self) -> None:
        from source_packet import list_verses
        self.assertEqual(list_verses("eclesiastes", 4), list(range(1, 17)))
        self.assertEqual(list_verses("eclesiastes", 5), list(range(1, 21)))
        packet = build_packet("eclesiastes", 5, 1)
        self.assertEqual(packet["oshbOsis"], "Eccl.4.17")
        self.assertEqual(packet["tokens"][0]["strongs"], "H8104")
        self.assertEqual(packet["tokens"][1]["surface"], "רַגְלְךָ֗")
        self.assertEqual(packet["tokens"][1]["strongs"], "H7272")

    def test_salmos_title_merges_into_protestant_v1(self) -> None:
        from source_packet import list_verses
        self.assertEqual(list_verses("salmos", 3)[0], 1)
        packet = build_packet("salmos", 3, 1)
        self.assertIn("Ps.3.1", packet["oshbOsis"])
        self.assertIn("Ps.3.2", packet["oshbOsis"])

    def test_joel_hebrew_chapter_offset_is_protestant(self) -> None:
        from source_packet import list_verses
        self.assertEqual(list_verses("joel", 2), list(range(1, 33)))
        self.assertEqual(list_verses("joel", 3), list(range(1, 22)))

    def test_isaias_63_19_not_swallowed_by_64_1(self) -> None:
        from source_packet import list_verses
        self.assertEqual(list_verses("isaias", 63), list(range(1, 20)))
        self.assertEqual(list_verses("isaias", 64), list(range(1, 13)))
        v19 = build_packet("isaias", 63, 19)
        v64 = build_packet("isaias", 64, 1)
        self.assertEqual(v19["oshbOsis"], "Isa.63.19")
        self.assertEqual(v64["oshbOsis"], "Isa.63.19")
        self.assertEqual(v19["tokens"][0]["strongs"], "H1961")
        self.assertEqual(v64["tokens"][0]["strongs"], "H3863")

    def test_isaias_9_starts_at_hebrew_8_23(self) -> None:
        from source_packet import list_verses
        self.assertEqual(list_verses("isaias", 9), list(range(1, 22)))
        packet = build_packet("isaias", 9, 1)
        self.assertEqual(packet["oshbOsis"], "Isa.8.23")

    def test_salmos_14_title_stays_in_v1(self) -> None:
        packet = build_packet("salmos", 14, 1)
        self.assertIn("Ps.14.1", packet["oshbOsis"])
        self.assertEqual(packet["tokens"][0]["strongs"], "H5329")

    def test_titus_1_lists_tr_verses(self) -> None:
        from source_packet import list_verses
        verses = list_verses("titus", 1)
        self.assertEqual(verses[0], 1)
        self.assertGreaterEqual(len(verses), 16)

    def test_hold_is_parked_on_resume(self) -> None:
        from unittest.mock import patch
        from runner import run_one_verse

        def boom(*_args, **_kwargs):
            raise AssertionError("parked verses must not call APIs")

        with patch("runner.verse_disk_status", return_value="hold"):
            result = run_one_verse(
                "exodo",
                1,
                16,
                resume=True,
                steps={
                    "draft": boom,
                    "audit_draft": boom,
                    "polish": boom,
                    "audit_polish": boom,
                },
            )
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "hold")

    def test_chapter_continues_after_a_hold(self) -> None:
        from unittest.mock import patch
        from runner import empty_queue, run_chapter

        queue = empty_queue("exodo", 1, [1, 2])
        outcomes = {
            1: {"status": "passed", "verse": 1},
            2: {
                "status": "hold",
                "verse": 2,
                "stage": "audit-draft",
                "verdict": "fail",
                "findings": [],
            },
        }

        with patch("runner.list_verses", return_value=[1, 2]), patch(
            "runner.load_queue", return_value=queue
        ), patch("runner.save_queue", side_effect=lambda item: item), patch(
            "runner.run_one_verse",
            side_effect=lambda slug, chapter, verse, **kwargs: outcomes[verse],
        ):
            out = run_chapter("exodo", 1, require_api_keys=False)

        self.assertEqual(out["passed"], [1])
        self.assertEqual(out["holds"][0]["verse"], 2)

    def test_public_error_unwraps_openai_json(self) -> None:
        from runner import hold_record, public_error

        blob = '{"error": {"message": "You have no credits remaining.", "code": "credit_balance_exhausted"}}'
        self.assertEqual(public_error(blob), "You have no credits remaining.")
        hold = hold_record(
            7,
            "audit-draft",
            {
                "verdict": "fail",
                "spanish": "vosotros veréis",
                "notes": "2pl is Spain",
                "findings": [
                    {
                        "severity": "fail",
                        "issue": "Spain vosotros",
                        "spanishSpan": "vosotros",
                        "sourceTokenIds": ["h02001007001"],
                    }
                ],
            },
        )
        self.assertEqual(hold["verse"], 7)
        self.assertEqual(hold["notes"], "2pl is Spain")
        self.assertEqual(hold["findings"][0]["spanishSpan"], "vosotros")

    def test_lint_flags_known_anti_examples(self) -> None:
        from lint_lib import lint_spanish

        hits = {item["issue"] for item in lint_spanish("Cuando vosotros veáis el sexo, parid")}
        self.assertIn("Spain vosotros", hits)
        self.assertIn("Spain 2pl verb", hits)
        self.assertIn("el sexo is not in the packet; gender is si hijo / si hija", hits)
        self.assertIn("archaic parir", hits)
        clean = lint_spanish(
            "Y dijo: Cuando asistan a las hebreas a dar a luz, y verán sobre las dos piedras: si él es hijo, lo matarán; y si ella es hija, vivirá."
        )
        self.assertEqual(clean, [])

    def test_draft_uncertainties_remain_structured(self) -> None:
        from draft_lib import normalize_draft

        packet = {
            "book": "exodo",
            "reference": "Éxodo 1:1",
            "chapter": 1,
            "verse": 1,
            "tokens": [{"sourceTokenId": "h02001001009"}],
        }
        raw = {
            "spanish": "hombre",
            "units": [{"es": "hombre", "sourceTokenIds": ["h02001001009"]}],
            "uncertainties": [{
                "sourceTokenIds": ["h02001001009", "not-allowed"],
                "issue": "distributive force is unresolved",
            }],
        }
        result = normalize_draft(raw, packet, "gpt-pilot")
        self.assertEqual(result["uncertainties"], [{
            "sourceTokenIds": ["h02001001009"],
            "issue": "distributive force is unresolved",
        }])

    def test_needs_polish_only_on_warn(self) -> None:
        from runner import needs_polish

        silent = {"verdict": "pass", "findings": []}
        warned = {"verdict": "pass", "findings": [{"severity": "warn", "issue": "dual"}]}
        self.assertFalse(needs_polish(silent, polish="warn"))
        self.assertTrue(needs_polish(warned, polish="warn"))
        self.assertTrue(needs_polish(silent, polish="always"))
        self.assertFalse(needs_polish(warned, polish="never"))

    def test_lint_parks_without_grok(self) -> None:
        from unittest.mock import patch
        from runner import DRAFT_LABEL, draft_path, run_one_verse

        store = {str(draft_path("exodo", 1, 99, DRAFT_LABEL)): {"spanish": "Cuando vosotros veáis"}}

        def boom(*_args, **_kwargs):
            raise AssertionError("lint holds must not call APIs")

        with patch("runner.verse_disk_status", return_value="pending"), patch(
            "runner._read", side_effect=lambda path: store.get(str(path))
        ), patch("runner.write_json", lambda path, data: store.update({str(path): data}) or path):
            result = run_one_verse(
                "exodo",
                1,
                99,
                resume=True,
                steps={
                    "draft": boom,
                    "audit_draft": boom,
                    "polish": boom,
                    "audit_polish": boom,
                },
            )
        self.assertEqual(result["status"], "hold")
        self.assertEqual(result["stage"], "lint")

    def test_grok_pass_without_warns_skips_sonnet(self) -> None:
        from unittest.mock import patch
        from runner import DRAFT_LABEL, audit_path, draft_path, run_one_verse

        spanish = "Y dijo: Cuando asistan a las hebreas a dar a luz"
        store = {
            str(draft_path("exodo", 1, 99, DRAFT_LABEL)): {"spanish": spanish},
            str(audit_path("exodo", 1, 99, DRAFT_LABEL)): {
                "verdict": "pass",
                "spanish": spanish,
                "findings": [],
            },
        }

        def boom(*_args, **_kwargs):
            raise AssertionError("economy pass must not call Sonnet")

        with patch("runner.verse_disk_status", return_value="pending"), patch(
            "runner._read", side_effect=lambda path: store.get(str(path))
        ):
            result = run_one_verse(
                "exodo",
                1,
                99,
                resume=True,
                polish="warn",
                steps={
                    "draft": boom,
                    "audit_draft": boom,
                    "polish": boom,
                    "audit_polish": boom,
                },
            )
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["stage"], "audit-draft")

    def test_grok_warn_calls_sonnet(self) -> None:
        from unittest.mock import patch
        from runner import (
            DRAFT_LABEL,
            POLISH_LABEL,
            audit_path,
            draft_path,
            polish_path,
            run_one_verse,
        )

        spanish = "Y dijo: Cuando asistan a las hebreas a dar a luz"
        polished = "Y dijo: Cuando asistan a las hebreas a dar a luz."
        store = {
            str(draft_path("exodo", 1, 99, DRAFT_LABEL)): {"spanish": spanish},
            str(audit_path("exodo", 1, 99, DRAFT_LABEL)): {
                "verdict": "pass",
                "spanish": spanish,
                "findings": [
                    {
                        "severity": "warn",
                        "issue": "dual unmarked",
                        "sourceTokenIds": ["h02001016007"],
                    }
                ],
            },
        }

        def do_polish(*_args, **_kwargs):
            store[str(polish_path("exodo", 1, 99, "sonnet5"))] = {"spanish": polished}

        def do_audit_polish(*_args, **_kwargs):
            store[str(audit_path("exodo", 1, 99, POLISH_LABEL))] = {
                "verdict": "pass",
                "spanish": polished,
            }

        def boom(*_args, **_kwargs):
            raise AssertionError("draft/grok already on disk")

        with patch("runner.verse_disk_status", return_value="pending"), patch(
            "runner._read", side_effect=lambda path: store.get(str(path))
        ), patch("runner.keys", return_value={"openai": True, "xai": True, "anthropic": True}):
            result = run_one_verse(
                "exodo",
                1,
                99,
                resume=True,
                polish="warn",
                steps={
                    "draft": boom,
                    "audit_draft": boom,
                    "polish": do_polish,
                    "audit_polish": do_audit_polish,
                },
            )
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["stage"], "audit-polish")

    def test_usage_cost_does_not_double_count_reasoning(self) -> None:
        from usage_lib import call_cost, extract_usage

        usage = extract_usage(
            "openai",
            "gpt-5.6",
            {
                "usage": {
                    "prompt_tokens": 2900,
                    "completion_tokens": 3600,
                    "completion_tokens_details": {"reasoning_tokens": 3000},
                }
            },
        )
        self.assertEqual(usage["input"], 2900)
        self.assertEqual(usage["output"], 3600)
        self.assertEqual(usage["reasoning"], 3000)
        self.assertAlmostEqual(call_cost(usage), 2900 / 1_000_000 * 4 + 3600 / 1_000_000 * 20)

    def test_ot_prompt_packet_has_complete_canonical_evidence_bundle(self) -> None:
        packet = build_packet("exodo", 1, 16)
        self.assertEqual(packet["sourcePolicy"], "lbf-source-policy-v4")
        self.assertEqual(
            packet["evidencePolicy"],
            "canonical-ot-evidence-bundle-v1",
        )
        self.assertEqual(packet["evidenceStatus"], "READY_FOR_MODEL")
        self.assertTrue(all("ahrc" not in token for token in packet["tokens"]))
        self.assertEqual(packet_for_prompt(packet)["reference"], "Éxodo 1:16")

    def test_macula_visible_surface_wins_over_faulty_unicode_metadata(self) -> None:
        packet = build_packet("exodo", 4, 13)
        self.assertEqual(packet["evidenceStatus"], "READY_FOR_MODEL")
        self.assertEqual(packet["tokens"][1]["surface"], "בִּ֣י")
        self.assertEqual(packet["syntax"]["mapping"]["status"], "exact")

    def test_model_packet_is_compact_but_keeps_primary_evidence(self) -> None:
        packet = build_packet("exodo", 1, 5)
        compact = packet_for_prompt(packet)
        self.assertEqual(compact["promptProfile"], "canonical-ot-compact-v1")
        self.assertEqual(
            [item["sourceTokenId"] for item in compact["tokens"]],
            [item["sourceTokenId"] for item in packet["tokens"]],
        )
        self.assertTrue(compact["syntax"]["nodes"])
        self.assertNotIn("sourceCommit", compact["lexicalEvidence"][0])
        self.assertNotIn("paleo", compact["tokens"][0])
        self.assertTrue(all(item["relation"] != "current" for item in compact["originalLanguageContext"]))
        full_size = len(dump_prompt({"packet": packet}))
        compact_size = len(dump_prompt({"packet": compact}))
        self.assertLess(compact_size, full_size * 0.65)

    def test_exact_neighbor_constructions_precede_generic_corpus_samples(self) -> None:
        packet = build_packet("exodo", 1, 5)
        evidence = {
            item["corpusEvidenceId"]: item
            for item in packet["corpusEvidence"]
        }
        refs = [item["reference"] for item in evidence["3409"]["samples"][:2]]
        self.assertEqual(refs, ["Gen.46.26", "Judg.8.30"])

    def test_nt_prompt_remains_blocked(self) -> None:
        packet = build_packet("titus", 1, 1)
        with self.assertRaisesRegex(RuntimeError, "evidence bundle is incomplete"):
            packet_for_prompt(packet)

    def test_macula_mapping_is_exact_and_structural_only(self) -> None:
        packet = build_packet("exodo", 1, 16)
        self.assertEqual(packet["syntax"]["mapping"]["status"], "exact")
        self.assertEqual(packet["syntax"]["mapping"]["matched"], len(packet["tokens"]))
        serialized = dump_prompt(packet)
        for forbidden in ('"english":', '"mandarin":', '"gloss":', '"greek":', '"sdbh":', '"frame":'):
            self.assertNotIn(forbidden, serialized)

    def test_prompt_rejects_forbidden_macula_field(self) -> None:
        packet = build_packet("exodo", 1, 16)
        packet["syntax"]["nodes"][0]["gloss"] = "forbidden"
        with self.assertRaisesRegex(ValueError, "forbidden MACULA fields leaked"):
            packet_for_prompt(packet)

    def test_prompt_rejects_noncanonical_syntax_token(self) -> None:
        packet = build_packet("exodo", 1, 16)
        packet["syntax"]["nodes"][0]["sourceTokenIds"].append("not-a-token")
        with self.assertRaisesRegex(ValueError, "noncanonical token IDs"):
            packet_for_prompt(packet)

    def test_open_scriptures_lexicon_is_pinned_and_mapped(self) -> None:
        packet = build_packet("exodo", 1, 1)
        son = next(token for token in packet["tokens"] if token["lemma"] == "1121 a")
        evidence = next(
            item
            for item in packet["lexicalEvidence"]
            if item["lexicalIndexId"] == son["lexicalEvidenceId"]
        )
        self.assertEqual(evidence["augmentedStrong"], "1121a")
        self.assertEqual(evidence["lexicalIndexId"], "bss")
        self.assertEqual(
            evidence["sourceCommit"],
            "21c9add13bc727d3a951361778e97e3ff7afd1ce",
        )
        self.assertEqual(evidence["authority"], "secondary-possibilities-only")
        self.assertTrue(evidence["possibleSenses"])

    def test_exodus_7_11_plural_lahat_follows_pinned_bdb_form_redirect(self) -> None:
        packet = build_packet("exodo", 7, 11)
        token = next(item for item in packet["tokens"] if item["lemma"] == "b/3858")
        evidence = next(
            item
            for item in packet["lexicalEvidence"]
            if (item.get("lexicalEvidenceId") or item["lexicalIndexId"])
            == token["lexicalEvidenceId"]
        )
        self.assertEqual(evidence["bdbIndexedEntryId"], "l.ap.ab")
        self.assertEqual(evidence["bdbEntryId"], "l.ax.ab")
        self.assertEqual(
            evidence["bdbFormCrossReference"],
            {
                "entryId": "l.ap.ac",
                "targetRootEntryId": "l.ax.aa",
                "resolvedEntryId": "l.ax.ab",
            },
        )
        self.assertIn("enchantments", evidence["possibleSenses"])
        self.assertNotIn("flame", evidence["possibleSenses"])
        prompt = packet_for_prompt(packet)
        prompt_evidence = next(
            item
            for item in prompt["lexicalEvidence"]
            if (item.get("lexicalEvidenceId") or item["lexicalIndexId"])
            == token["lexicalEvidenceId"]
        )
        self.assertIn("enchantments", prompt_evidence["possibleSenses"])

    def test_genesis_3_24_singular_lahat_remains_flame(self) -> None:
        packet = build_packet("genesis", 3, 24)
        token = next(item for item in packet["tokens"] if item["lemma"] == "3858")
        evidence = next(
            item
            for item in packet["lexicalEvidence"]
            if (item.get("lexicalEvidenceId") or item["lexicalIndexId"])
            == token["lexicalEvidenceId"]
        )
        self.assertEqual(evidence["bdbEntryId"], "l.ap.ab")
        self.assertNotIn("bdbFormCrossReference", evidence)
        self.assertIn("flame", evidence["possibleSenses"])
        self.assertNotIn("enchantments", evidence["possibleSenses"])

    def test_open_scriptures_entries_are_deduplicated(self) -> None:
        packet = build_packet("exodo", 1, 1)
        ids = [item["lexicalIndexId"] for item in packet["lexicalEvidence"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_prompt_rejects_tampered_lexical_evidence(self) -> None:
        packet = build_packet("exodo", 1, 1)
        packet["lexicalEvidence"][0]["sourceCommit"] = "floating-master"
        with self.assertRaisesRegex(ValueError, "noncanonical lexical evidence"):
            packet_for_prompt(packet)

    def test_tbesh_meaning_never_enters_ot_packet(self) -> None:
        prompt = dump_prompt(build_packet("exodo", 1, 1))
        self.assertNotIn("Online Bible", prompt)
        self.assertNotIn("TBESH", prompt)

    def test_prompt_rejects_noncanonical_source_allowlist(self) -> None:
        packet = build_packet("titus", 1, 1)
        packet["allowedSources"].append("other-version")
        with self.assertRaisesRegex(ValueError, "noncanonical source allowlist"):
            packet_for_prompt(packet)

    def test_grok_reasoning_billed_when_above_output(self) -> None:
        from usage_lib import call_cost, extract_usage

        usage = extract_usage(
            "xai",
            "grok-4",
            {
                "usage": {
                    "prompt_tokens": 4000,
                    "completion_tokens": 25,
                    "completion_tokens_details": {"reasoning_tokens": 991},
                }
            },
        )
        self.assertEqual(usage["output"], 25)
        self.assertEqual(usage["reasoning"], 991)
        self.assertAlmostEqual(
            call_cost(usage),
            4000 / 1_000_000 * 2 + (25 + 991) / 1_000_000 * 6,
        )

    def test_usage_rollup_scales_bible(self) -> None:
        from usage_lib import BIBLE_VERSES, summarize_files

        totals = summarize_files([])
        self.assertEqual(totals["bibleAtThisRate"], 0)
        self.assertEqual(BIBLE_VERSES, 31098)


if __name__ == "__main__":
    unittest.main()
