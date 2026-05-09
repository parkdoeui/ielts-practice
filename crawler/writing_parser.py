from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from models import WritingTask, WritingTest


def _extract_test_id(url: str) -> str:
    match = re.search(r"ielts-writing-test-(\d+)", url, flags=re.IGNORECASE)
    if not match:
        raise ValueError(f"Unable to extract writing test number from URL: {url}")
    return f"writing-test-{match.group(1)}"


def _normalize_text(value: str) -> str:
    value = value.replace("\xa0", " ").strip()
    value = re.sub(r"\s+", " ", value)
    return value


def _extract_min_words(text: str) -> int | None:
    match = re.search(r"write at least\s+(\d+)\s+words", text, flags=re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1))


def _is_noise(text: str) -> bool:
    lower = text.lower()
    if not lower:
        return True
    return (
        "cambridge ielts tests" in lower
        or "addtoany" in lower
        or "comments are closed" in lower
        or "copyright" in lower
        or lower.startswith("advertisement")
    )


def _looks_like_instruction(text: str) -> bool:
    lower = text.lower()
    markers = (
        "write at least",
        "you should spend",
        "summarise the information",
        "summarize the information",
        "write about the following topic",
        "give reasons for your answer",
        "include relevant examples",
        "write an essay",
    )
    return any(marker in lower for marker in markers)


def _extract_image_url(element, base_url: str) -> str | None:
    img = element if getattr(element, "name", None) == "img" else element.find("img")
    if not img:
        return None
    url = (
        img.get("data-src")
        or img.get("data-lazy-src")
        or img.get("data-original")
        or img.get("src")
        or None
    )
    if not url:
        return None
    if url.startswith("data:"):
        return None
    return urljoin(base_url, url.strip())


def _extract_table(element) -> list[list[str]] | None:
    table = element if getattr(element, "name", None) == "table" else element.find("table")
    if not table:
        return None
    rows: list[list[str]] = []
    for tr in table.find_all("tr"):
        cells = [_normalize_text(cell.get_text(" ", strip=True)) for cell in tr.find_all(["th", "td"])]
        if any(cells):
            rows.append(cells)
    return rows or None


def _collect_entry_blocks(entry, base_url: str) -> list[dict]:
    blocks: list[dict] = []
    for element in entry.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6", "figure", "img", "table"], recursive=True):
        if element.find_parent("figure") and element.name == "table":
            continue
        text = _normalize_text(element.get_text(" ", strip=True))
        image_url = _extract_image_url(element, base_url)
        table = _extract_table(element)
        if not text and not image_url and not table:
            continue
        if text.lower().startswith("sample answer"):
            break
        if text.lower().startswith("comments are closed"):
            break
        blocks.append({"text": text, "image_url": image_url, "table": table})
    return blocks


def parse_writing_test(html: str, url: str) -> WritingTest:
    soup = BeautifulSoup(html, "html.parser")
    title_node = soup.find(["h1", "h2"], class_=re.compile(r"entry-title|page-title")) or soup.find("title")
    title_raw = title_node.get_text(" ", strip=True) if title_node else _extract_test_id(url)
    title = _normalize_text(title_raw)

    entry = soup.find("div", class_="entry-content")
    if not entry:
        raise ValueError("Unable to find entry-content block in writing page HTML")

    blocks = _collect_entry_blocks(entry, url)
    task_index = 0
    prompts: dict[int, list[str]] = {1: [], 2: []}
    instructions: dict[int, list[str]] = {1: [], 2: []}
    min_words: dict[int, int | None] = {1: None, 2: None}
    task_1_image_url: str | None = None
    task_1_table: list[list[str]] | None = None

    for block in blocks:
        text = block["text"]
        image_url = block["image_url"]
        table = block["table"]
        normalized = text.lower()

        if "task 1" in normalized and normalized.startswith("task"):
            task_index = 1
            remainder = re.sub(r"(?i)^task\s*1\s*:?\s*", "", text).strip()
            if remainder:
                prompts[1].append(remainder)
            continue
        if "task 2" in normalized and normalized.startswith("task"):
            task_index = 2
            remainder = re.sub(r"(?i)^task\s*2\s*:?\s*", "", text).strip()
            if remainder:
                prompts[2].append(remainder)
            continue

        if image_url and task_index == 1 and not task_1_image_url:
            task_1_image_url = image_url

        if table and task_index == 1 and not task_1_table:
            task_1_table = table
            continue

        if task_index not in (1, 2):
            continue
        if _is_noise(text):
            continue

        candidate_min_words = _extract_min_words(text)
        if candidate_min_words is not None:
            min_words[task_index] = candidate_min_words
            instructions[task_index].append(text)
            continue

        if _looks_like_instruction(text):
            instructions[task_index].append(text)
            continue

        if text.endswith("?") or text.endswith("."):
            # Keep prompts concise; push extra sentence-like blocks to instructions.
            if len(prompts[task_index]) >= 3:
                instructions[task_index].append(text)
                continue
            prompts[task_index].append(text)
        else:
            instructions[task_index].append(text)

    task_1_prompt = " ".join(prompts[1]).strip()
    task_2_prompt = " ".join(prompts[2]).strip()
    if not task_1_prompt or not task_2_prompt:
        raise ValueError("Failed to extract Task 1/Task 2 prompts from writing page")

    return WritingTest(
        id=_extract_test_id(url),
        title=title,
        test_type="academic",
        tasks=[
            WritingTask(
                task_number=1,
                task_type="academic-task-1",
                prompt=task_1_prompt,
                instructions=instructions[1],
                min_words=min_words[1] or 150,
                image_url=task_1_image_url,
                table=task_1_table,
            ),
            WritingTask(
                task_number=2,
                task_type="essay",
                prompt=task_2_prompt,
                instructions=instructions[2],
                min_words=min_words[2] or 250,
            ),
        ],
        time_limit_minutes=60,
        source_url=url,
    )
