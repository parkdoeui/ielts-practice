import json
from pathlib import Path

import pytest

from migrate_writing_answers_json import convert_answers_json, load_prompts


def test_convert_answers_json_adds_prompts() -> None:
    converted = convert_answers_json(
        {"1": "Task 1 answer", "2": "Task 2 answer"},
        {"1": "Task 1 prompt", "2": "Task 2 prompt"},
    )

    assert converted == {
        "task1": {"prompt": "Task 1 prompt", "answer": "Task 1 answer"},
        "task2": {"prompt": "Task 2 prompt", "answer": "Task 2 answer"},
    }


def test_convert_answers_json_skips_migrated_shape() -> None:
    migrated = {
        "task1": {"prompt": "Existing prompt 1", "answer": "Existing answer 1"},
        "task2": {"prompt": "Existing prompt 2", "answer": "Existing answer 2"},
    }

    assert convert_answers_json(migrated, {"1": "New prompt 1", "2": "New prompt 2"}) == migrated


def test_load_prompts_requires_prompt_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_prompts("writing-test-99", tmp_path)


def test_load_prompts_reads_static_writing_test_json(tmp_path: Path) -> None:
    test_path = tmp_path / "writing-test-1.json"
    test_path.write_text(
        json.dumps(
            {
                "tasks": [
                    {"task_number": 1, "prompt": "Task 1 prompt"},
                    {"task_number": 2, "prompt": "Task 2 prompt"},
                ]
            }
        ),
        encoding="utf-8",
    )

    assert load_prompts("writing-test-1", tmp_path) == {
        "1": "Task 1 prompt",
        "2": "Task 2 prompt",
    }
