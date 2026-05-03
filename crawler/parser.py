"""
IELTS reading test HTML parser.

This parser is designed to be extended once you inspect the target site's HTML.
Run: python main.py inspect <url>  to print the HTML for inspection.
"""
from __future__ import annotations
from bs4 import BeautifulSoup
import re
import uuid
from models import ReadingTest, Passage, SimpleQuestion, QuestionGroup

QUESTION_RANGE_SEPARATORS = r"[-–—]"
PASSAGE_TITLE_TAGS = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']


def _is_interstitial_section_noise(text: str) -> bool:
    return bool(re.match(r'(?i)^cambridge ielts test\b', text.strip()))


def _looks_like_question_content(text: str) -> bool:
    stripped = text.strip()
    return bool(
        re.search(r'(?i)Questions?\s+\d+', stripped)
        or re.search(r'[…_]{3,}', stripped)
        or re.search(r'\(\d+\)\s*[…_]', stripped)
        or (len(stripped) < 400 and re.search(r'^[A-E](?:[A-Z]|\s+[A-Z])', stripped))
    )


def _resolve_passage_title_candidate(child) -> str | None:
    """Resolve the actual passage title after a blank line in QUESTIONS state.

    Some source pages insert short promotional lines like "Cambridge IELTS Test 1 to 17"
    between a blank separator and the real passage title. Scan forward across those short
    lines until we either hit a long paragraph that looks like passage body or discover that
    we're still inside question content.
    """
    candidate_lines: list[str] = []
    next_sib = child

    while next_sib:
        if next_sib.name not in PASSAGE_TITLE_TAGS:
            return None

        next_text = next_sib.get_text(separator="\n", strip=True)
        if not next_text:
            next_sib = next_sib.find_next_sibling(PASSAGE_TITLE_TAGS)
            continue

        if _looks_like_question_content(next_text) or re.search(r'^\d+', next_text):
            return None

        if len(next_text) > 200:
            if not candidate_lines or _looks_like_question_content(next_text):
                return None
            non_noise = [line for line in candidate_lines if not _is_interstitial_section_noise(line)]
            return non_noise[-1] if non_noise else candidate_lines[-1]

        candidate_lines.append(next_text)
        next_sib = next_sib.find_next_sibling(PASSAGE_TITLE_TAGS)

    return None


def _get_prev_text_sibling(child):
    prev_sib = child.find_previous_sibling(PASSAGE_TITLE_TAGS)
    while prev_sib and not prev_sib.get_text(separator="\n", strip=True):
        prev_sib = prev_sib.find_previous_sibling(PASSAGE_TITLE_TAGS)
    return prev_sib


def _sanitize_shared_text(text: str | None) -> str | None:
    if text is None:
        return None

    stripped = text.strip()
    if not stripped:
        return None

    if stripped.lower().startswith("show answers"):
        return None

    return stripped


def _extract_passages(soup: BeautifulSoup) -> list[Passage]:
    # Passages and questions are grouped linearly in this parser.
    # So _extract_passages will just return an empty list and we will handle both in a new combined parser
    return []

def _extract_questions(soup: BeautifulSoup, passages: list[Passage]) -> list[QuestionGroup]:
    return []

# New combined parser logic for the entire test
def parse_reading_test(html: str, url: str) -> ReadingTest:
    soup = BeautifulSoup(html, "html.parser")

    entry_content = soup.find('div', class_='entry-content')
    if not entry_content:
        entry_content = soup.body

    passages: list[Passage] = []
    raw_groups: list[dict] = []
    answers = {}

    current_passage_text = []
    current_passage_title = ""
    passage_count = 1

    state = "PASSAGE"
    current_q_group = None
    after_empty_in_questions = False  # flag: saw empty <p> while in QUESTIONS state

    # Pre-extract answers — handle varying HTML structures for the answer section.
    # Strategy: try multiple approaches in order of specificity.
    ans_container = None

    # Approach 1: Find the hidden answer div by its ID pattern (works regardless of nesting)
    ans_div = soup.find('div', id=lambda x: x and x.startswith('bg-showmore-hidden-'))
    if ans_div:
        # The answer text may be inside this div, or in the next sibling(s) if the div
        # is malformed (opened but not properly closed around the content).
        div_text = ans_div.get_text(strip=True)
        if div_text and re.search(r'\d+\.\s+', div_text):
            ans_container = ans_div
        else:
            # Walk up to the nearest block-level ancestor and find the next sibling with answers
            ancestor = ans_div
            while ancestor and ancestor.parent and ancestor.parent.name in ['span', 'p', 'div']:
                candidate = ancestor.parent.find_next_sibling(['p', 'div'])
                if candidate and re.search(r'\d+\.\s+', candidate.get_text(strip=True)):
                    ans_container = candidate
                    break
                ancestor = ancestor.parent

    # Approach 2: Button as direct sibling (original logic)
    if not ans_container:
        btn = soup.find('button', string=lambda t: t and 'Show Answers' in t)
        if btn:
            ans_container = btn.find_next_sibling('div')

    # Approach 3: <p> containing "Show Answers" text
    if not ans_container:
        for p in soup.find_all('p'):
            text = p.get_text(strip=True)
            if "Show Answers" in text or text == "Answers":
                ans_container = p.find_next_sibling(['p', 'div'])
                break

    # Collect ALL consecutive answer <p> siblings (answers may span multiple <p> tags)
    if ans_container:
        all_ans_parts = [ans_container]
        nxt = ans_container.find_next_sibling(['p', 'div'])
        while nxt and re.search(r'\d+\.\s+', nxt.get_text(strip=True)):
            all_ans_parts.append(nxt)
            nxt = nxt.find_next_sibling(['p', 'div'])

        for part in all_ans_parts:
            for br in part.find_all('br'):
                br.replace_with('\n')
            ans_text = part.get_text(separator="\n", strip=True)
            for line in ans_text.split('\n'):
                line = line.strip()
                match = re.match(r'^(\d+)\.\s+(.*)', line)
                if match:
                    answers[int(match.group(1))] = match.group(2).strip()

    def _flush_passage():
        nonlocal current_passage_text, current_passage_title, passage_count
        if current_passage_text:
            text = "\n\n".join(current_passage_text)
            passages.append(Passage(
                id=f"passage-{passage_count}",
                title=current_passage_title or f"Passage {passage_count}",
                text=text,
                paragraphs=current_passage_text[:10]
            ))
            current_passage_text = []
            current_passage_title = ""
            passage_count += 1

    for child in entry_content.children:
        if child.name is None:
            continue

        text = child.get_text(separator="\n", strip=True)

        # Track empty paragraphs while in QUESTIONS state (used to detect passage transitions)
        if not text:
            if state == "QUESTIONS":
                after_empty_in_questions = True
            continue

        if "Show Answers" in text and child.name in ['p', 'strong', 'h2', 'h3', 'div']:
            if current_passage_text:
                _flush_passage()
            break

        # Match "Questions 1-8", "Questions 11 and 12", "Question 13"
        q_range_match = re.search(rf'(?i)Questions\s+(\d+)\s*{QUESTION_RANGE_SEPARATORS}\s*(\d+)', text)
        q_and_match = re.search(r'(?i)Questions\s+(\d+)\s+and\s+(\d+)', text)
        q_single = re.search(r'(?i)Question\s+(\d+)', text)
        q_match = q_range_match or q_and_match

        if q_match or (q_single and "Choose the correct letter" in text):
            state = "QUESTIONS"
            after_empty_in_questions = False
            if current_passage_text:
                _flush_passage()

            start_q = int(q_match.group(1)) if q_match else int(q_single.group(1))
            end_q = int(q_match.group(2)) if q_match else start_q

            # Reference the most recently created passage
            p_id = passages[-1].id if passages else "passage-1"
            current_q_group = {
                "start": start_q,
                "end": end_q,
                "instruction": text,
                "text": "",
                "passage_id": p_id,
                "image_url": None,
            }
            raw_groups.append(current_q_group)
            continue

        # Heading tags denote passage titles
        if child.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            if state == "QUESTIONS":
                state = "PASSAGE"
            if current_passage_text:
                _flush_passage()
            current_passage_title = text
            state = "PASSAGE"
            after_empty_in_questions = False
            continue

        # Detect a new passage starting while we're in QUESTIONS state.
        # A short <p> after an empty line *could* be a new passage title (e.g. "Venus in
        # Transit") or a question stem (e.g. "The language debate", "An Undersea Turbine").
        # To distinguish: only treat it as a passage title if the next non-empty sibling
        # is a long paragraph (passage body), not a question-related element.
        if state == "QUESTIONS" and child.name == 'p':
            prev_sib = _get_prev_text_sibling(child)
            prev_text = prev_sib.get_text(separator="\n", strip=True) if prev_sib else ""
            follows_interstitial_noise = bool(prev_text and _is_interstitial_section_noise(prev_text))
            # Only match "Reading Passage N" as a standalone section marker,
            # not when it appears inside a question (e.g. "...purpose in Reading Passage?")
            is_reading_passage_marker = bool(re.match(r'^reading passage\b', text.lower()))
            is_candidate_title = ((after_empty_in_questions
                                  or follows_interstitial_noise
                                  or _is_interstitial_section_noise(text))
                                  and len(text) < 100
                                  and not re.search(r'(?i)Questions?\s+\d+', text)
                                  and not re.search(r'^\d+', text)
                                  and not re.search(r'(?i)^which\b', text)  # "Which FIVE..." is a question
                                  and not re.search(r'(?i)\bchoose\b', text)  # "Choose the correct..." is a question
                                  and current_q_group is not None)

            if is_candidate_title and not is_reading_passage_marker:
                resolved_title = _resolve_passage_title_candidate(child)
                if resolved_title and text != resolved_title:
                    # Ignore short interstitial lines and keep scanning until we reach the
                    # actual title that introduces the next passage.
                    continue
                is_candidate_title = resolved_title == text

            if is_reading_passage_marker or is_candidate_title:
                state = "PASSAGE"
                if current_passage_text:
                    _flush_passage()
                current_passage_title = text
                after_empty_in_questions = False
                continue

        after_empty_in_questions = False

        if state == "PASSAGE":
            if child.name == 'p':
                current_passage_text.append(text)
        elif state == "QUESTIONS" and current_q_group is not None:
            # Capture image URL if present (for diagram labeling questions)
            img = child if child.name == 'img' else child.find('img')
            if img and img.get('src') and not current_q_group['image_url']:
                current_q_group['image_url'] = img['src']
            for br in child.find_all('br'):
                br.replace_with('\n')
            current_q_group["text"] += "\n" + child.get_text(separator="\n", strip=True)

    if current_passage_text:
        _flush_passage()

    question_groups = _build_question_groups(raw_groups, answers)

    # Fallback to placeholders if completely failed
    if not passages:
        passages = _create_placeholder_passages()
    if not question_groups:
        question_groups = _create_placeholder_groups(passages)

    # Extract test ID from URL (e.g., .../ielts-reading-test-1/ -> test-1)
    match = re.search(r'test-(\d+)', url)
    test_id = f"test-{match.group(1)}" if match else f"test-{uuid.uuid4().hex[:8]}"

    return ReadingTest(
        id=test_id,
        title=_extract_title(soup),
        test_type="academic",
        passages=passages[:3],
        question_groups=question_groups,
        time_limit_minutes=60,
        source_url=url,
    )

def _extract_title(soup: BeautifulSoup) -> str:
    """Extract the test title from the page."""
    for selector in ["h1", ".test-title", ".reading-title", "title"]:
        el = soup.select_one(selector)
        if el:
            return el.get_text(strip=True)
    return "IELTS Academic Reading Test"

def _parse_children_text(header: str, children_text: str, start_q: int, end_q: int):
    """Parse the children text of a question group to extract:
    - full_instruction: header + explanation text (e.g. YES/NO/NOT GIVEN definitions)
    - individual_questions: dict mapping question number -> statement text
    - options: dict mapping option letter -> option text (for MC questions)
    - stem_text: question stem or passage text (for MC stems, summary passages, note passages)

    Strategy:
    - Lines matching "YES/NO/TRUE/FALSE/NOT GIVEN if the statement..." are instruction lines
    - Lines matching "N text..." where N is in [start_q, end_q] are numbered questions
    - Lines matching "A text..." or standalone "A" followed by text on the next line are option lines
    - Everything else is stem/passage text
    """
    lines = children_text.strip().split("\n")

    instruction_lines = []
    numbered_questions = {}
    options = {}
    stem_lines = []

    numbered_pattern = re.compile(r'^(\d+)\.?\s+(.*)')
    # Option with text on same line: "A descriptivists" or "A It is a more reliable..."
    option_inline_pattern = re.compile(r'^([A-K])\s+(.*)')
    heading_option_pattern = re.compile(r'^(i|ii|iii|iv|v|vi|vii|viii|ix|x)\.\s+(.*)', re.IGNORECASE)
    # Standalone option letter: just "A" or "B" on its own line
    option_standalone_pattern = re.compile(r'^([A-K])$')
    # Instruction explanation patterns (YES/NO/TRUE/FALSE definitions)
    instruction_kw_pattern = re.compile(r'^(YES|NO|TRUE|FALSE|NOT GIVEN|NOT)\b', re.IGNORECASE)
    # "if the statement..." continuation lines
    instruction_cont_pattern = re.compile(r'^if (the statement|there is|it is)', re.IGNORECASE)

    in_instruction_block = False
    pending_option_letter = None  # Tracks a standalone letter waiting for its text on the next line

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # If we have a pending option letter from the previous line, this line is the option text
        if pending_option_letter is not None:
            options[pending_option_letter] = line
            pending_option_letter = None
            in_instruction_block = False
            continue

        # Check if this is a numbered question line
        num_match = numbered_pattern.match(line)
        if num_match:
            qnum = int(num_match.group(1))
            if start_q <= qnum <= end_q:
                numbered_questions[qnum] = num_match.group(2).strip()
                in_instruction_block = False
                continue

        # Check if this is an instruction keyword line (YES, NO, TRUE, FALSE, NOT GIVEN)
        if instruction_kw_pattern.match(line) or instruction_cont_pattern.match(line):
            instruction_lines.append(line)
            in_instruction_block = True
            continue

        heading_match = heading_option_pattern.match(line)
        if heading_match:
            options[heading_match.group(1).lower()] = heading_match.group(2).strip()
            in_instruction_block = False
            continue

        # Check if this is an option line with text on the same line (A descriptivists, etc.)
        opt_match = option_inline_pattern.match(line)
        if opt_match and len(opt_match.group(2)) > 1:
            options[opt_match.group(1)] = opt_match.group(2).strip()
            in_instruction_block = False
            continue

        # Check if this is a standalone option letter (just "A", "B", etc.)
        opt_standalone = option_standalone_pattern.match(line)
        if opt_standalone:
            pending_option_letter = opt_standalone.group(1)
            continue

        # If we're in an instruction block (after YES/NO/TRUE/FALSE), continuation
        if in_instruction_block:
            instruction_lines.append(line)
            continue

        # Everything else is stem/passage text
        stem_lines.append(line)

    # Build full instruction: header + explanation lines
    full_instruction = header
    if instruction_lines:
        full_instruction = header + "\n" + "\n".join(instruction_lines)

    stem_text = "\n".join(stem_lines) if stem_lines else ""

    return full_instruction, numbered_questions, options, stem_text


def _build_question_groups(groups: list[dict], answers: dict) -> list[QuestionGroup]:
    result = []
    for g in groups:
        start_q = g['start']
        end_q = g['end']
        passage_id = g['passage_id']
        header = g['instruction']
        children_text = g['text'].strip()
        image_url = g.get('image_url')

        full_instruction, numbered_qs, options, stem_text = _parse_children_text(
            header, children_text, start_q, end_q
        )

        # Build individual questions
        simple_questions = []
        for qid in range(start_q, end_q + 1):
            ans = answers.get(qid, "UNKNOWN")
            statement = numbered_qs.get(qid, "")
            simple_questions.append(SimpleQuestion(id=qid, statement=statement, answer=ans))

        instr_lower = full_instruction.lower()

        # Check most-specific types first to avoid false positives.
        # e.g. "no more than two words" must not trigger true-false-ng.

        if "diagram" in instr_lower or "label" in instr_lower:
            result.append(QuestionGroup(
                id=f"group-{start_q}-{end_q}",
                type="diagram-labeling",
                passage_id=passage_id,
                instruction=full_instruction,
                questions=simple_questions,
                image_url=image_url or "",
            ))

        elif ("summary" in instr_lower or "notes" in instr_lower
              or ("complete" in instr_lower and "using" in instr_lower)):
            # Both summary completion and note completion are treated identically
            word_list = list(options.values()) if options else None
            shared = _sanitize_shared_text(stem_text or children_text or None)
            result.append(QuestionGroup(
                id=f"group-{start_q}-{end_q}",
                type="summary-completion",
                passage_id=passage_id,
                instruction=full_instruction,
                questions=simple_questions,
                shared_text=shared,
                word_list=word_list,
            ))

        elif (("contain" in instr_lower and ("paragraph" in instr_lower or "section" in instr_lower))
              or ("which" in instr_lower and ("paragraph" in instr_lower or "section" in instr_lower))
              or ("match" in instr_lower and ("person" in instr_lower or "people" in instr_lower or "statement" in instr_lower))):
            # "Which paragraph/section contains..." or "Match each statement with correct person"
            # Build options from parsed options dict or default to A-I
            if options:
                para_options = options
            else:
                # Try to infer range from instruction (e.g., "sections A-I" or "paragraphs A-G")
                # Note: some sites render "I" as lowercase "l" — handle that case
                sec_match = re.search(r'([A-Z])\s*[-–]\s*([A-Za-z])', full_instruction)
                if sec_match:
                    start_letter = ord(sec_match.group(1))
                    end_char = sec_match.group(2)
                    # 'l' (lowercase L) often represents 'I' on IELTS sites
                    if end_char == 'l':
                        end_letter = ord('I')
                    else:
                        end_letter = ord(end_char.upper())
                    para_options = {chr(c): chr(c) for c in range(start_letter, end_letter + 1)}
                else:
                    para_options = {"A": "A", "B": "B", "C": "C", "D": "D", "E": "E", "F": "F"}
            result.append(QuestionGroup(
                id=f"group-{start_q}-{end_q}",
                type="matching-information",
                passage_id=passage_id,
                instruction=full_instruction,
                questions=simple_questions,
                options=para_options,
            ))

        elif "heading" in instr_lower:
            heading_options = options if options else {"i": "i", "ii": "ii", "iii": "iii", "iv": "iv", "v": "v"}
            result.append(QuestionGroup(
                id=f"group-{start_q}-{end_q}",
                type="matching-headings",
                passage_id=passage_id,
                instruction=full_instruction,
                questions=simple_questions,
                options=heading_options,
            ))

        elif "choose" in instr_lower and "letter" in instr_lower:
            mc_options = options if options else {chr(65+i): f"Option {chr(65+i)}" for i in range(4)}
            result.append(QuestionGroup(
                id=f"group-{start_q}-{end_q}",
                type="multiple-choice",
                passage_id=passage_id,
                instruction=full_instruction,
                questions=simple_questions,
                options=mc_options,
                shared_text=_sanitize_shared_text(stem_text or None),
            ))

        elif ("not given" in instr_lower
              or re.search(r'\b(yes|no|true|false)\b.*if.*statement', instr_lower, re.DOTALL)):
            # True/False/NG and Yes/No/NG questions
            result.append(QuestionGroup(
                id=f"group-{start_q}-{end_q}",
                type="true-false-ng",
                passage_id=passage_id,
                instruction=full_instruction,
                questions=simple_questions,
            ))

        else:
            # Default: sentence completion
            result.append(QuestionGroup(
                id=f"group-{start_q}-{end_q}",
                type="sentence-completion",
                passage_id=passage_id,
                instruction=full_instruction,
                questions=simple_questions,
                shared_text=_sanitize_shared_text(stem_text or None),
            ))

    return result


def _create_placeholder_passages() -> list[Passage]:
    return [Passage(id="passage-1", title="Parsing failed", text="[Parsing failed]", paragraphs=[])]

def _create_placeholder_groups(passages: list[Passage]) -> list[QuestionGroup]:
    return [QuestionGroup(
        id="group-1-1",
        type="true-false-ng",
        passage_id="passage-1",
        instruction="Parsing failed",
        questions=[SimpleQuestion(id=1, statement="Failed", answer="TRUE")],
    )]
