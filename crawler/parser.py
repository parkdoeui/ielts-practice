"""
IELTS reading test HTML parser — 3-phase pipeline.

Phase 1 (_normalize_dom):   Strip noise, ads, empty wrappers. Stop at Show Answers.
Phase 2 (_classify_blocks): Label each element with a type independently.
Phase 3 (_segment_test):    Segment blocks into passages and raw question groups
                             using question_headers as reliable anchors.
Phase 4 (_build_question_groups): Classify question types (unchanged from v1).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from bs4 import BeautifulSoup
import re
import uuid
from models import ReadingTest, Passage, SimpleQuestion, QuestionGroup

QUESTION_RANGE_SEPARATORS = r"[-–—]"

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _is_interstitial_section_noise(text: str) -> bool:
    return bool(re.match(r'(?i)^cambridge ielts test\b', text.strip()))


def _is_passage_content(text: str) -> bool:
    """True if text is genuine reading-passage prose (not question material).

    Rejects:
      - MC option blocks: ≥2 lines starting with a letter+space, OR ≥2 standalone
        single-letter lines (A, B, C, D each on their own line due to <br/> splits)
      - Summary fill-in-blank patterns (…, _, (N) ___)
      - Text containing question headers
    """
    if len(text) < 100:
        return False
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    # "A word" style option lines (letter + space + text on same line)
    option_lines = sum(1 for l in lines if re.match(r"^[A-K]\s+\S", l))
    if option_lines >= 2:
        return False
    # Standalone single-letter lines from <br/>-split MC options (A, B, C each alone)
    standalone_letters = sum(1 for l in lines if re.match(r"^[A-K]$", l))
    if standalone_letters >= 2:
        return False
    if re.search(r"[…_]{3,}", text):
        return False
    if re.search(r"\(\d+\)\s*[…_]", text):
        return False
    if re.search(r"(?i)Questions?\s+\d+", text):
        return False
    return True


def _sanitize_shared_text(text: str | None) -> str | None:
    if text is None:
        return None
    stripped = text.strip()
    if not stripped:
        return None
    if stripped.lower().startswith("show answers"):
        return None
    return stripped


# ---------------------------------------------------------------------------
# Phase 1: DOM normalization
# ---------------------------------------------------------------------------

def _normalize_dom(entry_content) -> list:
    """Strip noise elements and stop at Show Answers.

    Removes: <ins> ad blocks, addtoany share widgets, show-more toggle inputs.
    Returns: list of meaningful element nodes (non-empty, non-ad).
    """
    result = []
    for child in entry_content.children:
        if child.name is None:
            continue
        # Check "Show Answers" boundary BEFORE filtering buttons/inputs so we don't skip the trigger
        text = child.get_text(strip=True)
        if "Show Answers" in text and child.name in ("p", "button", "div", "strong", "h2", "h3"):
            # If "Show Answers" comes from an embedded button inside a <p> that also
            # contains question content, include the element (cleaned) then stop.
            if child.name == "p":
                btn = child.find("button")
                if btn and "Show Answers" in btn.get_text(strip=True):
                    clean = BeautifulSoup(str(child), "html.parser").find("p")
                    # Also strip hidden divs (answer containers) in addition to buttons/inputs/ins
                    for noise in clean.find_all(["button", "input", "ins", "div"]):
                        noise.decompose()
                    if clean.get_text(strip=True):
                        result.append(clean)
            break
        if child.name == "ins":
            continue
        if child.name in ("input", "button"):
            continue
        cls = " ".join(child.get("class", []))
        if "addtoany" in cls or "a2a_" in cls:
            continue
        result.append(child)
    return result


# ---------------------------------------------------------------------------
# Phase 2: Block classification
# ---------------------------------------------------------------------------

@dataclass
class Block:
    element: Any
    text: str
    type: str   # question_header | passage_title | noise | image |
                # short_p | long_p | question_body | other
    img_url: str | None = None


def _extract_image_url(element) -> str | None:
    """Extract image URL, handling lazy-loaded data-src and <figure> wrappers."""
    img = element if element.name == "img" else element.find("img")
    if not img:
        fig = element if element.name == "figure" else element.find("figure")
        if fig:
            img = fig.find("img")
    if not img:
        return None
    url = img.get("data-src") or img.get("src") or None
    if url and url.startswith("data:"):
        url = None
    return url


_NOISE_SHORT_PATTERNS = [
    r"(?i)^cambridge ielts test\b",
    r"(?i)^show answers\b",
    # Note: "Example Answer" lines are handled line-by-line in _parse_children_text
    # rather than here, so that elements containing both example answers AND real
    # question statements (e.g. "14. Paragraph B") are not discarded entirely.
]


def _classify_blocks(children: list) -> list[Block]:
    """Classify each DOM element into a Block type.

    Types:
      question_header  — contains "Questions N-M" or "Question N" with instruction
      passage_title    — heading tag (h1-h6)
      noise            — Cambridge IELTS promo, "List of Headings", share widgets
      image            — <figure> or element containing <img>
      short_p          — short <p> (< 100 chars) — resolved as passage_title or
                         question_body in the segmenter
      long_p           — <p> with > 200 chars — likely passage paragraph
      question_body    — numbered question line (starts with digit)
      other            — everything else (instruction text, options, etc.)
    """
    blocks = []
    for el in children:
        text = el.get_text(separator="\n", strip=True)

        # Images may have no text — classify them before the empty-text guard
        if not text and (el.name in ("figure", "img") or el.find("img")):
            img_url = _extract_image_url(el)
            if img_url:
                blocks.append(Block(el, "", "image", img_url=img_url))
            continue

        if not text:
            continue

        # Question header: "Questions N-M" or "Question N" at the START of a line
        # (use multiline ^ so "(Questions 34-39)" in the middle of a line doesn't match)
        if re.search(r"(?im)^Questions?\s+\d+", text):
            img_url = _extract_image_url(el) if el.find("img") else None
            blocks.append(Block(el, text, "question_header", img_url=img_url))
            continue

        # Heading tags: always passage titles
        if el.name in ("h1", "h2", "h3", "h4", "h5", "h6"):
            blocks.append(Block(el, text, "passage_title"))
            continue

        # Known noise patterns
        if any(re.match(p, text.strip()) for p in _NOISE_SHORT_PATTERNS):
            blocks.append(Block(el, text, "noise"))
            continue
        if "Show Answers" in text:
            blocks.append(Block(el, text, "noise"))
            continue

        # "Reading Passage N" / "Reading Passage One" — section boundary marker,
        # treat as passage_title so the segmenter flushes and starts a new passage.
        if re.match(r"(?i)^reading passage\b", text.strip()):
            blocks.append(Block(el, text, "passage_title"))
            continue

        # Image / figure — only if there's an actual <img> tag inside
        if el.name == "img" or el.find("img"):
            img_url = _extract_image_url(el)
            blocks.append(Block(el, text, "image", img_url=img_url))
            continue

        # Short paragraph: ambiguous — resolved in segmenter
        if el.name == "p" and len(text) < 100:
            if re.match(r"^\d+", text):
                blocks.append(Block(el, text, "question_body"))
            else:
                blocks.append(Block(el, text, "short_p"))
            continue

        # Long paragraph: likely passage content
        if el.name == "p" and len(text) > 200:
            blocks.append(Block(el, text, "long_p"))
            continue

        # Everything else
        blocks.append(Block(el, text, "other"))

    return blocks


# ---------------------------------------------------------------------------
# Phase 3: Segmentation
# ---------------------------------------------------------------------------

def _is_passage_title_candidate(text: str, blocks: list[Block], current_index: int) -> bool:
    """Lookahead check: is this short text the title of an upcoming passage?

    Returns True if the next substantial block within ~20 elements is genuine
    passage content (not question material).

    Rejection rules for the candidate itself:
      - starts with a digit
      - starts with known question words / section markers
    """
    if re.match(r"^\d+", text):
        return False
    if re.match(r"(?i)^(which|choose|select|for each|where|complete|answer|true|false|yes|no|not given|write|nb\b|note\b|according to)\b", text):
        return False
    if re.match(r"(?i)^(list of|example\b|reading passage\b)", text):
        return False
    # Reject MC option blocks: "A\nsome option text" (letter alone on first line)
    if re.match(r"^[A-K]\n", text):
        return False
    # Reject option lists: standalone letter lines (A, B, C each on own line)
    lines_check = [l.strip() for l in text.split("\n") if l.strip()]
    standalone = sum(1 for l in lines_check if re.match(r"^[A-K]$", l))
    if standalone >= 2:
        return False
    option_check = sum(1 for l in lines_check if re.match(r"^[A-K]\s+\S", l))
    if option_check >= 2:
        return False

    for j in range(current_index + 1, min(current_index + 25, len(blocks))):
        b = blocks[j]
        if b.type in ("question_header", "passage_title"):
            return False  # Hit another structural anchor — no passage content found
        if b.type == "noise":
            continue
        if b.type == "long_p":
            return _is_passage_content(b.text)
        # short_p / question_body / other — keep scanning

    return False


def _segment_test(blocks: list[Block]) -> tuple[list[Passage], list[dict]]:
    """Segment classified blocks into passages and raw question groups.

    Uses question_header blocks as the primary anchors:
      - question_header → flush current passage, switch to QUESTIONS mode
      - passage_title (heading) or confirmed short_p → switch to PASSAGE mode
      - Everything else accumulates into the current passage or question group
    """
    passages: list[Passage] = []
    raw_groups: list[dict] = []

    current_passage_text: list[str] = []
    current_passage_title: str = ""
    passage_count = 1
    state = "PASSAGE"
    current_q_group: dict | None = None

    def flush_passage():
        nonlocal passage_count, current_passage_text, current_passage_title
        if current_passage_text:
            passages.append(Passage(
                id=f"passage-{passage_count}",
                title=current_passage_title or f"Passage {passage_count}",
                text="\n\n".join(current_passage_text),
                paragraphs=current_passage_text,
            ))
            passage_count += 1
        current_passage_text = []
        current_passage_title = ""

    for i, block in enumerate(blocks):

        # --- Skip noise in all modes ---
        if block.type == "noise":
            continue

        # --- Question header: reliable anchor ---
        if block.type == "question_header":
            flush_passage()
            state = "QUESTIONS"

            p_id = passages[-1].id if passages else "passage-1"
            q_range = re.search(
                rf"(?i)Questions?\s+(\d+)\s*{QUESTION_RANGE_SEPARATORS}\s*(\d+)",
                block.text,
            )
            q_and = re.search(r"(?i)Questions?\s+(\d+)\s+and\s+(\d+)", block.text)
            q_single = re.search(r"(?i)Question\s+(\d+)", block.text)
            q_match = q_range or q_and
            start_q = int(q_match.group(1)) if q_match else (int(q_single.group(1)) if q_single else 0)
            end_q = int(q_match.group(2)) if q_match else start_q

            # If the block contains content BEFORE the "Questions N-M" marker
            # (e.g. numbered question statements from the previous group),
            # append that prefix to the previous group's text.
            header_match = q_match or q_single
            if header_match and header_match.start() > 0 and current_q_group is not None:
                prefix = block.text[: header_match.start()].strip()
                if prefix:
                    current_q_group["text"] += "\n" + prefix
            # Use only the text from the "Questions N-M" marker onwards as instruction
            if header_match:
                instruction_text = block.text[header_match.start():].strip()
            else:
                instruction_text = block.text

            current_q_group = {
                "start": start_q,
                "end": end_q,
                "instruction": instruction_text,
                "text": "",
                "passage_id": p_id,
                "image_url": block.img_url,  # may be embedded in the header <p>
            }
            raw_groups.append(current_q_group)
            continue

        # --- Passage title (heading tag): always triggers passage mode ---
        if block.type == "passage_title":
            flush_passage()
            state = "PASSAGE"
            current_passage_title = block.text
            continue

        # --- Image: attach to current question group ---
        if block.type == "image":
            if state == "QUESTIONS" and current_q_group and not current_q_group["image_url"]:
                current_q_group["image_url"] = block.img_url or ""
            continue

        # --- Short paragraph: resolve via lookahead ---
        if block.type == "short_p":
            if state == "QUESTIONS":
                if _is_passage_title_candidate(block.text, blocks, i):
                    flush_passage()
                    state = "PASSAGE"
                    current_passage_title = block.text
                else:
                    if current_q_group is not None:
                        current_q_group["text"] += "\n" + block.text
            else:  # PASSAGE mode
                # Short p at start of passage (before any body paragraphs) — check if title
                if not current_passage_text and not current_passage_title:
                    if _is_passage_title_candidate(block.text, blocks, i):
                        current_passage_title = block.text
                    else:
                        current_passage_text.append(block.text)
                else:
                    current_passage_text.append(block.text)
            continue

        # --- Question body (numbered line) ---
        if block.type == "question_body":
            if state == "QUESTIONS" and current_q_group is not None:
                current_q_group["text"] += "\n" + block.text
            continue

        # --- Long paragraph and other content ---
        if state == "PASSAGE":
            current_passage_text.append(block.text)
        elif state == "QUESTIONS" and current_q_group is not None:
            current_q_group["text"] += "\n" + block.text

    flush_passage()
    return passages, raw_groups


# ---------------------------------------------------------------------------
# Phase 4: Question group building (unchanged from v1)
# ---------------------------------------------------------------------------

def _parse_children_text(header: str, children_text: str, start_q: int, end_q: int):
    """Parse the children text of a question group to extract:
    - full_instruction: header + explanation text (e.g. YES/NO/NOT GIVEN definitions)
    - individual_questions: dict mapping question number -> statement text
    - options: dict mapping option letter -> option text (for MC questions)
    - stem_text: question stem or passage text (for MC stems, summary passages, etc.)
    """
    lines = children_text.strip().split("\n")

    instruction_lines = []
    numbered_questions = {}
    options = {}
    stem_lines = []

    numbered_pattern = re.compile(r"^(\d+)\.?\s+(.*)")
    option_inline_pattern = re.compile(r"^([A-Z])\s+(.*)")
    heading_option_pattern = re.compile(r"^(i{1,3}|iv|vi{0,3}|ix|x)\.?\s+(.*)")
    option_standalone_pattern = re.compile(r"^([A-Z])$")
    instruction_kw_pattern = re.compile(r"^(YES|NO|TRUE|FALSE|NOT GIVEN)\b", re.IGNORECASE)
    instruction_cont_pattern = re.compile(r"^if (the statement|there is|it is)", re.IGNORECASE)

    in_instruction_block = False
    pending_option_letter = None
    last_qnum = None  # track most recently parsed question number (for multi-line questions)

    # Pre-pass: extract options embedded in the instruction header.
    # Some groups (e.g. classification) put "A\nfirst category\nB\nsecond category" in
    # the instruction text rather than in the body.
    _pre_pending = None
    for hline in header.strip().split("\n")[1:]:  # skip "Questions N-M" first line
        hline = hline.strip()
        if not hline:
            continue
        if _pre_pending is not None:
            options[_pre_pending] = hline
            _pre_pending = None
            continue
        heading_match = heading_option_pattern.match(hline)
        if heading_match:
            options[heading_match.group(1).lower()] = heading_match.group(2).strip()
            continue
        opt_m = option_inline_pattern.match(hline)
        if opt_m and len(opt_m.group(2)) > 1:
            options[opt_m.group(1)] = opt_m.group(2).strip()
            continue
        if option_standalone_pattern.match(hline):
            _pre_pending = hline

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Skip noise lines (Example Answer, Cambridge IELTS promo, etc.)
        # Note: "Show Answers" is intentionally NOT skipped here — it needs to
        # propagate to stem_text so _sanitize_shared_text can detect and reject it.
        if (re.match(r'(?i)^example\b', line)
                or re.match(r'(?i)^cambridge ielts\b', line)):
            last_qnum = None
            continue

        if pending_option_letter is not None:
            options[pending_option_letter] = line
            pending_option_letter = None
            last_qnum = None
            in_instruction_block = False
            continue

        # Handle "(N)..." parenthesized blanks in classification/form tables.
        # The statement (row label) is on the preceding stem line — but only use it
        # if it looks like a simple name label (short, letters/hyphens only, no parens).
        paren_q_match = re.match(r'^\((\d+)\)', line)
        if paren_q_match:
            qnum = int(paren_q_match.group(1))
            if start_q <= qnum <= end_q:
                stmt = ""
                if stem_lines:
                    candidate = stem_lines[-1]
                    # Only use as statement if it's a name-like label (no digits, no parens)
                    if re.match(r'^[A-Za-z][A-Za-z\-\s]+$', candidate) and len(candidate) <= 30:
                        stmt = stem_lines.pop()
                numbered_questions[qnum] = stmt
                if not stmt:
                    # No label found; preserve the blank marker in stem so
                    # it appears in shared_text (gives form/table context to the reader)
                    stem_lines.append(line)
                last_qnum = None  # next line is a new row label, not a continuation
                in_instruction_block = False
                continue

        num_match = numbered_pattern.match(line)
        if num_match:
            qnum = int(num_match.group(1))
            if start_q <= qnum <= end_q:
                numbered_questions[qnum] = num_match.group(2).strip()
                last_qnum = qnum
                in_instruction_block = False
                continue
            else:
                last_qnum = None  # out-of-range number, stop continuation

        if instruction_kw_pattern.match(line) or instruction_cont_pattern.match(line):
            instruction_lines.append(line)
            in_instruction_block = True
            continue

        heading_match = heading_option_pattern.match(line)
        if heading_match:
            options[heading_match.group(1).lower()] = heading_match.group(2).strip()
            in_instruction_block = False
            continue

        opt_match = option_inline_pattern.match(line)
        if opt_match and len(opt_match.group(2)) > 1:
            # Check if this is "SECTION_LETTER QUESTION_NUM statement" pattern:
            # e.g. "B 2 Section C" where B is the label for Q1, 2 starts Q2.
            rest = opt_match.group(2)
            digit_match = re.match(r'^(\d+)\s+(.*)', rest)
            if digit_match and last_qnum is not None:
                qnum2 = int(digit_match.group(1))
                if start_q <= qnum2 <= end_q:
                    # Append the letter to the previous question's statement
                    prev_letter = opt_match.group(1)
                    if last_qnum in numbered_questions:
                        numbered_questions[last_qnum] = (numbered_questions[last_qnum] + " " + prev_letter).strip()
                    numbered_questions[qnum2] = digit_match.group(2).strip()
                    last_qnum = qnum2
                    in_instruction_block = False
                    continue
            options[opt_match.group(1)] = opt_match.group(2).strip()
            last_qnum = None
            in_instruction_block = False
            continue

        opt_standalone = option_standalone_pattern.match(line)
        if opt_standalone:
            pending_option_letter = opt_standalone.group(1)
            last_qnum = None
            continue

        if in_instruction_block:
            instruction_lines.append(line)
            continue

        # If a non-structural line follows a numbered question (e.g. multi-line
        # question split by <br>), append it to that question rather than stem.
        if last_qnum is not None and last_qnum in numbered_questions:
            numbered_questions[last_qnum] = (numbered_questions[last_qnum] + " " + line).strip()
            continue

        stem_lines.append(line)

    full_instruction = header
    if instruction_lines:
        full_instruction = header + "\n" + "\n".join(instruction_lines)

    stem_text = "\n".join(stem_lines) if stem_lines else ""
    return full_instruction, numbered_questions, options, stem_text


def _build_question_groups(groups: list[dict], answers: dict) -> list[QuestionGroup]:
    result = []
    seen_ids: set[str] = set()

    for g in groups:
        start_q = g["start"]
        end_q = g["end"]
        passage_id = g["passage_id"]
        header = g["instruction"]
        children_text = g["text"].strip()
        image_url = g.get("image_url")

        # Deduplicate groups with the same ID
        group_id = f"group-{start_q}-{end_q}"
        if group_id in seen_ids:
            continue
        seen_ids.add(group_id)

        full_instruction, numbered_qs, options, stem_text = _parse_children_text(
            header, children_text, start_q, end_q
        )

        simple_questions = []
        for qid in range(start_q, end_q + 1):
            ans = answers.get(qid, "UNKNOWN")
            statement = numbered_qs.get(qid, "")
            simple_questions.append(SimpleQuestion(id=qid, statement=statement, answer=ans))

        instr_lower = full_instruction.lower()
        # Also search the body text for type signals when instruction is minimal (e.g. "Question 26")
        body_lower = children_text.lower()
        stem_lower = stem_text.lower()

        if "diagram" in instr_lower or "label" in instr_lower:
            result.append(QuestionGroup(
                id=group_id,
                type="diagram-labeling",
                passage_id=passage_id,
                instruction=full_instruction,
                questions=simple_questions,
                image_url=image_url or "",
            ))

        elif ("summary" in instr_lower or "notes" in instr_lower
              or "summary" in body_lower or "notes" in body_lower
              or ("complete" in instr_lower and "using" in instr_lower)):
            word_list = list(options.values()) if options else None
            shared = _sanitize_shared_text(stem_text or children_text or None)
            result.append(QuestionGroup(
                id=group_id,
                type="summary-completion",
                passage_id=passage_id,
                instruction=full_instruction,
                questions=simple_questions,
                shared_text=shared,
                word_list=word_list,
            ))

        elif (("contain" in instr_lower and ("paragraph" in instr_lower or "section" in instr_lower))
              or ("which" in instr_lower and ("paragraph" in instr_lower or "section" in instr_lower))
              or ("which" in stem_lower and ("paragraph" in stem_lower or "section" in stem_lower))
              or ("match" in instr_lower and ("person" in instr_lower or "people" in instr_lower
                                              or "statement" in instr_lower or "nationality" in instr_lower
                                              or "researcher" in instr_lower or "event" in instr_lower))
              or ("match" in body_lower and "statement" in body_lower)):
            if options:
                para_options = options
            else:
                sec_match = re.search(r"([A-Z])\s*[-–]\s*([A-Za-z])", full_instruction)
                if sec_match:
                    start_letter = ord(sec_match.group(1))
                    end_char = sec_match.group(2)
                    end_letter = ord("I") if end_char == "l" else ord(end_char.upper())
                    para_options = {chr(c): chr(c) for c in range(start_letter, end_letter + 1)}
                else:
                    para_options = {"A": "A", "B": "B", "C": "C", "D": "D", "E": "E", "F": "F"}
            result.append(QuestionGroup(
                id=group_id,
                type="matching-information",
                passage_id=passage_id,
                instruction=full_instruction,
                questions=simple_questions,
                options=para_options,
            ))

        elif "heading" in instr_lower:
            heading_options = options if options else {"i": "i", "ii": "ii", "iii": "iii", "iv": "iv", "v": "v"}
            result.append(QuestionGroup(
                id=group_id,
                type="matching-headings",
                passage_id=passage_id,
                instruction=full_instruction,
                questions=simple_questions,
                options=heading_options,
            ))

        elif ("choose" in instr_lower and "letter" in instr_lower
              or "choose" in body_lower and "letter" in body_lower):
            mc_options = options if options else {chr(65 + i): f"Option {chr(65 + i)}" for i in range(4)}
            result.append(QuestionGroup(
                id=group_id,
                type="multiple-choice",
                passage_id=passage_id,
                instruction=full_instruction,
                questions=simple_questions,
                options=mc_options,
                shared_text=_sanitize_shared_text(stem_text or None),
            ))

        elif ("not given" in instr_lower
              or re.search(r"\b(yes|no|true|false)\b.*if.*statement", instr_lower, re.DOTALL)):
            result.append(QuestionGroup(
                id=group_id,
                type="true-false-ng",
                passage_id=passage_id,
                instruction=full_instruction,
                questions=simple_questions,
            ))

        elif "classif" in instr_lower or "classif" in body_lower:
            # "Classify the following statements as referring to A ... B ... C ..."
            # options are inline in the instruction (A hand collecting, B using bait, ...)
            classif_options = options if options else None
            result.append(QuestionGroup(
                id=group_id,
                type="classification",
                passage_id=passage_id,
                instruction=full_instruction,
                questions=simple_questions,
                options=classif_options,
            ))

        elif re.search(r"correct ending", instr_lower):
            # "Complete each sentence with the correct ending, A-G, below"
            ending_options = options if options else None
            result.append(QuestionGroup(
                id=group_id,
                type="matching-sentence-endings",
                passage_id=passage_id,
                instruction=full_instruction,
                questions=simple_questions,
                options=ending_options,
            ))

        else:
            result.append(QuestionGroup(
                id=group_id,
                type="sentence-completion",
                passage_id=passage_id,
                instruction=full_instruction,
                questions=simple_questions,
                shared_text=_sanitize_shared_text(stem_text or None),
            ))

    return result


# ---------------------------------------------------------------------------
# Answer extraction (extracted from original parse_reading_test)
# ---------------------------------------------------------------------------

def _extract_answers(soup: BeautifulSoup) -> dict[int, str]:
    """Extract the answer key from the hidden answers section."""
    answers: dict[int, str] = {}
    ans_container = None

    ans_div = soup.find("div", id=lambda x: x and x.startswith("bg-showmore-hidden-"))
    if ans_div:
        div_text = ans_div.get_text(strip=True)
        if div_text and re.search(r"\d+\.\s+", div_text):
            ans_container = ans_div
        else:
            ancestor = ans_div
            while ancestor and ancestor.parent and ancestor.parent.name in ("span", "p", "div"):
                candidate = ancestor.parent.find_next_sibling(["p", "div"])
                if candidate and re.search(r"\d+\.\s+", candidate.get_text(strip=True)):
                    ans_container = candidate
                    break
                ancestor = ancestor.parent

    if not ans_container:
        btn = soup.find("button", string=lambda t: t and "Show Answers" in t)
        if btn:
            ans_container = btn.find_next_sibling("div")

    if not ans_container:
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if "Show Answers" in text or text == "Answers":
                ans_container = p.find_next_sibling(["p", "div"])
                break

    if ans_container:
        all_ans_parts = [ans_container]
        nxt = ans_container.find_next_sibling(["p", "div"])
        while nxt and re.search(r"\d+\.\s+", nxt.get_text(strip=True)):
            all_ans_parts.append(nxt)
            nxt = nxt.find_next_sibling(["p", "div"])

        for part in all_ans_parts:
            for br in part.find_all("br"):
                br.replace_with("\n")
            ans_text = part.get_text(separator="\n", strip=True)
            for line in ans_text.split("\n"):
                line = line.strip()
                match = re.match(r"^(\d+)\.\s+(.*)", line)
                if match:
                    answers[int(match.group(1))] = match.group(2).strip()

    return answers


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------

def parse_reading_test(html: str, url: str) -> ReadingTest:
    soup = BeautifulSoup(html, "html.parser")

    entry_content = soup.find("div", class_="entry-content")
    if not entry_content:
        entry_content = soup.body

    # Phase 0: Extract answers
    answers = _extract_answers(soup)

    # Phase 1: Normalize DOM
    clean_children = _normalize_dom(entry_content)

    # Phase 2: Classify blocks
    blocks = _classify_blocks(clean_children)

    # Phase 3: Segment into passages and raw question groups
    passages, raw_groups = _segment_test(blocks)

    # Phase 4: Build question groups (type classification)
    question_groups = _build_question_groups(raw_groups, answers)

    # Fallback to placeholders if completely failed
    if not passages:
        passages = _create_placeholder_passages()
    if not question_groups:
        question_groups = _create_placeholder_groups(passages)

    match = re.search(r"test-(\d+)", url)
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
    for selector in ["h1", ".test-title", ".reading-title", "title"]:
        el = soup.select_one(selector)
        if el:
            return el.get_text(strip=True)
    return "IELTS Academic Reading Test"


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
