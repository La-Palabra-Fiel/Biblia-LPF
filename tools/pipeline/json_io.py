"""Small atomic JSON writer for artifacts read by the live review desk."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


def write_json_atomic(path: Path, payload: object) -> None:
    """Replace a JSON file only after its complete new contents are durable."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary_path = Path(temporary)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)
