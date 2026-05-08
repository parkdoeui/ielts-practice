from pathlib import Path

from writing_parser import parse_writing_test
from writing_validator import validate_writing_test


def test_parse_writing_fixture_test_1() -> None:
    html = Path(__file__).with_name("fixtures").joinpath("writing-test-1.html").read_text(encoding="utf-8")
    test = parse_writing_test(html, "https://practicepteonline.com/ielts-writing-test-1/")
    result = validate_writing_test(test)

    assert result.valid, result.report()
    assert test.id == "writing-test-1"
    assert len(test.tasks) == 2
    assert test.tasks[0].task_number == 1
    assert test.tasks[1].task_number == 2
    assert test.tasks[0].min_words == 150
    assert test.tasks[1].min_words == 250
    assert test.tasks[0].image_url and test.tasks[0].image_url.startswith("https://practicepteonline.com/")
