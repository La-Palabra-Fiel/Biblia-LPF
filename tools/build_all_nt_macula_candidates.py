#!/usr/bin/env python3
"""Build every review-only NT structural candidate without approving HOLDs."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "pipeline"))

from books import NT  # noqa: E402
from nt_source import TR_CODE_BY_STEM  # noqa: E402

MAPPING = ROOT / "source" / "greek" / "TR1894" / "macula-structure-mapping.json"
BUILDER = ROOT / "tools" / "build_nt_macula_candidate.py"


def chapter_jobs() -> list[tuple[str, int]]:
    mapping = json.loads(MAPPING.read_text(encoding="utf-8"))
    slug_by_code = {TR_CODE_BY_STEM[book.utr_stem]: book.slug for book in NT}
    jobs = {
        (slug_by_code[parts[0]], int(parts[1]))
        for row in mapping.get("verses") or []
        if len(parts := str(row.get("reference") or "").split(".")) == 3
        and parts[0] in slug_by_code
        and parts[1].isdigit()
    }
    order = {book.slug: index for index, book in enumerate(NT)}
    return sorted(jobs, key=lambda job: (order[job[0]], job[1]))


def build(job: tuple[str, int]) -> str:
    book, chapter = job
    result = subprocess.run(
        [sys.executable, str(BUILDER), book, str(chapter)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(
            f"{book} {chapter}: "
            + (result.stderr or result.stdout or "candidate build failed").strip()
        )
    return result.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    jobs = chapter_jobs()
    completed = 0
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(build, job): job for job in jobs}
        for future in as_completed(futures):
            future.result()
            completed += 1
            if completed % 20 == 0 or completed == len(jobs):
                print(f"built {completed}/{len(jobs)} NT chapter candidates", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
