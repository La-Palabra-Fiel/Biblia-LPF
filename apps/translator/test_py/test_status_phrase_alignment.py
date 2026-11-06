import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools import status


class PhraseAlignmentStatusTests(unittest.TestCase):
    def write_book(self, root: Path, final_surface: str = "Dios", link_status: str = "hand") -> None:
        translation_dir = root / "translation" / "nt"
        alignment_dir = root / "alignment" / "nt" / "sample"
        translation_dir.mkdir(parents=True)
        alignment_dir.mkdir(parents=True)
        (translation_dir / "sample.md").write_text(
            "# Sample\n\n## Capítulo 1\n\n### 1:1\n\nEn el principio, creó Dios.\n",
            encoding="utf-8",
        )
        links = {
            "links": [
                {
                    "phraseIndex": 0,
                    "reference": "Sample 1:1",
                    "status": link_status,
                    "units": [
                        {"surface": "En", "sourceTokenIds": ["t1"], "method": "hand"},
                        {"surface": "el principio", "sourceTokenIds": ["t2"], "method": "hand"},
                    ],
                },
                {
                    "phraseIndex": 1,
                    "reference": "Sample 1:1",
                    "status": link_status,
                    "units": [
                        {"surface": "creó", "sourceTokenIds": ["t3"], "method": "hand"},
                        {"surface": final_surface, "sourceTokenIds": ["t4"], "method": "hand"},
                    ],
                },
            ]
        }
        (alignment_dir / "sample-reverse-links.json").write_text(
            json.dumps(links, ensure_ascii=False),
            encoding="utf-8",
        )

    def test_multiple_phrases_reconstruct_one_verse(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_book(root)
            with patch.object(status, "ROOT", root):
                self.assertEqual(status.alignment_errors("sample", "nt", 1), [])

    def test_complete_verse_mismatch_is_still_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_book(root, final_surface="Señor")
            with patch.object(status, "ROOT", root):
                self.assertEqual(
                    status.alignment_errors("sample", "nt", 1),
                    ["sample 1:1: units do not reconstruct Spanish"],
                )

    def test_punctuation_in_alignment_surface_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_book(root, final_surface="Dios.")
            with patch.object(status, "ROOT", root):
                self.assertEqual(
                    status.alignment_errors("sample", "nt", 1),
                    ["sample 1:1: alignment surfaces must contain words only"],
                )

    def test_seeded_hand_units_are_not_human_confirmed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_book(root, link_status="seeded-hand")
            with patch.object(status, "ROOT", root):
                self.assertEqual(
                    status.alignment_errors("sample", "nt", 1),
                    [
                        "sample: alignment still has auto=0 gloss=0 unwalked=0 "
                        "unconfirmed=2 other=0",
                        "sample: alignment has no finished map units",
                    ],
                )


if __name__ == "__main__":
    unittest.main()
