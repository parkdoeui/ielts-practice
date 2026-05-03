#!/usr/bin/env python3
"""
HTML capture script — saves raw page HTML to a fixture file for regression testing.

Usage:
  python capture.py <url>
  python capture.py <url> --output fixtures/
"""
import argparse
import re
import sys
from pathlib import Path

from scraper import fetch_test_page


def capture(url: str, output_dir: str = "fixtures") -> Path:
    html = fetch_test_page(url)

    match = re.search(r'test-(\d+)', url)
    test_id = f"test-{match.group(1)}" if match else "test-unknown"

    out = Path(output_dir) / f"{test_id}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out


def main():
    parser = argparse.ArgumentParser(description="Save raw HTML from a URL to a fixture file")
    parser.add_argument("url", help="URL to capture")
    parser.add_argument("--output", default="fixtures", help="Output directory (default: fixtures/)")
    args = parser.parse_args()

    print(f"Fetching: {args.url}")
    path = capture(args.url, args.output)
    print(f"Saved: {path}")


if __name__ == "__main__":
    main()
