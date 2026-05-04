import unittest
from pathlib import Path

from parser import _build_question_groups, parse_reading_test
from validator import validate_reading_test

FIXTURES_DIR = Path(__file__).parent / "fixtures"


HTML = """
<html>
  <body>
    <div class="entry-content">
      <p>William Henry Perkin</p>
      <p>Passage one paragraph alpha. Passage one paragraph alpha. Passage one paragraph alpha. Passage one paragraph alpha. Passage one paragraph alpha. Passage one paragraph alpha. Passage one paragraph alpha. Passage one paragraph alpha. Passage one paragraph alpha.</p>
      <p>Questions 1-7</p>
      <p>1 First question.</p>
      <p>Questions 8-13</p>
      <p>Write your answers in boxes 8-13 on your answer sheet.</p>
      <p>8 Eighth question.</p>
      <p></p>
      <p>Cambridge IELTS Test 1 to 17</p>
      <p>Is There Anybody Out There?</p>
      <p>A Passage two paragraph alpha. Passage two paragraph alpha. Passage two paragraph alpha. Passage two paragraph alpha. Passage two paragraph alpha. Passage two paragraph alpha. Passage two paragraph alpha. Passage two paragraph alpha. Passage two paragraph alpha. Passage two paragraph alpha. Passage two paragraph alpha. Passage two paragraph alpha. Passage two paragraph alpha. Passage two paragraph alpha.</p>
      <p>B Passage two paragraph beta. Passage two paragraph beta. Passage two paragraph beta. Passage two paragraph beta. Passage two paragraph beta. Passage two paragraph beta. Passage two paragraph beta. Passage two paragraph beta. Passage two paragraph beta. Passage two paragraph beta. Passage two paragraph beta. Passage two paragraph beta. Passage two paragraph beta. Passage two paragraph beta.</p>
      <p>Questions 14—17
      Reading Passage 2 has ﬁve paragraphs, A-E. Choose the correct heading for paragraphs B-E from the headings below.</p>
      <p>List of Headings
      i. Seeking the transmission of radio signals from planets
      ii. Appropriate responses to signals from other civilizations
      iii. Vast distances to Earth’s closest neighbors
      iv. Assumptions underlying the search for extra-terrestrial intelligence
      v. Reasons for the search for extra-terrestrial intelligence
      vi. Knowledge of extra-terrestrial life forms
      vii. Likelihood of life on other planets</p>
      <p>14. Paragraph B</p>
      <p>Questions 18-20</p>
      <p>18. What is the life expectancy of Earth?</p>
      <p>Questions 21-26</p>
      <p>TRUE if the statement agrees with the information</p>
      <p>21. Alien civilizations may be able to help the human race to overcome serious problems.</p>
      <p></p>
      <p>The History of the Tortoise</p>
      <p>Passage three paragraph alpha. Passage three paragraph alpha. Passage three paragraph alpha. Passage three paragraph alpha. Passage three paragraph alpha. Passage three paragraph alpha. Passage three paragraph alpha. Passage three paragraph alpha. Passage three paragraph alpha.</p>
      <p>Questions 27-30</p>
      <p>27. What had to transfer from sea to land before any animals could migrate?</p>
      <p>Show Answers</p>
      <div id="bg-showmore-hidden-1">
        <p>1. true</p>
        <p>8. rich</p>
        <p>14. iv</p>
        <p>18. several billion years</p>
        <p>21. true</p>
        <p>27. plants</p>
      </div>
    </div>
  </body>
</html>
"""


class ParserRegressionTests(unittest.TestCase):
    def test_detects_passage_after_interstitial_noise_and_em_dash_question_range(self):
        test = parse_reading_test(HTML, "https://practicepteonline.com/ielts-reading-test-3/")

        self.assertEqual(len(test.passages), 3)
        # New pipeline correctly detects "William Henry Perkin" as passage-1 title
        self.assertEqual(test.passages[0].title, "William Henry Perkin")
        self.assertEqual(test.passages[1].title, "Is There Anybody Out There?")
        self.assertEqual(test.passages[2].title, "The History of the Tortoise")

        groups_by_id = {group.id: group for group in test.question_groups}
        self.assertIn("group-14-17", groups_by_id)
        self.assertEqual(groups_by_id["group-14-17"].passage_id, "passage-2")
        self.assertIn("vii", groups_by_id["group-14-17"].options or {})
        self.assertEqual(groups_by_id["group-18-20"].passage_id, "passage-2")
        self.assertEqual(groups_by_id["group-21-26"].passage_id, "passage-2")
        self.assertEqual(groups_by_id["group-27-30"].passage_id, "passage-3")
        self.assertNotIn("Cambridge IELTS Test 1 to 17", groups_by_id["group-8-13"].shared_text or "")

    def test_excludes_shared_text_that_starts_with_show_answers(self):
        groups = _build_question_groups(
            [{
                "start": 40,
                "end": 40,
                "instruction": "Question 40\nChoose the correct letter A, B, C or D.",
                "text": "Show Answers\n1. A\n2. B",
                "passage_id": "passage-1",
                "image_url": None,
            }],
            {40: "A"},
        )

        self.assertEqual(len(groups), 1)
        self.assertIsNone(groups[0].shared_text)

    def test_detects_passage_after_cambridge_block_without_empty_separator(self):
        html = """
        <html>
          <body>
            <div class="entry-content">
              <p>Passage One</p>
              <p>Passage one paragraph alpha. Passage one paragraph alpha. Passage one paragraph alpha. Passage one paragraph alpha. Passage one paragraph alpha. Passage one paragraph alpha. Passage one paragraph alpha. Passage one paragraph alpha. Passage one paragraph alpha.</p>
              <p>Questions 1-2</p>
              <p>1 First question.</p>
              <p>Cambridge IELTS Test 1 to 17</p>
              <p>The Little Ice Age</p>
              <p>A Passage two paragraph alpha. Passage two paragraph alpha. Passage two paragraph alpha. Passage two paragraph alpha. Passage two paragraph alpha. Passage two paragraph alpha. Passage two paragraph alpha. Passage two paragraph alpha. Passage two paragraph alpha. Passage two paragraph alpha. Passage two paragraph alpha. Passage two paragraph alpha. Passage two paragraph alpha. Passage two paragraph alpha.</p>
              <p>Questions 3-4</p>
              <p>3 Third question.</p>
              <p>Show Answers</p>
              <div id="bg-showmore-hidden-1">
                <p>1. A</p>
                <p>3. B</p>
              </div>
            </div>
          </body>
        </html>
        """

        test = parse_reading_test(html, "https://practicepteonline.com/ielts-reading-test-6/")

        self.assertEqual(len(test.passages), 2)
        self.assertEqual(test.passages[1].title, "The Little Ice Age")
        groups_by_id = {group.id: group for group in test.question_groups}
        self.assertEqual(groups_by_id["group-3-4"].passage_id, "passage-2")

    def test_resolves_relative_image_urls_against_source_page(self):
        html = """
        <html>
          <body>
            <div class="entry-content">
              <p>Diagram Passage</p>
              <p>This is a long passage paragraph. This is a long passage paragraph. This is a long passage paragraph. This is a long passage paragraph. This is a long passage paragraph.</p>
              <p>Questions 1-2<br/>Label the diagram below.</p>
              <p><img data-src="/wp-content/uploads/2024/09/test-relative.png" alt="" /></p>
              <p>1. A</p>
              <p>2. B</p>
              <p>Show Answers</p>
              <div id="bg-showmore-hidden-1">
                <p>1. A</p>
                <p>2. B</p>
              </div>
            </div>
          </body>
        </html>
        """

        test = parse_reading_test(html, "https://practicepteonline.com/ielts-reading-test-11/")
        group = next(g for g in test.question_groups if g.id == "group-1-2")
        self.assertEqual(
            group.image_url,
            "https://practicepteonline.com/wp-content/uploads/2024/09/test-relative.png",
        )


class FixtureRegressionTests(unittest.TestCase):
    """Regression tests against saved raw HTML fixtures.

    Each test loads a real captured HTML file, parses it, and runs the
    deterministic validator. All 10 tests must produce valid output.
    """

    def _assert_fixture_valid(self, test_num: int):
        fixture = FIXTURES_DIR / f"test-{test_num}.html"
        if not fixture.exists():
            self.skipTest(f"Fixture not found: {fixture}")
        html = fixture.read_text(encoding="utf-8")
        url = f"https://practicepteonline.com/ielts-reading-test-{test_num}/"
        test = parse_reading_test(html, url)
        result = validate_reading_test(test)
        self.assertTrue(
            result.valid,
            msg=f"test-{test_num} failed validation:\n{result.report()}"
        )

    def test_fixture_01(self): self._assert_fixture_valid(1)
    def test_fixture_02(self): self._assert_fixture_valid(2)
    def test_fixture_03(self): self._assert_fixture_valid(3)
    def test_fixture_04(self): self._assert_fixture_valid(4)
    def test_fixture_05(self): self._assert_fixture_valid(5)
    def test_fixture_06(self): self._assert_fixture_valid(6)
    def test_fixture_07(self): self._assert_fixture_valid(7)
    def test_fixture_08(self): self._assert_fixture_valid(8)
    def test_fixture_09(self): self._assert_fixture_valid(9)
    def test_fixture_10(self): self._assert_fixture_valid(10)

if __name__ == "__main__":
    unittest.main()
