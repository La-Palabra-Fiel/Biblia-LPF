from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import publication_progress as progress


class PublicationProgressTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        translation = self.root / "translation" / "ot"
        translation.mkdir(parents=True)
        (translation / "sample.md").write_text(
            "# Sample\n\n## Capítulo 1\n\n### 1:1\n\nTexto aprobado.\n\n"
            "## Capítulo 2\n\n### 2:1\n\nTexto borrador.\n",
            encoding="utf-8",
        )
        pipeline = self.root / "pipeline" / "ot" / "sample"
        pipeline.mkdir(parents=True)
        progress.write_json(
            pipeline / "sample-1-1.candidate-human-reviewed.json",
            {
                "schema": "lbf-human-reviewed-candidate-v1",
                "spanish": "Texto aprobado.",
                "units": [
                    {"es": "Texto", "sourceTokenIds": ["h1"]},
                    {"es": "aprobado", "sourceTokenIds": ["h2"]},
                ],
                "approvalBinding": {"spanishSha256": "bound"},
                "adjudication": {
                    "humanApprovedInTeamDesk": True,
                    "reviewedBy": "Ana",
                    "reviewedOn": "2026-11-05",
                },
            },
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_approved_chapter_promotes_alignment_and_progress_labels(self):
        with patch.object(progress, "ROOT", self.root):
            path = progress.promote_chapter_alignment(
                book="sample", testament="ot", label="Sample", chapter=1, verses=[1]
            )
            progress.write_json(
                self.root / "pipeline" / "ot" / "sample" / "sample-1.human-review.json",
                {
                    "schema": "lbf-human-chapter-review-v1",
                    "continuityVoiceFlowConfirmed": True,
                    "verseWordingConfirmed": [1],
                    "alignmentSeedsConfirmed": [1],
                },
            )
            public = progress.publication_progress(
                book="sample", testament="ot", book_finished=False
            )
        document = progress.read_json(path, {})
        self.assertEqual(document["links"][0]["status"], "hand")
        self.assertTrue(all(unit["status"] == "confirmed" for unit in document["links"][0]["units"]))
        self.assertEqual(public["bookStatus"], "unfinished")
        self.assertEqual(public["schema"], "lpf-website-progress-v1")
        self.assertEqual(public["chapterStatuses"], {"1": "approved", "2": "draft-only"})
        self.assertEqual(public["chapterLabels"], {"1": None, "2": "Solo borrador"})

    def test_revision_demotes_chapter_without_deleting_links(self):
        with patch.object(progress, "ROOT", self.root):
            path = progress.promote_chapter_alignment(
                book="sample", testament="ot", label="Sample", chapter=1, verses=[1]
            )
            progress.demote_chapter_alignment(book="sample", testament="ot", chapter=1)
        document = progress.read_json(path, {})
        self.assertEqual(document["links"][0]["status"], "seeded-hand")
        self.assertEqual(document["links"][0]["units"][0]["status"], "seeded")


if __name__ == "__main__":
    unittest.main()
