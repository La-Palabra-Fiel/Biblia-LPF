"""Tests for JSON publication used by concurrent pipeline/UI readers."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from json_io import write_json_atomic


class JsonIoTests(unittest.TestCase):
    def test_atomic_writer_replaces_complete_json_without_leftovers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "artifact.json"
            write_json_atomic(path, {"value": "antes"})
            write_json_atomic(path, {"value": "después", "rows": list(range(50))})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["value"], "después")
            self.assertEqual(list(Path(directory).iterdir()), [path])


if __name__ == "__main__":
    unittest.main()
