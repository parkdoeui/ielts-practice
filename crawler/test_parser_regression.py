import unittest
from pathlib import Path

from bs4 import BeautifulSoup

from ai_repair import _build_repair_prompt
from ai_validator import _build_validation_prompt
from models import Passage, QuestionGroup, ReadingTest, SimpleQuestion
from parser import (
    _build_question_groups,
    _classify_blocks,
    _extract_answers,
    _normalize_dom,
    _normalize_known_source_artifacts,
    _normalize_oversegmented_passages,
    _segment_test,
    parse_reading_test,
)
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
    def test_bundled_reading_source_artifacts_are_normalized(self):
        value = (
            "still in my scat; sting rays; T emerged, as the sole embodiment; rustfree; "
            "liquid, polymer; factories, A different; prevents it. from; hard while lumps; "
            "What, helped; NO MORE THAN THREE WORD S; Imps helped to make beer; "
            "It want animals to work; Iike using wheels; when if did; drink beet; "
            "career choice made by graduates; Dr, Ken Aplin; Western Australia,most; "
            "purpose of Frogwatch is ."
        )

        cleaned = _normalize_known_source_artifacts(value)

        for expected in (
            "still in my seat", "stingrays", "I emerged as the sole embodiment",
            "rust-free", "liquid polymer", "factories. A different", "prevents it from",
            "hard white lumps", "What helped", "NO MORE THAN THREE WORDS",
            "Hops helped to make beer", "not want animals to work", "like using wheels",
            "when it did", "drink beer", "career choices made by graduates",
            "Dr. Ken Aplin", "Western Australia, most", "purpose of Frogwatch is:",
        ):
            self.assertIn(expected, cleaned)

    def test_known_reading_295_source_artifacts_are_normalized(self):
        value = (
            "There is a dear reason. The deep- sea contains minerals, Mining corporations argue for it. "
            "There is little waste, Different methods of extraction exist, (hen drawing a slurry upwards."
        )

        cleaned = _normalize_known_source_artifacts(value)

        self.assertIn("clear reason", cleaned)
        self.assertIn("deep-sea", cleaned)
        self.assertIn("minerals. Mining corporations", cleaned)
        self.assertIn("waste. Different methods", cleaned)
        self.assertIn("then drawing", cleaned)

    def test_completion_notes_before_next_passage_do_not_become_passage(self):
        long_first = "Butterfly passage content. " * 20
        long_second = "A Deep-sea mining passage content. " * 20
        soup = BeautifulSoup(
            f"""
            <div class="entry-content">
              <p>The impact of climate change on butterflies in Britain</p>
              <p>{long_first}</p>
              <p>Questions 7-13<br/>Complete the notes below. Choose ONE WORD ONLY from the passage.</p>
              <p>Butterflies in the UK</p>
              <p>The Small Blue<br/>• lives in large (7) ……………….<br/>• first appears at the start of (8) ………….</p>
              <p>The High Brown Fritillary<br/>• is considered to be more (9) ……………… than other species</p>
              <p>Deep-sea mining</p>
              <p>Bacteria from the ocean floor can beat superbugs and cancer.</p>
              <p>{long_second}</p>
              <p>Questions 14-17<br/>Which paragraph contains the following information?</p>
            </div>
            """,
            "html.parser",
        )

        children = _normalize_dom(soup.select_one("div.entry-content"))
        blocks = _classify_blocks(children, "https://practicepteonline.com/ielts-reading-test-295/")
        passages, raw_groups = _segment_test(blocks)
        completion = next(group for group in raw_groups if group["start"] == 7)
        built = _build_question_groups(raw_groups, {number: "answer" for number in range(7, 18)}, "")
        completion_group = next(group for group in built if group.id == "group-7-13")

        self.assertEqual([passage.title for passage in passages], [
            "The impact of climate change on butterflies in Britain",
            "Deep-sea mining",
        ])
        self.assertIn("Butterflies in the UK", completion["text"])
        self.assertIn("(7)", completion["text"])
        self.assertNotIn("(7)", passages[1].text)
        self.assertIn("Butterflies in the UK", completion_group.shared_text or "")

    def test_matching_heading_options_do_not_become_a_fake_passage(self):
        long_passage = "Tea and beer passage content. " * 50
        soup = BeautifulSoup(
            f"""
            <div class="entry-content">
              <p>Did tea and beer bring about industrialisation?</p>
              <p>{long_passage}</p>
              <p>Questions 14-18<br/>Choose the most suitable headings for sections B-F.</p>
              <p>There are more headings than sections so you will not use all of them.</p>
              <p>i. Tea drinking<br/>ii. Population growth<br/>iii. Waterborne disease<br/>iv. Japan<br/>v. Industry</p>
              <p>14. Section B<br/>15. Section C<br/>16. Section D<br/>17. Section E<br/>18. Section F</p>
              <p>Questions 19-22<br/>Complete the table.</p>
              <p>Reason: (19) …………</p>
            </div>
            """,
            "html.parser",
        )

        blocks = _classify_blocks(
            _normalize_dom(soup.select_one("div.entry-content")),
            "https://practicepteonline.com/ielts-reading-test-297/",
        )
        passages, raw_groups = _segment_test(blocks)
        groups = _build_question_groups(raw_groups, {qid: "answer" for qid in range(14, 23)})
        headings = next(group for group in groups if group.id == "group-14-18")

        self.assertEqual(len(passages), 1)
        self.assertEqual(list(headings.options or {}), ["i", "ii", "iii", "iv", "v"])
        self.assertEqual(
            [question.statement for question in headings.questions],
            ["Section B", "Section C", "Section D", "Section E", "Section F"],
        )

    def test_completion_content_is_not_mistaken_for_letter_or_boolean_options(self):
        groups = _build_question_groups(
            [{
                "start": 20,
                "end": 22,
                "instruction": "Questions 20-22\nComplete the description below.",
                "text": (
                    "A single product is mixed with alcohol and (20) ………… then left to stand.\n"
                    "The mixture is then (21) ………… vigorously.\n"
                    "No active substances remain when it gets (22) …………"
                ),
                "passage_id": "passage-2",
                "image_url": None,
            }],
            {20: "water", 21: "shaken", 22: "stronger"},
        )

        shared = groups[0].shared_text or ""
        self.assertIn("A single product", shared)
        self.assertIn("(20)", shared)
        self.assertIn("No active substances", shared)
        self.assertIn("(22)", shared)

    def test_bare_word_bank_is_extracted_from_summary_context(self):
        groups = _build_question_groups(
            [{
                "start": 28,
                "end": 29,
                "instruction": "Questions 28-29\nComplete the summary. Choose your answers from the box below.",
                "text": (
                    "List of Words\nAxis\nPerspective\nProjection\nCompare\n"
                    "Each method of (28) ………… involves compromise. The map shows an (29) …………"
                ),
                "passage_id": "passage-3",
                "image_url": None,
            }],
            {28: "Projection", 29: "Axis"},
        )

        self.assertEqual(groups[0].word_list, ["Axis", "Perspective", "Projection", "Compare"])
        self.assertNotIn("Axis\nPerspective", groups[0].shared_text or "")

    def test_letter_selection_instructions_produce_interactive_group_types(self):
        groups = _build_question_groups(
            [
                {
                    "start": 1,
                    "end": 1,
                    "instruction": "Questions 1\nCircle the correct answer A-D.",
                    "text": "1. Which answer?\nA\nAlpha\nB\nBeta\nC\nGamma\nD\nDelta",
                    "passage_id": "passage-1",
                    "image_url": None,
                },
                {
                    "start": 2,
                    "end": 3,
                    "instruction": "Questions 2-3\nChoose one phrase from the list A-C to complete each sentence.",
                    "text": "2. First stem\n3. Second stem\nA. Alpha\nB. Beta\nC. Gamma",
                    "passage_id": "passage-1",
                    "image_url": None,
                },
                {
                    "start": 4,
                    "end": 5,
                    "instruction": "Questions 4-5\nRe-order the following letters (A-C).",
                    "text": "A. First event\nB. Second event\nC. Third event\n4. Next\n5. Last",
                    "passage_id": "passage-1",
                    "image_url": None,
                },
            ],
            {1: "B", 2: "A", 3: "C", 4: "B", 5: "C"},
        )

        self.assertEqual([group.type for group in groups], [
            "multiple-choice", "matching-sentence-endings", "matching",
        ])
        self.assertTrue(all(group.questions[0].statement for group in groups))
        self.assertTrue(all(group.options or group.questions[0].options for group in groups))

    def test_answer_list_directly_after_show_answers_is_extracted(self):
        soup = BeautifulSoup("""
            <p>Show Answers</p>
            <ol><li>first</li><li>second</li></ol>
        """, "html.parser")

        self.assertEqual(_extract_answers(soup), {1: "first", 2: "second"})

    def test_oversegmented_pages_keep_three_substantive_passages(self):
        passages = [
            Passage(id="passage-1", title="One", text="a" * 1200, paragraphs=["a" * 1200]),
            Passage(id="passage-2", title="Option table", text="b" * 300, paragraphs=["b" * 300]),
            Passage(id="passage-3", title="Two", text="c" * 1200, paragraphs=["c" * 1200]),
            Passage(id="passage-4", title="Three", text="d" * 1200, paragraphs=["d" * 1200]),
        ]
        raw_groups = [
            {"start": 1, "passage_id": "passage-1"},
            {"start": 14, "passage_id": "passage-3"},
            {"start": 27, "passage_id": "passage-4"},
        ]

        normalized, groups = _normalize_oversegmented_passages(passages, raw_groups)

        self.assertEqual([passage.title for passage in normalized], ["One", "Two", "Three"])
        self.assertEqual([passage.id for passage in normalized], ["passage-1", "passage-2", "passage-3"])
        self.assertEqual([group["passage_id"] for group in groups], ["passage-1", "passage-2", "passage-3"])

    def test_per_question_multiple_choice_options_do_not_overwrite_siblings(self):
        groups = _build_question_groups(
            [{
                "start": 1,
                "end": 3,
                "instruction": (
                    "Questions 1-3\n"
                    "Choose the correct letter, A, B, C or D. Write the correct letter in boxes 1-3 on your answer sheet."
                ),
                "text": (
                    "1 The main topic discussed in the text is\n"
                    "A\n"
                    "the damage caused to US golf courses and golf players by lightning strikes.\n"
                    "B\n"
                    "the effect of lightning on power supplies in the US and in Japan.\n"
                    "C\n"
                    "a variety of methods used in trying to control lightning strikes.\n"
                    "D\n"
                    "a laser technique used in trying to control lightning strikes.\n"
                    "2 According to the text, every year lightning\n"
                    "A\n"
                    "does considerable damage to buildings during thunderstorms.\n"
                    "B\n"
                    "kills or injures mainly golfers in the United States.\n"
                    "C\n"
                    "kills or injures around 500 people throughout the world.\n"
                    "D\n"
                    "damages more than 100 American power companies.\n"
                    "3 Researchers at the University of Florida and at the University of New Mexico\n"
                    "A\n"
                    "receive funds from the same source\n"
                    "B\n"
                    "are using the same techniques\n"
                    "C\n"
                    "are employed by commercial companies\n"
                    "D\n"
                    "are in opposition to each other"
                ),
                "passage_id": "passage-1",
                "image_url": None,
            }],
            {1: "D", 2: "A", 3: "A"},
        )

        self.assertEqual(len(groups), 1)
        group = groups[0]
        self.assertEqual(group.type, "multiple-choice")
        self.assertIsNone(group.options)
        self.assertEqual(group.questions[0].options["A"], "the damage caused to US golf courses and golf players by lightning strikes.")
        self.assertEqual(group.questions[1].options["A"], "does considerable damage to buildings during thunderstorms.")
        self.assertEqual(group.questions[2].options["A"], "receive funds from the same source")

    def test_shared_multi_answer_multiple_choice_options_remain_group_level(self):
        groups = _build_question_groups(
            [{
                "start": 14,
                "end": 18,
                "instruction": (
                    "Questions 14-18\n"
                    "Choose\n"
                    "FIVE\n"
                    "letters, A-K. Write the correct letters in boxes 14-18 on your answer sheet."
                ),
                "text": (
                    "Which FIVE of these beliefs are reported by the writer of the text?\n"
                    "A Truly gifted people are talented in all areas.\n"
                    "B The talents of geniuses are soon exhausted.\n"
                    "C Gifted people should use their gifts.\n"
                    "D A genius appears once in every generation.\n"
                    "E Genius can be easily measured."
                ),
                "passage_id": "passage-2",
                "image_url": None,
            }],
            {14: "B", 15: "C", 16: "D", 17: "E", 18: "A"},
        )

        self.assertEqual(len(groups), 1)
        group = groups[0]
        self.assertEqual(group.type, "multiple-choice")
        self.assertEqual(group.options["A"], "Truly gifted people are talented in all areas.")
        self.assertTrue(all(q.options is None for q in group.questions))

    def test_which_two_option_list_is_multiple_choice(self):
        groups = _build_question_groups(
            [{
                "start": 9,
                "end": 10,
                "instruction": "Questions 9-10",
                "text": (
                    "Write your answers in boxes 9 and 10 on your answer sheet.\n"
                    "Which\n"
                    "TWO\n"
                    "of the following factors influencing the design of Bakelite objects are mentioned in the text?\n"
                    "A\n"
                    "the function which the object would serve\n"
                    "B\n"
                    "the ease with which the resin could fill the mould\n"
                    "C\n"
                    "the facility with which the object could be removed from the mould\n"
                    "D\n"
                    "the limitations of the materials used to manufacture the mould\n"
                    "E\n"
                    "the fashionable styles of the period"
                ),
                "passage_id": "passage-1",
                "image_url": None,
            }],
            {9: "B", 10: "C"},
        )

        self.assertEqual(len(groups), 1)
        group = groups[0]
        self.assertEqual(group.type, "multiple-choice")
        self.assertEqual(group.shared_text, "Which\nTWO\nof the following factors influencing the design of Bakelite objects are mentioned in the text?")
        self.assertEqual(group.options["A"], "the function which the object would serve")
        self.assertEqual(group.options["E"], "the fashionable styles of the period")
        self.assertTrue(all(q.options is None for q in group.questions))

    def test_sentence_completion_preserves_group_image(self):
        groups = _build_question_groups(
            [{
                "start": 4,
                "end": 8,
                "instruction": "Questions 4-8",
                "text": (
                    "Complete the flow-chart. Choose\n"
                    "ONE WORD ONLY\n"
                    "from the passage for each answer.\n"
                    "Write your answers in boxes 4-8 on your answer sheet."
                ),
                "passage_id": "passage-1",
                "image_url": "/wp-content/uploads/2024/09/test-16-min.png",
            }],
            {4: "Novalak", 5: "fillers", 6: "hexa", 7: "raw", 8: "pressure"},
            base_url="https://practicepteonline.com/ielts-reading-test-16/",
        )

        self.assertEqual(len(groups), 1)
        group = groups[0]
        self.assertEqual(group.type, "sentence-completion")
        self.assertEqual(
            group.image_url,
            "https://practicepteonline.com/wp-content/uploads/2024/09/test-16-min.png",
        )

    def test_matching_sentence_endings_options_remain_group_level_after_stems(self):
        groups = _build_question_groups(
            [{
                "start": 22,
                "end": 26,
                "instruction": "Questions 22-26\nComplete each sentence with the correct ending, A-I, below.",
                "text": (
                    "22 Disapene scale insects feed on\n"
                    "23 Neodumetia sangawani ate\n"
                    "24 Leaf-mining hispides blighted\n"
                    "25 An Argentinian weevil may be successful in wiping out\n"
                    "26 Salvinia molesta plagues\n"
                    "A\n"
                    "forage grass\n"
                    "B\n"
                    "rice fields\n"
                    "C\n"
                    "coconut trees\n"
                    "D\n"
                    "fruit trees\n"
                    "E\n"
                    "water hyacinth\n"
                    "F\n"
                    "parthenium weed\n"
                    "G\n"
                    "Brazilian beetles\n"
                    "H\n"
                    "grass-scale insects\n"
                    "I\n"
                    "larval parasites"
                ),
                "passage_id": "passage-2",
                "image_url": None,
            }],
            {22: "D", 23: "H", 24: "C", 25: "E", 26: "B"},
        )

        self.assertEqual(len(groups), 1)
        group = groups[0]
        self.assertEqual(group.type, "matching-sentence-endings")
        self.assertEqual(group.options["A"], "forage grass")
        self.assertEqual(group.options["I"], "larval parasites")
        self.assertTrue(all(q.options is None for q in group.questions))

    def test_classification_header_options_are_group_level(self):
        groups = _build_question_groups(
            [{
                "start": 31,
                "end": 36,
                "instruction": (
                    "Questions 31-36\n"
                    "Classify the following statements as referring to\n"
                    "A\n"
                    "hand collecting\n"
                    "B\n"
                    "using bait\n"
                    "C\n"
                    "sampling ground litter\n"
                    "D\n"
                    "using a pitfall trap"
                ),
                "text": (
                    "Write the correct letter, A, B, C or D, in boxes 31-36 on your answer sheet.\n"
                    "31 It is preferable to take specimens from groups of ants.\n"
                    "32 It is particularly effective for wet habitats.\n"
                    "33 It is a good method for species which are hard to find.\n"
                    "34 Little time and effort is required.\n"
                    "35 Separate containers are used for individual specimens.\n"
                    "36 Non-alcoholic preservative should be used."
                ),
                "passage_id": "passage-3",
                "image_url": None,
            }],
            {31: "A", 32: "C", 33: "B", 34: "D", 35: "A", 36: "D"},
        )

        self.assertEqual(len(groups), 1)
        group = groups[0]
        self.assertEqual(group.type, "classification")
        self.assertEqual(group.options["A"], "hand collecting")
        self.assertEqual(group.options["D"], "using a pitfall trap")
        self.assertTrue(all(q.options is None for q in group.questions))

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

    def test_parses_plural_single_question_header(self):
        html = """
        <html>
          <body>
            <div class="entry-content">
              <p>Single Question Passage</p>
              <p>This is a long passage paragraph. This is a long passage paragraph. This is a long passage paragraph. This is a long passage paragraph. This is a long passage paragraph.</p>
              <p>Questions 9<br/>Choose TWO WORDS from the passage for the answer.</p>
              <p>There are many different types of dogs today, because, in early times humans began to (9) ........ their animals for the characteristics they wanted.</p>
              <p>Show Answers</p>
              <div id="bg-showmore-hidden-1">
                <p>9. selectively breed</p>
              </div>
            </div>
          </body>
        </html>
        """

        test = parse_reading_test(html, "https://practicepteonline.com/ielts-reading-test-300/")
        group = next(g for g in test.question_groups if g.id == "group-9-9")

        self.assertEqual(group.type, "sentence-completion")
        self.assertEqual([q.id for q in group.questions], [9])
        self.assertEqual(group.questions[0].answer, "selectively breed")
        self.assertIn("(9)", group.shared_text or "")

    def test_diagram_instruction_without_image_falls_back_to_completion(self):
        groups = _build_question_groups(
            [{
                "start": 14,
                "end": 16,
                "instruction": (
                    "Questions 14-16\n"
                    "Complete the timeline diagram below. Write\n"
                    "NO MORE THAN THREE WORDS\n"
                    "from the passage for each answer."
                ),
                "text": (
                    "1876\n"
                    "No longer is criminality confined to a (14) ........ realm.\n"
                    "1960s\n"
                    "(15) ........ are linked to criminality.\n"
                    "1995\n"
                    "(16) ........ undermines the hypothesis."
                ),
                "passage_id": "passage-1",
                "image_url": None,
            }],
            {14: "moral or philosophical", 15: "chromosomal abnormalities", 16: "Epps's study"},
        )

        self.assertEqual(len(groups), 1)
        group = groups[0]
        self.assertEqual(group.type, "sentence-completion")
        self.assertIsNone(group.image_url)
        self.assertIn("1876", group.shared_text or "")
        self.assertEqual([q.id for q in group.questions], [14, 15, 16])


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


def _minimal_reading_test(groups: list[QuestionGroup]) -> ReadingTest:
    passages = [
        Passage(
            id=f"passage-{idx}",
            title=f"Passage {idx}",
            text="This is a sufficiently long passage paragraph for validation. " * 3,
            paragraphs=["This is a sufficiently long passage paragraph for validation. " * 3],
        )
        for idx in range(1, 4)
    ]
    return ReadingTest(
        id="test-x",
        title="Test X",
        test_type="academic",
        passages=passages,
        question_groups=groups,
        time_limit_minutes=60,
        source_url="https://practicepteonline.com/ielts-reading-test-x/",
    )


def _filler_group(start: int) -> QuestionGroup:
    return QuestionGroup(
        id=f"group-{start}-40",
        type="sentence-completion",
        passage_id="passage-3",
        instruction=f"Questions {start}-40\nComplete the sentences.",
        questions=[
            SimpleQuestion(id=qid, statement=f"Question {qid}", answer="answer")
            for qid in range(start, 41)
        ],
    )


class ValidationRegressionTests(unittest.TestCase):
    def test_validator_rejects_completion_group_without_displayable_context(self):
        test = _minimal_reading_test([
            QuestionGroup(
                id="group-1-3",
                type="summary-completion",
                passage_id="passage-1",
                instruction="Questions 1-3\nComplete the notes.",
                questions=[
                    SimpleQuestion(id=qid, statement="", answer="answer")
                    for qid in range(1, 4)
                ],
            ),
            _filler_group(4),
        ])

        result = validate_reading_test(test)

        self.assertFalse(result.valid)
        self.assertTrue(any("completion questions without displayable context" in error for error in result.errors))

    def test_validator_allows_completion_context_embedded_in_instruction(self):
        test = _minimal_reading_test([
            QuestionGroup(
                id="group-1-3",
                type="summary-completion",
                passage_id="passage-1",
                instruction="Questions 1-3\n• lives in (1) ………\n• appears in (2) ………\n• eats (3) ………",
                questions=[
                    SimpleQuestion(id=qid, statement="", answer="answer")
                    for qid in range(1, 4)
                ],
            ),
            _filler_group(4),
        ])

        result = validate_reading_test(test)

        self.assertTrue(result.valid, result.report())

    def test_validator_requires_context_for_each_empty_completion_question(self):
        test = _minimal_reading_test([
            QuestionGroup(
                id="group-1-3",
                type="summary-completion",
                passage_id="passage-1",
                instruction="Questions 1-3\nComplete the notes.",
                questions=[
                    SimpleQuestion(id=qid, statement="", answer="answer")
                    for qid in range(1, 4)
                ],
                shared_text="First (1) ………\nSecond (2) ………",
            ),
            _filler_group(4),
        ])

        result = validate_reading_test(test)

        self.assertFalse(result.valid)
        self.assertTrue(any("[3]" in error for error in result.errors))

    def test_validator_rejects_placeholder_matching_headings(self):
        test = _minimal_reading_test([
            QuestionGroup(
                id="group-1-3",
                type="matching-headings",
                passage_id="passage-1",
                instruction="Questions 1-3\nChoose the headings.",
                questions=[
                    SimpleQuestion(id=1, statement="", answer="i"),
                    SimpleQuestion(id=2, statement="", answer="ii"),
                    SimpleQuestion(id=3, statement="", answer="iii"),
                ],
                options={"i": "i", "ii": "ii", "iii": "iii"},
            ),
            _filler_group(4),
        ])

        result = validate_reading_test(test)

        self.assertFalse(result.valid)
        self.assertTrue(any("questions without labels" in error for error in result.errors))
        self.assertTrue(any("placeholder-only options" in error for error in result.errors))

    def test_validator_rejects_letter_selection_as_sentence_completion(self):
        test = _minimal_reading_test([
            QuestionGroup(
                id="group-1-3",
                type="sentence-completion",
                passage_id="passage-1",
                instruction="Questions 1-3\nChoose one phrase from A-C.",
                questions=[
                    SimpleQuestion(id=1, statement="First", answer="A"),
                    SimpleQuestion(id=2, statement="Second", answer="B"),
                    SimpleQuestion(id=3, statement="Third", answer="C"),
                ],
            ),
            _filler_group(4),
        ])

        result = validate_reading_test(test)

        self.assertFalse(result.valid)
        self.assertTrue(any("misclassified as sentence-completion" in error for error in result.errors))

    def test_validator_rejects_question_placeholders_inside_passage(self):
        test = _minimal_reading_test([_filler_group(1)])
        test.passages[0].text += "\nButterflies in the UK: lives in large (7) ………………."
        test.passages[0].paragraphs.append("Butterflies in the UK: lives in large (7) ……………….")

        result = validate_reading_test(test)

        self.assertFalse(result.valid)
        self.assertTrue(any("question-completion placeholders" in error for error in result.errors))

    def test_validator_flags_overwritten_unique_multiple_choice_options(self):
        test = _minimal_reading_test([
            QuestionGroup(
                id="group-1-3",
                type="multiple-choice",
                passage_id="passage-1",
                instruction="Questions 1-3\nChoose the correct letter, A, B, C or D.",
                questions=[
                    SimpleQuestion(id=1, statement="First MC question", answer="A"),
                    SimpleQuestion(id=2, statement="Second MC question", answer="B"),
                    SimpleQuestion(id=3, statement="Third MC question", answer="C"),
                ],
                options={"A": "last A", "B": "last B", "C": "last C", "D": "last D"},
            ),
            _filler_group(4),
        ])

        result = validate_reading_test(test)

        self.assertFalse(result.valid)
        self.assertTrue(any("likely overwritten multiple-choice options" in error for error in result.errors))

    def test_validator_allows_shared_multi_answer_multiple_choice_options(self):
        test = _minimal_reading_test([
            QuestionGroup(
                id="group-1-5",
                type="multiple-choice",
                passage_id="passage-1",
                instruction="Questions 1-5\nChoose FIVE letters, A-G.",
                questions=[
                    SimpleQuestion(id=1, statement="", answer="A"),
                    SimpleQuestion(id=2, statement="", answer="B"),
                    SimpleQuestion(id=3, statement="", answer="C"),
                    SimpleQuestion(id=4, statement="", answer="D"),
                    SimpleQuestion(id=5, statement="", answer="E"),
                ],
                options={"A": "Alpha", "B": "Beta", "C": "Gamma", "D": "Delta", "E": "Epsilon", "F": "Zeta", "G": "Eta"},
            ),
            _filler_group(6),
        ])

        result = validate_reading_test(test)

        self.assertTrue(result.valid, msg=result.report())

    def test_validator_flags_matching_sentence_endings_attached_to_question(self):
        test = _minimal_reading_test([
            QuestionGroup(
                id="group-1-3",
                type="matching-sentence-endings",
                passage_id="passage-1",
                instruction="Questions 1-3\nComplete each sentence with the correct ending, A-C, below.",
                questions=[
                    SimpleQuestion(id=1, statement="First stem", answer="A"),
                    SimpleQuestion(id=2, statement="Second stem", answer="B"),
                    SimpleQuestion(id=3, statement="Third stem", answer="C", options={"A": "Alpha", "B": "Beta", "C": "Gamma"}),
                ],
                options=None,
            ),
            _filler_group(4),
        ])

        result = validate_reading_test(test)

        self.assertFalse(result.valid)
        self.assertTrue(any("matching-sentence-endings group has no ending options" in error for error in result.errors))
        self.assertTrue(any("options should be group-level" in error for error in result.errors))


class AiPromptRegressionTests(unittest.TestCase):
    def test_ai_validation_prompt_flags_unique_multiple_choice_option_loss(self):
        test = _minimal_reading_test([_filler_group(1)])
        prompt = _build_validation_prompt(test, "Questions 1-3\n1 First\nA one\nB two")

        self.assertIn("each numbered question has its own visible A/B/C/D option block", prompt)
        self.assertIn("each question must have its own `options` object", prompt)
        self.assertNotIn("Do NOT flag this at all", prompt)

    def test_ai_validation_prompt_flags_misplaced_sentence_endings(self):
        test = _minimal_reading_test([_filler_group(1)])
        prompt = _build_validation_prompt(test, "Questions 22-26\nComplete each sentence with the correct ending")

        self.assertIn("Matching-sentence-ending groups", prompt)
        self.assertIn("instead of `group.options`", prompt)
        self.assertIn("The numbered stems should stay as `questions[].statement`", prompt)
        self.assertIn("`sentence-completion` is valid for those instructions", prompt)

    def test_ai_validation_prompt_flags_missing_classification_options(self):
        test = _minimal_reading_test([_filler_group(1)])
        prompt = _build_validation_prompt(test, "Questions 31-36\nClassify the following statements as referring to")

        self.assertIn("Classification groups", prompt)
        self.assertIn("The category labels must be preserved as shared group options", prompt)

    def test_ai_repair_prompt_allows_per_question_multiple_choice_repair(self):
        test = _minimal_reading_test([_filler_group(1)])
        prompt = _build_repair_prompt(test, "Questions 1-3\n1 First\nA one\nB two")

        self.assertIn("move those choices into each question's `options` object", prompt)
        self.assertIn("put the ending choices in group-level `options`", prompt)
        self.assertIn("preserve those labels in group-level `options`", prompt)

if __name__ == "__main__":
    unittest.main()
