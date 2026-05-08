from __future__ import annotations

import json
import re

from bs4 import BeautifulSoup

from models import WritingTest


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


def ai_validate_writing(
    test: WritingTest,
    source_html: str,
    project: str,
    location: str = "us-central1",
    model: str = "gemini-2.5-pro",
    page_text_max_chars: int = 12000,
) -> dict:
    from google import genai

    client = genai.Client(vertexai=True, project=project, location=location)
    page_text = _extract_entry_text(source_html, max_chars=page_text_max_chars)
    test_json = json.dumps(test.model_dump(), indent=2, ensure_ascii=False)

    prompt = f"""You validate parsed IELTS Writing test JSON against source page text.
Only flag structural extraction failures.

SOURCE PAGE TEXT:
{page_text}

PARSED JSON:
{test_json}

Validate only:
1) Task 1 and Task 2 prompts are extracted and not swapped.
2) Task 1 diagram image_url exists and looks valid if image exists in source.
3) Min words for Task 1 and Task 2 match source instructions.
4) Title and source_url are coherent.
5) Non-prompt noise (comments/share widgets/sample answers) is not mixed into task prompts.

Ignore:
- Source typos.
- Minor punctuation/casing differences.
- Content that appears only outside the provided source excerpt.

Return ONLY JSON:
{{
  "valid": true or false,
  "issues": ["..."],
  "confidence": 0.0 to 1.0
}}"""

    response = client.models.generate_content(model=model, contents=prompt)
    raw = _strip_json_fence(response.text or "")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "valid": False,
            "issues": [f"AI writing validator returned non-JSON response: {raw[:200]}"],
            "confidence": 0.0,
        }
    return {
        "valid": bool(payload.get("valid", False)),
        "issues": list(payload.get("issues", [])),
        "confidence": float(payload.get("confidence", 0.0)),
    }
