#!/usr/bin/env python3
"""
Batch crawl helper for practicepteonline reading tests.

Supports:
- Concurrency (multiple tests in flight)
- AI validate-first, AI repair-on-demand
- Timeouts and retries around slow AI calls

Examples:
  python crawl_range.py 11 20 --output ../frontend/src/data/tests
  python crawl_range.py 11 20 --output ../frontend/src/data/tests --ai-repair --project <gcp-project>
  python crawl_range.py 11 20 --output ../frontend/src/data/tests --ai-auto --project <gcp-project> --workers 4
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ai_repair import ai_repair
from ai_validator import ai_validate
from parser import parse_reading_test
from scraper import fetch_test_page
from validator import validate_reading_test, validate_repaired_reading_test


BASE_URL = "https://practicepteonline.com/ielts-reading-test-{n}/"


@dataclass
class CrawlOutcome:
    test_num: int
    ok: bool
    message: str
    saved_json: Optional[Path] = None
    saved_report: Optional[Path] = None


def _save_json(out_dir: Path, test) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{test.id}.json"
    path.write_text(json.dumps(test.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def _save_report(out_dir: Path, test_id: str, report: dict) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{test_id}.repair-report.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def _run_ai_validate_with_retries(
    test,
    html: str,
    project: str,
    model: str,
    timeout_s: int,
    retries: int,
    page_text_max_chars: int,
) -> dict:
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        start = time.time()
        try:
            # Run in a one-off executor to enforce timeout without changing the genai client.
            with ThreadPoolExecutor(max_workers=1) as ex:
                fut = ex.submit(
                    ai_validate,
                    test,
                    html,
                    project,
                    "us-central1",
                    model,
                    page_text_max_chars,
                )
                return fut.result(timeout=timeout_s)
        except FuturesTimeoutError as e:
            last_exc = e
        except Exception as e:
            last_exc = e
        finally:
            _ = start  # keep a breakpoint-friendly local

        if attempt < retries:
            time.sleep(min(2 ** attempt, 8))

    raise RuntimeError(f"AI validate failed after retries: {last_exc}")


def _run_ai_repair_with_retries(
    test,
    html: str,
    project: str,
    model: str,
    timeout_s: int,
    retries: int,
    page_text_max_chars: int,
) -> tuple:
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with ThreadPoolExecutor(max_workers=1) as ex:
                fut = ex.submit(
                    ai_repair,
                    test,
                    html,
                    project,
                    "us-central1",
                    model,
                    page_text_max_chars,
                )
                return fut.result(timeout=timeout_s)
        except FuturesTimeoutError as e:
            last_exc = e
        except Exception as e:
            last_exc = e

        if attempt < retries:
            time.sleep(min(2 ** attempt, 8))

    raise RuntimeError(f"AI repair failed after retries: {last_exc}")


def crawl_one(
    test_num: int,
    out_dir: Path,
    project: Optional[str],
    ai_validate_only: bool,
    ai_repair_always: bool,
    ai_auto: bool,
    validate_model: str,
    repair_model: str,
    ai_timeout_s: int,
    ai_retries: int,
    page_text_max_chars: int,
) -> CrawlOutcome:
    url = BASE_URL.format(n=test_num)
    try:
        html = fetch_test_page(url)
        test = parse_reading_test(html, url)

        det = validate_reading_test(test)
        if not det.valid:
            return CrawlOutcome(test_num, False, f"Deterministic validation failed: {det.report()}")

        repair_report = None

        if ai_validate_only or ai_auto:
            if not project:
                return CrawlOutcome(test_num, False, "Missing --project for AI mode")
            ai_result = _run_ai_validate_with_retries(
                test,
                html,
                project=project,
                model=validate_model,
                timeout_s=ai_timeout_s,
                retries=ai_retries,
                page_text_max_chars=page_text_max_chars,
            )
            if not ai_result.get("valid", False):
                if ai_validate_only and not ai_auto:
                    issues = "; ".join(ai_result.get("issues", [])[:3])
                    return CrawlOutcome(test_num, False, f"AI validation failed: {issues}")
                # ai_auto: fall through to repair
            else:
                # AI says OK; in ai_auto we skip repair to save cost/latency.
                if ai_auto:
                    saved_json = _save_json(out_dir, test)
                    return CrawlOutcome(test_num, True, "Saved (ai_auto: validate OK, skipped repair)", saved_json=saved_json)

        if ai_repair_always or ai_auto:
            if not project:
                return CrawlOutcome(test_num, False, "Missing --project for AI mode")
            repaired, repair_report = _run_ai_repair_with_retries(
                test,
                html,
                project=project,
                model=repair_model,
                timeout_s=ai_timeout_s,
                retries=ai_retries,
                page_text_max_chars=page_text_max_chars,
            )
            post = validate_repaired_reading_test(test, repaired)
            if not post.valid:
                return CrawlOutcome(test_num, False, f"Post-repair validation failed: {post.report()}")
            test = repaired

        saved_json = _save_json(out_dir, test)
        saved_report = None
        if repair_report is not None:
            saved_report = _save_report(out_dir, test.id, repair_report)
        return CrawlOutcome(test_num, True, "Saved", saved_json=saved_json, saved_report=saved_report)
    except Exception as e:
        return CrawlOutcome(test_num, False, f"Exception: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch crawl IELTS reading tests")
    parser.add_argument("start", type=int, help="Start test number (inclusive)")
    parser.add_argument("end", type=int, help="End test number (inclusive)")
    parser.add_argument("--output", default="../frontend/src/data/tests/",
                        help="Output directory for JSON files")

    ai_mode = parser.add_mutually_exclusive_group()
    ai_mode.add_argument("--ai-validate", action="store_true",
                         help="Run AI validation only (diagnostic gate; fails on invalid)")
    ai_mode.add_argument("--ai-repair", action="store_true",
                         help="Run AI repair/polish for every test before saving")
    ai_mode.add_argument("--ai-auto", action="store_true",
                         help="Run AI validation first; only repair if invalid (faster/cheaper)")

    parser.add_argument("--project", default=None,
                        help="GCP project ID for Vertex AI (required with AI modes)")
    parser.add_argument("--workers", type=int, default=3,
                        help="Number of concurrent tests to crawl (default: 3)")
    parser.add_argument("--ai-timeout-s", type=int, default=120,
                        help="Timeout for a single AI call (default: 120s)")
    parser.add_argument("--ai-retries", type=int, default=1,
                        help="Retries for AI calls after timeout/error (default: 1)")
    parser.add_argument("--ai-validate-model", default="gemini-2.5-pro",
                        help="Vertex model for AI validation (default: gemini-2.5-pro)")
    parser.add_argument("--ai-repair-model", default="gemini-2.5-pro",
                        help="Vertex model for AI repair (default: gemini-2.5-pro)")
    parser.add_argument("--page-text-max-chars", type=int, default=12000,
                        help="Max chars of source page text to send to AI (default: 12000)")

    args = parser.parse_args()
    out_dir = Path(args.output)

    if (args.ai_validate or args.ai_repair or args.ai_auto) and not args.project:
        print("Error: --project is required for AI modes")
        sys.exit(2)

    test_nums = list(range(args.start, args.end + 1))
    outcomes: list[CrawlOutcome] = []

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        futs = [
            ex.submit(
                crawl_one,
                n,
                out_dir,
                args.project,
                args.ai_validate,
                args.ai_repair,
                args.ai_auto,
                args.ai_validate_model,
                args.ai_repair_model,
                args.ai_timeout_s,
                args.ai_retries,
                args.page_text_max_chars,
            )
            for n in test_nums
        ]
        for fut in as_completed(futs):
            outcome = fut.result()
            outcomes.append(outcome)
            status = "OK" if outcome.ok else "FAIL"
            print(f"[{status}] test-{outcome.test_num}: {outcome.message}")

    outcomes.sort(key=lambda o: o.test_num)
    failed = [o for o in outcomes if not o.ok]
    print(f"Done: {len(outcomes) - len(failed)}/{len(outcomes)} succeeded")
    if failed:
        print("Failures:")
        for o in failed:
            print(f"- test-{o.test_num}: {o.message}")
        sys.exit(1)


if __name__ == "__main__":
    main()

