import unittest

import desk


class BulkApprovalRegressionTests(unittest.TestCase):
    def test_seed_units_do_not_create_a_synthetic_recovered_review(self):
        candidate = {"units": [{"es": "Texto", "sourceTokenIds": ["h1"]}]}
        self.assertEqual(desk.restore_recovered_units({}, candidate), {})

    def test_real_recovered_review_can_restore_seed_units(self):
        candidate = {"units": [{"es": "Texto", "sourceTokenIds": ["h1"]}]}
        recovered = {"spanish": "Texto revisado", "units": []}
        restored = desk.restore_recovered_units(recovered, candidate)
        self.assertEqual(restored["spanish"], "Texto revisado")
        self.assertEqual(restored["units"], candidate["units"])


if __name__ == "__main__":
    unittest.main()
