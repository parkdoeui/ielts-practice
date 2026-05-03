#!/usr/bin/env python3
"""
IELTS Reading Test Crawler

Usage:
  python main.py crawl <url> --output <path>
  python main.py inspect <url>              # Print raw HTML for debugging
"""
import json
import sys
import argparse
from pathlib import Path

from scraper import fetch_test_page
from parser import parse_reading_test


def cmd_crawl(url: str, output_dir: str) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"Fetching: {url}")
    html = fetch_test_page(url)

    print("Parsing...")
    test = parse_reading_test(html, url)

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
    # Print first 5000 chars to avoid overwhelming output
    print(html[:5000])
    print("\n... (truncated)")


def main():
    parser = argparse.ArgumentParser(description="IELTS Reading Test Crawler")
    subparsers = parser.add_subparsers(dest="command")

    crawl_cmd = subparsers.add_parser("crawl", help="Crawl and save a test")
    crawl_cmd.add_argument("url", help="URL of the IELTS test page")
    crawl_cmd.add_argument("--output", default="../frontend/src/data/tests/",
                          help="Output directory for JSON files")

    inspect_cmd = subparsers.add_parser("inspect", help="Print raw HTML for debugging")
    inspect_cmd.add_argument("url", help="URL to inspect")

    args = parser.parse_args()

    if args.command == "crawl":
        cmd_crawl(args.url, args.output)
    elif args.command == "inspect":
        cmd_inspect(args.url)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
