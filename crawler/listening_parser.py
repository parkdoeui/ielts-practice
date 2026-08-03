from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Optional

from bs4 import BeautifulSoup

from models import ListeningPart, ListeningTest, QuestionGroup, SimpleQuestion
from parser import _extract_answers, _normalize_url


BLANK_MARKER = "␣"
CHECKBOX_MARKER = "☐"
PART_RE = re.compile(r"^Part\s+(\d+)\b", re.IGNORECASE)
QUESTION_HEADER_RE = re.compile(
    r"Questions?\s+(\d+)\s*(?:(?:[-–—]\s*(\d+))|(?:and\s+(\d+)))?",
    re.IGNORECASE,
)
QUESTION_START_RE = re.compile(r"^Questions?\s+", re.IGNORECASE)
NUMBERED_RE = re.compile(r"^(\d+)\.?\s+(.*)$")
NUMBERED_BLANK_RE = re.compile(
    rf"^(\d+)\.?\s+(.*?)\s*{re.escape(BLANK_MARKER)}\s*$"
)
COMPLETION_RE = re.compile(rf"\((\d+)\)(?=[^\n{re.escape(BLANK_MARKER)}]{{0,80}}{re.escape(BLANK_MARKER)})")
CHECKBOX_OPTION_RE = re.compile(
    rf"^{re.escape(CHECKBOX_MARKER)}\s*([A-Z])\b\s*(.*)$"
)
BOX_OPTION_RE = re.compile(r"^([A-I])\s+(.+)$")
LEADING_LIST_MARKER_RE = re.compile(r"^(?:[•●○◦▪▫·]|[oO](?=\s))\s*")
KNOWN_OCR_REPLACEMENTS = (
    (re.compile(r"\binternal wails\b", re.IGNORECASE), "internal walls"),
    (re.compile(r"\btoo tow\b", re.IGNORECASE), "too low"),
)


@dataclass
class _RawGroup:
    kind: str
    instruction: str
    lines: list[str]
    header_numbers: list[int]


def _normalize_text(value: str) -> str:
    value = value.replace("\xa0", " ").strip()
    return re.sub(r"\s+", " ", value)


def _extract_test_id(url: str) -> str:
    match = re.search(r"ielts-listening-test-(\d+)", url, flags=re.IGNORECASE)
    if not match:
        raise ValueError(f"Unable to extract listening test number from URL: {url}")
    return f"listening-test-{match.group(1)}"


def _extract_title(soup: BeautifulSoup, test_id: str) -> str:
    node = soup.select_one("h1.entry-title, h1.page-title, h1, h2.entry-title, title")
    if node:
        title = _normalize_text(node.get_text(" ", strip=True))
        if title:
            return title
    number = test_id.rsplit("-", 1)[-1]
    return f"IELTS Listening Test {number}"


def _linearize_entry(entry) -> list[str]:
    """Convert source paragraphs and form controls to marker-tagged lines."""
    lines: list[str] = []
    for element in entry.find_all(["p", "table"]):
        if element.name == "p" and element.find_parent("table"):
            continue
        if element.find_parent("div", id=lambda value: value and value.startswith("bg-showmore-hidden-")):
            continue

        fragment = BeautifulSoup(str(element), "html.parser").find(element.name)
        if fragment is None:
            continue
        for ad in fragment.find_all(["ins", "script"]):
            ad.decompose()

        def replace_controls(node) -> None:
            for tag in node.find_all("br"):
                tag.replace_with("\n")
            for control in node.find_all("input"):
                control_type = (control.get("type") or "text").lower()
                if control_type == "checkbox":
                    control.replace_with(CHECKBOX_MARKER)
                elif control_type == "text":
                    control.replace_with(BLANK_MARKER)
                else:
                    control.decompose()

        def append_text(raw: str) -> None:
            for line in raw.splitlines():
                normalized = re.sub(r"[ \t\r\f\v]+", " ", line).strip()
                if not normalized:
                    continue
                # A few source paragraphs put the next question header after a
                # sentence without a <br>. Split that structural boundary while
                # leaving ordinary instruction text containing "Questions" intact.
                chunks = re.split(r"(?<=\.)\s+(?=Questions?\s+\d+\b)", normalized, flags=re.IGNORECASE)
                lines.extend(chunk.strip() for chunk in chunks if chunk.strip())

        if element.name == "table":
            replace_controls(fragment)
            for row in fragment.find_all("tr"):
                cells = row.find_all(["th", "td"], recursive=False)
                values = [_normalize_text(cell.get_text(" ", strip=False)) for cell in cells]
                append_text(" | ".join(values))
        else:
            replace_controls(fragment)
            append_text(fragment.get_text("", strip=False))
    return lines


def _question_header_numbers(line: str) -> list[int]:
    match = QUESTION_HEADER_RE.search(line.strip())
    if not match:
        return []
    first = int(match.group(1))
    second = match.group(2) or match.group(3)
    return [first, int(second)] if second else [first]


def _instruction_kind(line: str) -> Optional[str]:
    lower = line.lower()
    if "from the box" in lower or "from box" in lower or "next to questions" in lower:
        return "matching"
    if re.search(r"\bcomplete\s+the\s+(?:notes?|form|table|flow(?:-chart)?)\b", lower):
        return "note-completion"
    if "choose the correct letter" in lower:
        return "multiple-choice"
    if re.search(r"\bchoose\s+(?:two|six|seven)\s+letters?\b", lower):
        return "multiple-choice"
    return None


def _clean_question_text(text: str) -> str:
    text = text.replace(BLANK_MARKER, "")
    text = re.sub(r"\(\d+\)", "", text)
    text = _normalize_text(text)
    text = LEADING_LIST_MARKER_RE.sub("", text)
    # Test 202's source contains "• va (1)" for the phrase "a (1)".
    text = re.sub(r"^va\b", "a", text, flags=re.IGNORECASE)
    for pattern, replacement in KNOWN_OCR_REPLACEMENTS:
        text = pattern.sub(replacement, text)
    return text.strip(" -–—")


def _split_multi_answer(answer: str) -> list[str]:
    values = re.split(r"\s*(?:,|/|\band\b)\s*", answer.strip(), flags=re.IGNORECASE)
    return [value.strip().upper() for value in values if value.strip()]


def _part_title(lines: list[str]) -> Optional[str]:
    for line in lines:
        if PART_RE.match(line) or _instruction_kind(line):
            continue
        if QUESTION_HEADER_RE.match(line):
            continue
        if (
            COMPLETION_RE.search(line)
            or NUMBERED_RE.match(line)
            or CHECKBOX_OPTION_RE.match(line)
            or BOX_OPTION_RE.match(line)
        ):
            continue
        if line in {"Topics", "Opinions", "Speakers", "Developments", "Background", "Recent research"}:
            continue
        lower = line.lower()
        if lower.startswith(("in which ", "which ", "what opinion ", "the students ")):
            continue
        return _clean_question_text(line) or None
    return None


def _build_note_group(raw: _RawGroup, answers: dict[int, str], part_id: str) -> QuestionGroup:
    questions: list[SimpleQuestion] = []
    context: list[str] = []
    for line in raw.lines:
        matches = list(COMPLETION_RE.finditer(line))
        if not matches:
            context.append(line)
            continue
        statement = _clean_question_text(line)
        for match in matches:
            number = int(match.group(1))
            questions.append(SimpleQuestion(id=number, statement=statement, answer=answers.get(number, "")))

    return QuestionGroup(
        id=f"g-{part_id.replace('-', '')}-q{questions[0].id if questions else 'unknown'}",
        type="note-completion",
        passage_id=part_id,
        instruction=raw.instruction,
        questions=questions,
        shared_text=_normalize_text(" ".join(context)) or None,
    )


def _build_mc_group(raw: _RawGroup, answers: dict[int, str], part_id: str) -> QuestionGroup:
    options_by_question: dict[int, dict[str, str]] = {}
    shared_option_candidates: dict[str, str] = {}
    stems: dict[int, str] = {}
    current_number: Optional[int] = None
    context: list[str] = []

    for line in raw.lines:
        option = CHECKBOX_OPTION_RE.match(line)
        if option:
            if current_number is not None:
                options_by_question.setdefault(current_number, {})[option.group(1)] = _normalize_text(option.group(2))
            else:
                shared_option_candidates[option.group(1)] = _normalize_text(option.group(2))
            continue
        stem = NUMBERED_RE.match(line)
        if stem:
            current_number = int(stem.group(1))
            stems[current_number] = _clean_question_text(stem.group(2))
            options_by_question.setdefault(current_number, {})
            continue
        if line not in {"Topics", "Opinions", "Speakers", "Developments"}:
            context.append(line)

    if raw.header_numbers and len(raw.header_numbers) == 2 and not stems:
        ids = raw.header_numbers
        pair = _split_multi_answer(answers.get(ids[0], ""))
        questions = [
            SimpleQuestion(
                id=number,
                statement=_normalize_text(" ".join(context)),
                answer=pair[index] if index < len(pair) else "",
            )
            for index, number in enumerate(ids)
        ]
    else:
        questions = [
            SimpleQuestion(
                id=number,
                statement=stems[number],
                answer=answers.get(number, ""),
                options=options or None,
            )
            for number, options in options_by_question.items()
            if number in stems
        ]

    shared_options: Optional[dict[str, str]] = None
    if not stems and shared_option_candidates:
        shared_options = shared_option_candidates
    if questions and all(question.options == questions[0].options for question in questions):
        candidate = questions[0].options
        if candidate and shared_options is None:
            shared_options = candidate
            questions = [question.model_copy(update={"options": None}) for question in questions]

    return QuestionGroup(
        id=f"g-{part_id.replace('-', '')}-q{questions[0].id if questions else 'unknown'}",
        type="multiple-choice",
        passage_id=part_id,
        instruction=raw.instruction,
        questions=questions,
        shared_text=_normalize_text(" ".join(context)) or None,
        options=shared_options,
    )


def _build_matching_group(raw: _RawGroup, answers: dict[int, str], part_id: str) -> QuestionGroup:
    options: dict[str, str] = {}
    questions: list[SimpleQuestion] = []
    for line in raw.lines:
        option = BOX_OPTION_RE.match(line)
        if option:
            options[option.group(1)] = _normalize_text(option.group(2))
            continue
        completion_matches = list(COMPLETION_RE.finditer(line))
        if completion_matches:
            statement = _clean_question_text(line)
            for completion in completion_matches:
                number = int(completion.group(1))
                questions.append(
                    SimpleQuestion(
                        id=number,
                        statement=statement,
                        answer=answers.get(number, ""),
                    )
                )
            continue
        numbered = NUMBERED_BLANK_RE.match(line)
        if numbered:
            number = int(numbered.group(1))
            questions.append(
                SimpleQuestion(
                    id=number,
                    statement=_clean_question_text(numbered.group(2)),
                    answer=answers.get(number, ""),
                )
            )

    if not options:
        letter_range = re.search(r"letters?\s+([A-Z])\s*[-–—]\s*([A-Z])", raw.instruction, re.IGNORECASE)
        if letter_range:
            start, end = (ord(letter.upper()) for letter in letter_range.groups())
            options = {chr(code): chr(code) for code in range(start, end + 1)}

    return QuestionGroup(
        id=f"g-{part_id.replace('-', '')}-q{questions[0].id if questions else 'unknown'}",
        type="matching",
        passage_id=part_id,
        instruction=raw.instruction,
        questions=questions,
        options=options or None,
    )


def _parse_part(number: int, lines: list[str], answers: dict[int, str]) -> tuple[ListeningPart, list[QuestionGroup]]:
    part_id = f"part-{number}"
    title = _part_title(lines)
    raw_groups: list[_RawGroup] = []
    current: Optional[_RawGroup] = None
    pending_numbers: list[int] = []

    def flush() -> None:
        nonlocal current
        if current is not None:
            raw_groups.append(current)
            current = None

    for line in lines:
        if PART_RE.match(line):
            pending_numbers = _question_header_numbers(line)
            continue
        header_numbers = _question_header_numbers(line) if QUESTION_START_RE.match(line.strip()) else []
        if header_numbers:
            flush()
            pending_numbers = header_numbers
            continue
        kind = _instruction_kind(line)
        if kind:
            flush()
            current = _RawGroup(kind=kind, instruction=line, lines=[], header_numbers=pending_numbers)
            pending_numbers = []
            continue
        if current is not None:
            current.lines.append(line)

    flush()
    groups: list[QuestionGroup] = []
    for raw in raw_groups:
        if raw.kind == "note-completion":
            group = _build_note_group(raw, answers, part_id)
        elif raw.kind == "matching":
            group = _build_matching_group(raw, answers, part_id)
        else:
            group = _build_mc_group(raw, answers, part_id)
        if group.questions:
            groups.append(group)
    return ListeningPart(id=part_id, number=number, title=title), groups


def _segment_parts(lines: list[str]) -> list[tuple[int, list[str]]]:
    parts: list[tuple[int, list[str]]] = []
    current_number: Optional[int] = None
    current_lines: list[str] = []
    for line in lines:
        match = PART_RE.match(line)
        if match:
            if current_number is not None:
                parts.append((current_number, current_lines))
            current_number = int(match.group(1))
            current_lines = [line]
        elif current_number is not None:
            current_lines.append(line)
    if current_number is not None:
        parts.append((current_number, current_lines))
    return parts


def parse_listening_test(html: str, url: str) -> ListeningTest:
    soup = BeautifulSoup(html, "html.parser")
    entry = soup.select_one("div.entry-content") or soup.select_one("article[id^='post-']")
    if entry is None:
        raise ValueError("Unable to find entry-content block in listening page HTML")

    audio = entry.select_one("audio[src]") or soup.select_one("audio[src]")
    audio_value = audio.get("src") if audio else None
    if not audio_value:
        audio_link = entry.select_one("a[href$='.mp3' i]") or soup.select_one("a[href$='.mp3' i]")
        audio_value = audio_link.get("href") if audio_link else None
    audio_url = _normalize_url(audio_value, url)
    if not audio_url:
        raise ValueError("Unable to find listening audio src")

    answers = _extract_answers(soup)
    lines = _linearize_entry(entry)
    parsed_parts = [_parse_part(number, part_lines, answers) for number, part_lines in _segment_parts(lines)]
    test_id = _extract_test_id(url)
    return ListeningTest(
        id=test_id,
        title=_extract_title(soup, test_id),
        audio_url=audio_url,
        parts=[part for part, _ in parsed_parts],
        question_groups=[group for _, groups in parsed_parts for group in groups],
        source_url=url,
    )
