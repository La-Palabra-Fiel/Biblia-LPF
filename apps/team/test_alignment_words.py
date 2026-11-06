import unittest

import desk


class AlignmentWordSurfaceTests(unittest.TestCase):
    def test_preflight_removes_punctuation_but_preserves_supplied_markup(self):
        packet = {"tokens": [{"sourceTokenId": "h1"}, {"sourceTokenId": "h2"}]}
        units, findings = desk.alignment_preflight_findings(
            packet,
            [
                {"es": "¿Palabra,", "sourceTokenIds": ["h1"]},
                {"es": "*es verdad*!", "sourceTokenIds": ["h2"]},
            ],
            "¿Palabra, *es verdad*!",
        )

        self.assertEqual(findings, [])
        self.assertEqual(
            units,
            [
                {"es": "Palabra", "sourceTokenIds": ["h1"]},
                {"es": "*es verdad*", "sourceTokenIds": ["h2"]},
            ],
        )


if __name__ == "__main__":
    unittest.main()
