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


def test_parse_writing_task_1_table() -> None:
    html = """
    <html>
      <body>
        <h1 class="entry-title">IELTS Writing Test 10</h1>
        <div class="entry-content">
          <p><strong><u>Task 1:</u></strong> The table below gives information about rail systems.</p>
          <p>Summarise the information by selecting and reporting the main features, and make comparisons where relevant. Write at least 150 words.</p>
          <figure>
            <table>
              <tr><th>City</th><th>Date opened</th><th>Passengers</th></tr>
              <tr><td>London</td><td>1863</td><td>775</td></tr>
              <tr><td>Paris</td><td>1900</td><td>1191</td></tr>
            </table>
          </figure>
          <p><strong><u>Task 2</u></strong><strong>:</strong> Some people think wealth should be used to help others. To what extent do you agree or disagree?</p>
          <p>Write at least 250 words.</p>
        </div>
      </body>
    </html>
    """
    test = parse_writing_test(html, "https://practicepteonline.com/ielts-writing-test-10/")
    result = validate_writing_test(test)

    assert result.valid, result.report()
    assert test.tasks[0].image_url is None
    assert test.tasks[0].table == [
        ["City", "Date opened", "Passengers"],
        ["London", "1863", "775"],
        ["Paris", "1900", "1191"],
    ]
