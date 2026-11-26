from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

import export as lpf_export  # noqa: E402
import publish as lpf_publish  # noqa: E402
from consumer_books import consumer_book_id  # noqa: E402


SOURCE_COMMIT = "a" * 40
SOURCE_FILE = "alignment/nt/titus/titus-reverse-links.json"


def shared_links() -> list[dict]:
    return [
        {
            "phraseIndex": index,
            "reference": f"Tito 1:{index + 1}",
            "status": "hand",
            "units": [
                {
                    "unitId": f"{index}:0",
                    "surface": "Texto",
                    "sourceTokenIds": [f"n560010{index + 1:03d}001"],
                }
            ],
        }
        for index in range(50)
    ]


def run_git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=check,
    )


def alias_text() -> str:
    return (
        "<!-- LPF (technical id: LBF)\n"
        "     book: titus\n"
        "     source: Biblia-LBF/translation/nt/titus.md\n"
        f"     sourceCommit: {SOURCE_COMMIT}\n"
        "-->\n"
        "Tito 1:1 Texto equivocado de prueba.\n"
    )


def alias_alignment() -> dict:
    return {
        "generated": True,
        "doNotEdit": True,
        "sourceRepository": "La-Palabra-Fiel/Biblia-LPF",
        "sourceCommit": SOURCE_COMMIT,
        "sourceFile": SOURCE_FILE,
        "generator": "tools/export.py",
        "bookId": "titus",
        "links": shared_links(),
    }


def package_meta() -> dict:
    return {
        "generated": True,
        "doNotEdit": True,
        "sourceRepository": "La-Palabra-Fiel/Biblia-LPF",
        "sourceCommit": "b" * 40,
        "sourceFile": SOURCE_FILE,
        "generator": "tools/export.py",
        "bookId": "tito",
        "sourceBookId": "titus",
        "links": shared_links(),
    }


class ConsumerBookIdentityTests(unittest.TestCase):
    def test_only_declared_source_id_is_remapped(self):
        self.assertEqual(consumer_book_id("titus"), "tito")
        self.assertEqual(consumer_book_id("romanos"), "romanos")
        self.assertEqual(consumer_book_id("filemon"), "filemon")

    def test_exported_text_uses_consumer_id_and_preserves_source_path(self):
        row = {
            "testament": "nt",
            "translation_by": "John Wry",
            "translation_on": "2026-11-25",
            "alignment_by": "John Wry",
            "alignment_on": "2026-11-25",
        }
        text = lpf_export.build_consumer(
            "titus",
            "tito",
            row,
            [(1, 1, "Texto aprobado.")],
            SOURCE_COMMIT,
        )
        self.assertIn("     book: tito\n", text)
        self.assertIn("     source: Biblia-LBF/translation/nt/titus.md\n", text)
        self.assertIn("Tito 1:1 Texto aprobado.\n", text)
        self.assertNotIn("     book: titus\n", text)

    def test_exported_alignment_separates_consumer_and_source_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / SOURCE_FILE
            source.parent.mkdir(parents=True)
            source.write_text(
                json.dumps(
                    {
                        "textualBasis": "TR",
                        "schemaVersion": 1,
                        "numbering": "protestant",
                        "links": [],
                    }
                ),
                encoding="utf-8",
            )
            row = {
                "testament": "ot",
                "translation_by": "John Wry",
                "alignment_by": "John Wry",
            }
            with patch.object(lpf_export, "ROOT", root):
                result = lpf_export.build_alignment(
                    "titus", "tito", row, source, SOURCE_COMMIT
                )
        self.assertEqual(result["bookId"], "tito")
        self.assertEqual(result["sourceBookId"], "titus")
        self.assertEqual(result["sourceFile"], SOURCE_FILE)

    def test_package_reader_uses_consumer_filenames(self):
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory)
            (package / "tito.lbf.md").write_text("text", encoding="utf-8")
            (package / "tito.alignment.json").write_text(
                json.dumps(package_meta()), encoding="utf-8"
            )
            text_path, align_path, meta = lpf_publish.read_package(package, "titus")
        self.assertEqual(text_path.name, "tito.lbf.md")
        self.assertEqual(align_path.name, "tito.alignment.json")
        self.assertEqual(meta["bookId"], "tito")


class CorrectivePublisherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / "cgv-data"
        self.repo.mkdir()
        run_git(self.repo, "init", "-b", "main")
        run_git(self.repo, "config", "user.name", "Publisher Test")
        run_git(self.repo, "config", "user.email", "publisher@example.invalid")

        lbf = self.repo / "bibles" / "LBF"
        alignments = lbf / "alignments"
        alignments.mkdir(parents=True)
        (self.repo / "README.md").write_text("fixture\n", encoding="utf-8")
        (lbf / "tito.lbf.md").write_text("old canonical text\n", encoding="utf-8")
        (lbf / "titus.lbf.md").write_text(alias_text(), encoding="utf-8")
        (alignments / "titus.alignment.json").write_text(
            json.dumps(alias_alignment()) + "\n", encoding="utf-8"
        )
        run_git(self.repo, "add", ".")
        run_git(self.repo, "commit", "-m", "fixture")

        self.package = self.root / "package"
        self.package.mkdir()
        self.text_path = self.package / "tito.lbf.md"
        self.align_path = self.package / "tito.alignment.json"
        self.text_path.write_text("new canonical text\n", encoding="utf-8")
        self.align_path.write_text(json.dumps(package_meta()) + "\n", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_corrective_publish_atomically_replaces_pair_and_removes_aliases(self):
        branch = "lbf-tito-test"
        lpf_publish.publish(
            "titus",
            self.repo,
            branch,
            "main",
            self.text_path,
            self.align_path,
            package_meta(),
            "nt",
            "Correct Tito consumer ID.",
            cleanup_mispublished_source_id=True,
        )
        changed = run_git(
            self.repo, "diff", "--name-status", "--no-renames", "main.." + branch
        ).stdout.splitlines()
        self.assertEqual(
            set(changed),
            {
                "M\tbibles/LBF/tito.lbf.md",
                "A\tbibles/LBF/alignments/tito.alignment.json",
                "D\tbibles/LBF/titus.lbf.md",
                "D\tbibles/LBF/alignments/titus.alignment.json",
            },
        )
        tree = set(
            run_git(self.repo, "ls-tree", "-r", "--name-only", branch).stdout.splitlines()
        )
        self.assertIn("bibles/LBF/tito.lbf.md", tree)
        self.assertIn("bibles/LBF/alignments/tito.alignment.json", tree)
        self.assertNotIn("bibles/LBF/titus.lbf.md", tree)
        self.assertNotIn("bibles/LBF/alignments/titus.alignment.json", tree)
        self.assertEqual(
            run_git(self.repo, "show", branch + ":bibles/LBF/tito.lbf.md").stdout,
            self.text_path.read_text(encoding="utf-8"),
        )

    def test_cleanup_refuses_an_alias_with_wrong_provenance(self):
        bad = self.repo / "bibles" / "LBF" / "alignments" / "titus.alignment.json"
        metadata = alias_alignment()
        metadata["sourceFile"] = "alignment/nt/another/another-reverse-links.json"
        bad.write_text(json.dumps(metadata) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(SystemExit, "unexpected generated provenance"):
            lpf_publish.validate_mispublished_aliases(
                self.repo, "titus", "tito", "nt", package_meta()
            )


if __name__ == "__main__":
    unittest.main()
