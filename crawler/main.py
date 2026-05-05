#!/usr/bin/env python3
"""
IELTS Reading Test Crawler

Usage:
  python main.py crawl <url> --output <path>
  python main.py crawl <url> --output <path> --ai-validate --project <gcp-project>
  python main.py crawl <url> --output <path> --ai-auto --project <gcp-project>
  python main.py inspect <url>              # Print raw HTML for debugging
"""
import json
import sys
import argparse
from pathlib import Path
from typing import Optional

from scraper import fetch_test_page
from parser import parse_reading_test
from validator import validate_reading_test


def _validate_or_exit(test, label: str = "Validation") -> None:
    result = validate_reading_test(test)
    if result.warnings:
        for w in result.warnings:
            print(f"  ⚠ {w}")
    if not result.valid:
        print(f"{label} FAILED — aborting save:")
        for e in result.errors:
            print(f"  ✗ {e}")
        sys.exit(1)
    print(f"{label}: OK")


def cmd_crawl(
    url: str,
    output_dir: str,
    ai_validate: bool = False,
    ai_repair: bool = False,
    ai_auto: bool = False,
    project: Optional[str] = None,
    ai_validate_model: str = "gemini-2.5-pro",
    ai_repair_model: str = "gemini-2.5-pro",
    page_text_max_chars: int = 12000,
) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"Fetching: {url}")
    html = fetch_test_page(url)

    print("Parsing...")
    test = parse_reading_test(html, url)

    # --- Deterministic validation (always runs) ---
    _validate_or_exit(test, label="Validation")

    # --- AI auto: validate first, repair only if invalid ---
    repair_report = None
    if ai_auto:
        if not project:
            print("Error: --project is required when using --ai-auto")
            sys.exit(1)
        print("Running AI validation (auto mode)...")
        from ai_validator import ai_validate as run_ai_validate
        ai_result = run_ai_validate(
            test,
            html,
            project=project,
            model=ai_validate_model,
            page_text_max_chars=page_text_max_chars,
        )
        conf = ai_result.get("confidence", 0.0)
        if ai_result.get("valid", False):
            print(f"AI validation: OK (confidence: {conf:.2f}) — skipping repair")
        else:
            print(f"AI validation: FAILED (confidence: {conf:.2f}) — running repair")
            from ai_repair import ai_repair as run_ai_repair
            from validator import validate_repaired_reading_test

            try:
                repaired, repair_report = run_ai_repair(
                    test,
                    html,
                    project=project,
                    model=ai_repair_model,
                    page_text_max_chars=page_text_max_chars,
                )
            except Exception as e:
                print(f"AI repair FAILED — aborting save: {e}")
                sys.exit(1)
            post = validate_repaired_reading_test(test, repaired)
            if post.warnings:
                for w in post.warnings:
                    print(f"  ⚠ {w}")
            if not post.valid:
                print("Post-AI-repair validation FAILED — aborting save:")
                for e in post.errors:
                    print(f"  ✗ {e}")
                sys.exit(1)
            test = repaired
            changes = repair_report.get("changes", []) if isinstance(repair_report, dict) else []
            conf = repair_report.get("confidence", 0.0) if isinstance(repair_report, dict) else 0.0
            print(f"AI repair: OK (confidence: {conf:.2f}, changes: {len(changes)})")

    # --- AI repair (optional, requires --ai-repair and --project) ---
    elif ai_repair:
        if not project:
            print("Error: --project is required when using --ai-repair")
            sys.exit(1)
        print("Running AI repair...")
        from ai_repair import ai_repair as run_ai_repair
        from validator import validate_repaired_reading_test

        try:
            repaired, repair_report = run_ai_repair(
                test,
                html,
                project=project,
                model=ai_repair_model,
                page_text_max_chars=page_text_max_chars,
            )
        except Exception as e:
            print(f"AI repair FAILED — aborting save: {e}")
            sys.exit(1)
        post = validate_repaired_reading_test(test, repaired)
        if post.warnings:
            for w in post.warnings:
                print(f"  ⚠ {w}")
        if not post.valid:
            print("Post-AI-repair validation FAILED — aborting save:")
            for e in post.errors:
                print(f"  ✗ {e}")
            sys.exit(1)
        test = repaired
        changes = repair_report.get("changes", []) if isinstance(repair_report, dict) else []
        conf = repair_report.get("confidence", 0.0) if isinstance(repair_report, dict) else 0.0
        print(f"AI repair: OK (confidence: {conf:.2f}, changes: {len(changes)})")

    # --- AI validation (optional, requires --ai-validate and --project) ---
    elif ai_validate:
        if not project:
            print("Error: --project is required when using --ai-validate")
            sys.exit(1)
        print("Running AI validation...")
        from ai_validator import ai_validate as run_ai_validate
        ai_result = run_ai_validate(
            test,
            html,
            project=project,
            model=ai_validate_model,
            page_text_max_chars=page_text_max_chars,
        )
        conf = ai_result.get("confidence", 0.0)
        if not ai_result.get("valid", False):
            print(f"AI validation FAILED (confidence: {conf:.2f}) — aborting save:")
            for issue in ai_result.get("issues", []):
                print(f"  ✗ {issue}")
            sys.exit(1)
        print(f"AI validation: OK (confidence: {conf:.2f})")
        if ai_result.get("issues"):
            for issue in ai_result["issues"]:
                print(f"  ⚠ AI: {issue}")

    filename = f"{test.id}.json"
    filepath = output_path / filename

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(test.model_dump(), f, indent=2, ensure_ascii=False)

    if repair_report is not None:
        report_path = output_path / f"{test.id}.repair-report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(repair_report, f, indent=2, ensure_ascii=False)

    total_qs = sum(len(g.questions) for g in test.question_groups)
    print(f"Saved: {filepath}")
    print(f"Passages: {len(test.passages)}, Groups: {len(test.question_groups)}, Questions: {total_qs}")


def cmd_inspect(url: str) -> None:
    """Print page HTML for debugging parser selectors."""
    print(f"Fetching: {url}")
    html = fetch_test_page(url)
    print(html[:5000])
    print("\n... (truncated)")


def main():
    parser = argparse.ArgumentParser(description="IELTS Reading Test Crawler")
    subparsers = parser.add_subparsers(dest="command")

    crawl_cmd = subparsers.add_parser("crawl", help="Crawl and save a test")
    crawl_cmd.add_argument("url", help="URL of the IELTS test page")
    crawl_cmd.add_argument("--output", default="../frontend/src/data/tests/",
                          help="Output directory for JSON files")
    ai_mode = crawl_cmd.add_mutually_exclusive_group()
    ai_mode.add_argument("--ai-validate", action="store_true",
                         help="Run AI validation via Vertex AI (Gemini 2.5 Pro)")
    ai_mode.add_argument("--ai-repair", action="store_true",
                         help="Run AI repair/polish via Vertex AI (Gemini 2.5 Pro) before saving")
    ai_mode.add_argument("--ai-auto", action="store_true",
                         help="Run AI validation then repair only if invalid (faster/cheaper)")
    crawl_cmd.add_argument("--project", default=None,
                          help="GCP project ID for Vertex AI (required with --ai-validate/--ai-repair/--ai-auto)")
    crawl_cmd.add_argument("--ai-validate-model", default="gemini-2.5-pro",
                          help="Vertex model for AI validation (default: gemini-2.5-pro)")
    crawl_cmd.add_argument("--ai-repair-model", default="gemini-2.5-pro",
                          help="Vertex model for AI repair (default: gemini-2.5-pro)")
    crawl_cmd.add_argument("--page-text-max-chars", type=int, default=12000,
                          help="Max chars of page text to send to AI (default: 12000)")

    inspect_cmd = subparsers.add_parser("inspect", help="Print raw HTML for debugging")
    inspect_cmd.add_argument("url", help="URL to inspect")

    args = parser.parse_args()

    if args.command == "crawl":
        cmd_crawl(
            args.url,
            args.output,
            ai_validate=args.ai_validate,
            ai_repair=args.ai_repair,
            ai_auto=args.ai_auto,
            project=args.project,
            ai_validate_model=args.ai_validate_model,
            ai_repair_model=args.ai_repair_model,
            page_text_max_chars=args.page_text_max_chars,
        )
    elif args.command == "inspect":
        cmd_inspect(args.url)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
