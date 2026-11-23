from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools"))

import publish  # noqa: E402
import export  # noqa: E402


class CanonicalBookWorkflow(unittest.TestCase):
    def test_nt_export_maps_tr_tokens_to_reader_tokens_without_losing_canonical_ids(self) -> None:
        links = [{
            "reference": "Romanos 1:1",
            "units": [
                {"surface": "de Jesús", "sourceTokenIds": ["n45001001003"]},
                {"surface": "Cristo", "sourceTokenIds": ["n45001001004"]},
            ],
        }]
        exported, metadata = export.build_reader_links("romanos", links)
        units = exported[0]["units"]
        self.assertEqual(units[0]["canonicalSourceTokenIds"], ["n45001001003"])
        self.assertEqual(units[0]["sourceTokenIds"], ["n45001001004"])
        self.assertEqual(units[1]["canonicalSourceTokenIds"], ["n45001001004"])
        self.assertEqual(units[1]["sourceTokenIds"], ["n45001001003"])
        self.assertEqual(links[0]["units"][0]["sourceTokenIds"], ["n45001001003"])
        self.assertEqual(metadata["canonicalSourceTokenField"], "canonicalSourceTokenIds")
        self.assertEqual(metadata["readerSourceTokenField"], "sourceTokenIds")

    def test_nt_export_does_not_invent_reader_identity_for_tr_only_token(self) -> None:
        links = [{
            "reference": "Romanos 1:3",
            "units": [{"surface": "de David", "sourceTokenIds": ["n45001003009"]}],
        }]
        exported, _ = export.build_reader_links("romanos", links)
        unit = exported[0]["units"][0]
        self.assertEqual(unit["canonicalSourceTokenIds"], ["n45001003009"])
        self.assertEqual(unit["sourceTokenIds"], [])

    def test_status_script_can_check_one_book_without_unrelated_blockers(self) -> None:
        result = subprocess.run(
            [sys.executable, str(REPO / "tools" / "status.py"), "titus"],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("no stale ready/done labels", result.stdout)

    def test_status_script_refuses_an_unknown_book(self) -> None:
        result = subprocess.run(
            [sys.executable, str(REPO / "tools" / "status.py"), "not-a-book"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("not-a-book is not in STATUS.md", result.stderr)

    def test_publisher_status_gate_checks_only_the_selected_book(self) -> None:
        with patch("publish.subprocess.run") as run:
            run.return_value.returncode = 0
            publish.status_gate("apocalipsis")
        run.assert_called_once_with(
            [sys.executable, str(REPO / "tools" / "status.py"), "apocalipsis"],
            cwd=REPO,
        )


if __name__ == "__main__":
    unittest.main()
