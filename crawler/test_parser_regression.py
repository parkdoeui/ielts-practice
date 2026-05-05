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

    def test_sentence_completion_does_not_leak_instruction_text_into_shared_text(self):
        groups = _build_question_groups(
            [{
                "start": 9,
                "end": 14,
                "instruction": "Questions 9–14",
                "text": (
                    "Complete the sentences below. Write\n"
                    "NO MORE THAN TWO WORDS\n"
                    "from the passage for each answer.\n"
                    "9. Niel’s colleagues describe him as a………………………….. person.\n"
                    "10. Only a small fraction of people have imagination as…………………………. as Lauren does.\n"
                    "11. Hyperphantasia is………………………. to aphantasia.\n"
                    "12. Many people spend their lives with……………………………. somewhere in the mind’s eye.\n"
                    "13. Prof Zeman is………………………………. that aphantasia is not an illness.\n"
                    "14. Prof Zeman strongly believes that aphantasia is not a………………"
                ),
                "passage_id": "passage-1",
                "image_url": None,
            }],
            {9: "weird", 10: "vibrant", 11: "polar-opposite", 12: "imagery hovering", 13: "adamant", 14: "disorder"},
        )

        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].type, "sentence-completion")
        self.assertIsNone(groups[0].shared_text)

    def test_table_completion_parenthesized_blanks_stay_empty(self):
        groups = _build_question_groups(
            [{
                "start": 5,
                "end": 8,
                "instruction": "Questions 5-8\nComplete the table below. Choose\nNO MORE THAN THREE WORDS\nfrom Reading Passage 1 for each answer.",
                "text": (
                    "Country\nOrganisations involved\nType of project\nSupport provided\n"
                    "(5)……………… and ……….\n"
                    "– S.K.I.\n"
                    "courier service\n"
                    "– provision of (6)…………….\n"
                    "Dominican Republic\n"
                    "– S.K.I\n"
                    "– Y.W.C.A.\n"
                    "(7)…………………\n"
                    "– loans\n"
                    "– storage facilities\n"
                    "– saving plans\n"
                    "Zambia\n"
                    "– S.K.I.\n"
                    "– The Red Cross\n"
                    "– Y.W.C.A.\n"
                    "setting up small business\n"
                    "– business training\n"
                    "– (8)……………. training\n"
                    "– access to credit"
                ),
                "passage_id": "passage-1",
                "image_url": None,
            }],
            {5: "sudan and india", 6: "bicycles", 7: "shoe shine", 8: "life skills"},
        )

        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].type, "sentence-completion")
        self.assertEqual(groups[0].questions[0].statement, "")
        self.assertIn("Support provided", groups[0].shared_text or "")

    def test_paragraph_matching_is_not_summary_completion(self):
        groups = _build_question_groups(
            [{
                "start": 27,
                "end": 31,
                "instruction": (
                    "Questions 27-31\n"
                    "Reading Passage 3 has seven paragraphs labeled A-G. Which paragraph contains the following information?\n"
                    "Write the correct letter A-G in boxes 27-31 on your answer sheet. NB You may use any letter more than once."
                ),
                "text": (
                    "27 the effect of recording on the way people talk\n"
                    "28 the importance of taking notes on body language\n"
                    "29 the fact that language is influenced by social situation\n"
                    "30 how informants can be helped to be less self-conscious\n"
                    "31 various methods that can be used to generate specific data"
                ),
                "passage_id": "passage-1",
                "image_url": None,
            }],
            {27: "D", 28: "E", 29: "C", 30: "D", 31: "F"},
        )

        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].type, "matching-information")

    def test_inline_numbered_statements_are_extracted_from_instruction(self):
        groups = _build_question_groups(
            [{
                "start": 8,
                "end": 13,
                "instruction": (
                    "Questions 8-13\n"
                    "Do the following statements agree with the information given in Reading Passage 1? In boxes 8-13 on your answer sheet, write\n"
                    "TRUE\n"
                    "if the statement is true according to the passage\n"
                    "FALSE\n"
                    "if the statement is false according to the passage\n"
                    "NOT GIVEN\n"
                    "if the information is not given in the passage\n"
                    "8) The growing importance of the middle classes led to an increased demand for dictionaries.\n"
                    "9) Johnson has become more well known since his death.\n"
                    "10) Johnson had been planning to write a dictionary for several years.\n"
                    "11) Johnson set up an academy to help with the writing of his Dictionary.\n"
                    "12) Johnson only received payment for his Dictionary on its completion.\n"
                    "13) Not all of the assistants survived to see the publication of the Dictionary."
                ),
                "text": "",
                "passage_id": "passage-1",
                "image_url": None,
            }],
            {8: "true", 9: "false", 10: "not given", 11: "false", 12: "false", 13: "true"},
        )

        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].type, "true-false-ng")
        self.assertEqual(groups[0].questions[0].statement, "The growing importance of the middle classes led to an increased demand for dictionaries.")
        self.assertNotIn("8)", groups[0].instruction)

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
