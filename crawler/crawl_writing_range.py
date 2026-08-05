#!/usr/bin/env python3
"""Batch crawl and validate Academic IELTS Writing tests."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from scraper import fetch_test_page
from writing_parser import parse_writing_test
from writing_validator import validate_writing_test

BASE_URL = "https://practicepteonline.com/ielts-writing-test-{n}/"


@dataclass
class CrawlOutcome:
    number: int
    test: object | None
    error: str | None = None


def crawl_one(number: int, *, project: Optional[str], ai_validate: bool, model: str) -> CrawlOutcome:
    url = BASE_URL.format(n=number)
    try:
        html = fetch_test_page(url)
        test = parse_writing_test(html, url)
        deterministic = validate_writing_test(test)
        if not deterministic.valid:
            return CrawlOutcome(number, None, deterministic.report())

        if ai_validate:
            if not project:
                return CrawlOutcome(number, None, "--project is required with --ai-validate")
            from ai_writing_validator import ai_validate_writing

            result = ai_validate_writing(test, html, project=project, model=model)
            if not result.get("valid", False):
                return CrawlOutcome(number, None, "AI validation failed: " + "; ".join(result.get("issues", [])[:3]))

        return CrawlOutcome(number, test)
    except Exception as exc:  # pragma: no cover - network failures are reported to CLI
        return CrawlOutcome(number, None, f"{type(exc).__name__}: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("start", type=int)
    parser.add_argument("end", type=int)
    parser.add_argument("--output", default="../frontend/src/data/writing-tests")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--ai-validate", action="store_true")
    parser.add_argument("--project", default=None)
    parser.add_argument("--model", default="gemini-2.5-pro")
    args = parser.parse_args()

    if args.start > args.end:
        parser.error("start must be <= end")
    numbers = list(range(args.start, args.end + 1))
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = [
            executor.submit(
                crawl_one,
                number,
                project=args.project,
                ai_validate=args.ai_validate,
                model=args.model,
            )
            for number in numbers
        ]
        outcomes = [future.result() for future in as_completed(futures)]

    outcomes.sort(key=lambda item: item.number)
    failures = [item for item in outcomes if item.test is None]
    for item in outcomes:
        status = "OK" if item.test is not None else "FAIL"
        print(f"[{status}] writing-test-{item.number}: {item.error or 'validated'}")
    if failures:
        print(f"Aborting without writing output: {len(failures)} test(s) failed", file=sys.stderr)
        return 1

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="writing-range-") as temp_name:
        temp_dir = Path(temp_name)
        for item in outcomes:
            target = temp_dir / f"writing-test-{item.number}.json"
            target.write_text(
                json.dumps(item.test.model_dump(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        for item in outcomes:
            source = temp_dir / f"writing-test-{item.number}.json"
            shutil.copyfile(source, output_dir / source.name)

    print(f"Saved {len(outcomes)} writing tests to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
