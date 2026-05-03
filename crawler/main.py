#!/usr/bin/env python3
"""
IELTS Reading Test Crawler

Usage:
  python main.py crawl <url> --output <path>
  python main.py crawl <url> --output <path> --ai-validate --project <gcp-project>
  python main.py inspect <url>              # Print raw HTML for debugging
"""
import json
import sys
import argparse
from pathlib import Path

from scraper import fetch_test_page
from parser import parse_reading_test
from validator import validate_reading_test


def cmd_crawl(url: str, output_dir: str, ai_validate: bool = False, project: str | None = None) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"Fetching: {url}")
    html = fetch_test_page(url)

    print("Parsing...")
    test = parse_reading_test(html, url)

    # --- Deterministic validation (always runs) ---
    result = validate_reading_test(test)
    if result.warnings:
        for w in result.warnings:
            print(f"  ⚠ {w}")
    if not result.valid:
        print("Validation FAILED — aborting save:")
        for e in result.errors:
            print(f"  ✗ {e}")
        sys.exit(1)
    print("Validation: OK")

    # --- AI validation (optional, requires --ai-validate and --project) ---
    if ai_validate:
        if not project:
            print("Error: --project is required when using --ai-validate")
            sys.exit(1)
        print("Running AI validation...")
        from ai_validator import ai_validate as run_ai_validate
        ai_result = run_ai_validate(test, html, project=project)
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
    crawl_cmd.add_argument("--ai-validate", action="store_true",
                          help="Run AI validation via Vertex AI (Gemini 2.5 Pro)")
    crawl_cmd.add_argument("--project", default=None,
                          help="GCP project ID for Vertex AI (required with --ai-validate)")

    inspect_cmd = subparsers.add_parser("inspect", help="Print raw HTML for debugging")
    inspect_cmd.add_argument("url", help="URL to inspect")

    args = parser.parse_args()

    if args.command == "crawl":
        cmd_crawl(
            args.url,
            args.output,
            ai_validate=args.ai_validate,
            project=args.project,
        )
    elif args.command == "inspect":
        cmd_inspect(args.url)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
