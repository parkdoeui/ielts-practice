#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from database import SessionLocal
from models import WritingSessionRecord


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WRITING_TESTS_DIR = PROJECT_ROOT / "frontend" / "src" / "data" / "writing-tests"


def is_migrated(value: Any) -> bool:
    return isinstance(value, dict) and "task1" in value and "task2" in value


def load_prompts(test_id: str, writing_tests_dir: Path = WRITING_TESTS_DIR) -> dict[str, str]:
    if not re.fullmatch(r"writing-test-\d+", test_id):
        raise ValueError(f"Unsupported writing test id: {test_id}")

    path = writing_tests_dir / f"{test_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing writing test JSON for {test_id}: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    prompts: dict[str, str] = {}
    for task in data.get("tasks", []):
        task_number = str(task.get("task_number", ""))
        prompt = str(task.get("prompt", "")).strip()
        if task_number in {"1", "2"} and prompt:
            prompts[task_number] = prompt

    if set(prompts) != {"1", "2"}:
        raise ValueError(f"Missing Task 1/Task 2 prompts in {path}")
    return prompts


def convert_answers_json(old_value: Any, prompts: dict[str, str]) -> dict[str, dict[str, str]]:
    if is_migrated(old_value):
        return old_value
    if not isinstance(old_value, dict):
        raise ValueError("answers_json must be a JSON object")

    return {
        "task1": {
            "prompt": prompts["1"],
            "answer": str(old_value.get("1", "")).strip(),
        },
        "task2": {
            "prompt": prompts["2"],
            "answer": str(old_value.get("2", "")).strip(),
        },
    }


def migrate(dry_run: bool = False, writing_tests_dir: Path = WRITING_TESTS_DIR) -> tuple[int, int]:
    db = SessionLocal()
    migrated = 0
    skipped = 0
    try:
        records = db.query(WritingSessionRecord).order_by(WritingSessionRecord.completed_at.asc()).all()
        for record in records:
            if is_migrated(record.answers_json):
                skipped += 1
                continue
            prompts = load_prompts(record.test_id, writing_tests_dir)
            converted = convert_answers_json(record.answers_json, prompts)
            migrated += 1
            if not dry_run:
                record.answers_json = converted

        if dry_run:
            db.rollback()
        else:
            db.commit()
    finally:
        db.close()

    return migrated, skipped


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate writing_sessions.answers_json from {'1','2'} to task prompt/answer objects."
    )
    parser.add_argument("--dry-run", action="store_true", help="Report changes without writing to the database")
    parser.add_argument(
        "--writing-tests-dir",
        type=Path,
        default=WRITING_TESTS_DIR,
        help="Directory containing writing-test-<N>.json prompt files",
    )
    args = parser.parse_args()

    migrated, skipped = migrate(dry_run=args.dry_run, writing_tests_dir=args.writing_tests_dir)
    action = "Would migrate" if args.dry_run else "Migrated"
    print(f"{action} {migrated} writing session(s); skipped {skipped} already migrated session(s).")


if __name__ == "__main__":
    main()
