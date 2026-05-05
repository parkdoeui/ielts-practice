"""
AI-powered repair/polish step using Vertex AI (Gemini).

Unlike `ai_validator.py` (diagnostic-only), this module returns a corrected
ReadingTest JSON object that is then validated deterministically before saving.
"""

from __future__ import annotations

import json
import re
from typing import Any

from bs4 import BeautifulSoup

from models import ReadingTest


def _extract_entry_text(source_html: str, max_chars: int = 12000) -> str:
    soup = BeautifulSoup(source_html, "html.parser")
    entry = soup.find("div", class_="entry-content")
    if entry:
        full_text = entry.get_text(separator="\n", strip=True)
    else:
        full_text = source_html

    if len(full_text) <= max_chars:
        return full_text

    half = max_chars // 2
    return full_text[:half] + "\n...[middle truncated]...\n" + full_text[-half:]


def _strip_json_fence(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    return raw.strip()


def _build_repair_prompt(test: ReadingTest, page_text: str) -> str:
    test_json = json.dumps(test.model_dump(), indent=2, ensure_ascii=False)

    # NOTE: we keep the source excerpt small-ish; the repair model should be
    # conservative and operate primarily on the provided JSON and excerpt.
    return f"""You are polishing parsed IELTS Academic Reading test JSON against its source page text.

Goal: fix structural extraction issues that are difficult to handle with pure heuristics, while preserving the schema.

Hard rules:
- Respond with ONLY valid JSON. No markdown.
- The top-level JSON object MUST have exactly these keys: "reading_test" and "repair_report".
- Preserve the ReadingTest schema exactly (field names and types).
- Preserve: `id`, `source_url`, `time_limit_minutes`, `test_type` unless they are missing/empty in the input JSON.
- Keep exactly 3 passages.
- Keep exactly 40 questions with IDs 1 through 40 (no gaps, no duplicates).
- Do NOT invent content that isn't supported by the source text excerpt.
- Do NOT editorially fix typos that appear in the source text; only fix parser corruption/garbling.

Fix ONLY these kinds of issues when clearly provable:
- Wrong question group `type` given the instruction (e.g. multiple-choice vs sentence-completion).
- Missing group context (`shared_text`, `word_list`, `options`, `image_url`) when it exists in the source.
- Broken `image_url`: if the source has a relative path, make it absolute using base `https://practicepteonline.com/`.
- Instruction text incorrectly leaked into question statements, or vice versa.
- Missing question statements when the source clearly shows numbered statements.

SOURCE PAGE TEXT EXCERPT:
{page_text}

CURRENT PARSED JSON:
{test_json}

Return this JSON object:
{{
  "reading_test": <FULL corrected ReadingTest JSON>,
  "repair_report": {{
    "changes": ["short bullet describing each change"],
    "confidence": 0.0
  }}
}}"""


def ai_repair(
    test: ReadingTest,
    source_html: str,
    project: str,
    location: str = "us-central1",
    model: str = "gemini-2.5-pro",
    page_text_max_chars: int = 12000,
) -> tuple[ReadingTest, dict[str, Any]]:
    """
    Return (repaired_test, repair_report).

    The returned repaired_test MUST validate against ReadingTest schema.
    """
    from google import genai

    client = genai.Client(vertexai=True, project=project, location=location)

    page_text = _extract_entry_text(source_html, max_chars=page_text_max_chars)
    prompt = _build_repair_prompt(test, page_text)

    response = client.models.generate_content(model=model, contents=prompt)
    raw = _strip_json_fence((response.text or "").strip())

    payload = json.loads(raw)
    if isinstance(payload, dict) and "reading_test" in payload:
        reading_test_obj = payload["reading_test"]
        report = payload.get("repair_report", {"changes": [], "confidence": 0.5})
    elif isinstance(payload, dict) and {"id", "passages", "question_groups"}.issubset(payload.keys()):
        # Be tolerant if the model returns the ReadingTest object directly.
        reading_test_obj = payload
        report = {"changes": ["Model returned ReadingTest object without wrapper"], "confidence": 0.5}
    else:
        if isinstance(payload, dict):
            keys = ", ".join(sorted(payload.keys()))
            raise KeyError(f"AI repair JSON missing 'reading_test' (top-level keys: {keys})")
        raise TypeError(f"AI repair returned non-object JSON: {type(payload).__name__}")

    repaired = ReadingTest.model_validate(reading_test_obj)
    if not isinstance(report, dict):
        report = {"changes": [f"repair_report had unexpected type: {type(report).__name__}"], "confidence": 0.0}

    return repaired, report
