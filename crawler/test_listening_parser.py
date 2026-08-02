from pathlib import Path

import pytest

from listening_parser import parse_listening_test
from listening_validator import validate_listening_test


FIXTURE = Path(__file__).parent / "fixtures" / "listening-test-208.html"
SOURCE_URL = "https://practicepteonline.com/ielts-listening-test-208/"


def _fixture_test():
    return parse_listening_test(FIXTURE.read_text(encoding="utf-8"), SOURCE_URL)


def test_parse_listening_fixture_208() -> None:
    test = _fixture_test()
    result = validate_listening_test(test)
    questions = {question.id: question for group in test.question_groups for question in group.questions}

    assert result.valid, result.report()
    assert test.id == "listening-test-208"
    assert test.title == "IELTS Listening Test 208"
    assert len(test.parts) == 4
    assert [part.number for part in test.parts] == [1, 2, 3, 4]
    assert set(questions) == set(range(1, 41))
    assert test.audio_url.startswith("https://")
    assert test.audio_url.endswith("208_we.mp3")
    assert {number: questions[number].answer for number in (1, 11, 12, 15, 21, 24, 40)} == {
        1: "Leigh",
        11: "C",
        12: "E",
        15: "C",
        21: "B",
        24: "B",
        40: "Volume",
    }

    by_part = {part_id: [group.type for group in test.question_groups if group.passage_id == part_id] for part_id in {"part-1", "part-2", "part-3", "part-4"}}
    assert by_part["part-1"] == ["note-completion"]
    assert by_part["part-2"] == ["multiple-choice", "multiple-choice", "matching"]
    assert by_part["part-3"] == ["multiple-choice", "matching"]
    assert by_part["part-4"] == ["note-completion"]

    multi_groups = [group for group in test.question_groups if group.passage_id == "part-2" and group.type == "multiple-choice"]
    assert multi_groups[0].options and set(multi_groups[0].options) == {"A", "B", "C", "D", "E"}
    assert multi_groups[1].options and set(multi_groups[1].options) == {"A", "B", "C", "D", "E"}


def test_missing_root_or_audio_raises() -> None:
    with pytest.raises(ValueError, match="entry-content"):
        parse_listening_test("<html><body><p>nothing</p></body></html>", SOURCE_URL)

    with pytest.raises(ValueError, match="audio"):
        parse_listening_test("<div class='entry-content'><p>Part 1</p></div>", SOURCE_URL)


def test_validator_rejects_missing_question_and_options() -> None:
    test = _fixture_test()
    groups = [group.model_copy(deep=True) for group in test.question_groups]
    groups[-1].questions = groups[-1].questions[:-1]
    groups[1].options = None
    broken = test.model_copy(update={"question_groups": groups})

    result = validate_listening_test(broken)

    assert not result.valid
    assert any("Missing question ids" in error for error in result.errors)
    assert any("requires non-empty options" in error for error in result.errors)
