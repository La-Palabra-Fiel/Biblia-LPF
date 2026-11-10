#!/usr/bin/env python3
"""Focused tests for TR Jesus/Christ order and LPF naming policy."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_tr import check_name_order  # noqa: E402


def token(strong: str) -> dict:
    return {"strong": strong, "subscript": False}


class JesusChristOrderTests(unittest.TestCase):
    def audit(self, spanish: str, *, christ_first: bool = False):
        greek_tokens = (
            [token("5547"), token("2424")]
            if christ_first
            else [token("2424"), token("5547")]
        )
        findings = []
        check_name_order(
            {(1, 1): greek_tokens},
            {(1, 1): spanish},
            findings,
            set(),
        )
        return findings

    def test_approved_forms_preserve_each_greek_order(self) -> None:
        self.assertEqual(self.audit("Jesús, *el* Cristo"), [])
        self.assertEqual(self.audit("Cristo Jesús", christ_first=True), [])

    def test_fused_and_unnatural_forms_fail(self) -> None:
        fused = self.audit("Jesucristo")
        bare = self.audit("Jesús Cristo")
        self.assertTrue(any(row.severity == "FAIL" and "distinct tokens" in row.message for row in fused))
        self.assertTrue(any(row.severity == "FAIL" and "not «Jesús Cristo»" in row.message for row in bare))

    def test_reversing_to_christ_jesus_fails_for_tr_jesus_christ(self) -> None:
        findings = self.audit("Cristo Jesús")
        self.assertTrue(any(row.severity == "FAIL" and "Ihsou Cristou" in row.message for row in findings))


if __name__ == "__main__":
    unittest.main()
