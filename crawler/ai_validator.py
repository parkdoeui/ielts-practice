"""
AI-powered validation step using Vertex AI (Gemini 2.5 Pro).

This is a mandatory part of the crawl pipeline, not a fallback.
It validates the parsed JSON against the source HTML to catch issues
that the deterministic validator cannot detect:
  - Garbled or truncated passage text
  - Wrong question type classification
  - Instruction text that doesn't match the question type
  - Missing context (e.g. shared_text that was present in HTML but not extracted)
  - Answer key accuracy issues

Usage:
  result = ai_validate(test, source_html, project="project-d778e3ac-55b5-4b70-8dc")
  if not result["valid"]:
      for issue in result["issues"]:
          print(f"  AI: {issue}")
"""
from __future__ import annotations
import json
import re
from models import ReadingTest


def ai_validate(
    test: ReadingTest,
    source_html: str,
    project: str,
    location: str = "us-central1",
) -> dict:
    """
    Validate the parsed ReadingTest JSON against the source HTML using Gemini 2.5 Pro.

    Returns a dict:
      {
        "valid": bool,
        "issues": list[str],
        "confidence": float,  # 0.0 to 1.0
      }
    """
    from google import genai

    client = genai.Client(vertexai=True, project=project, location=location)

    # Strip HTML down to just .entry-content text to save tokens
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(source_html, "html.parser")
    entry = soup.find("div", class_="entry-content")
    page_text = entry.get_text(separator="\n", strip=True)[:12000] if entry else source_html[:12000]

    test_json = json.dumps(test.model_dump(), indent=2)

    prompt = f"""You are validating a parsed IELTS Academic Reading test JSON against its source page.
Focus ONLY on structural parsing failures — things the parser got wrong. Do NOT flag issues that are in the source HTML itself (typos in source text, answers that exceed word limits as written in source, Cyrillic/encoding quirks in source).

SOURCE PAGE TEXT (truncated to first 12000 chars):
{page_text}

PARSED JSON:
{test_json}

Flag ONLY these structural parsing failures:
1. Wrong number of passages (should be 3) — only if clearly provable from the visible source
2. Passage text is garbled or empty (blank passages, truncated mid-word)
3. Questions assigned to wrong passage
4. Question type label is completely wrong given the instruction (e.g. labelled "true-false-ng" but instruction clearly says "complete the summary with NO MORE THAN TWO WORDS")
5. A word_list or shared_text is clearly present in the source but completely absent in JSON (null when it should have content)
6. Question statements are all empty when the source clearly shows numbered question text

Do NOT flag:
- Typos or encoding issues in the source HTML (those get copied faithfully)
- Answers that exceed word limits (the source answer key may have verbose answers)
- YES/NO/NOT GIVEN vs TRUE/FALSE/NOT GIVEN distinction (treat as equivalent)
- Missing options for individual questions within a multi-question MC group (model limitation)
- Minor type classification differences (e.g. "sentence-completion" vs "short-answer" — only flag if completely wrong)
- Issues with portions of the source page that are truncated/not visible
- The `paragraphs` array having multiple items for a section that contains multiple paragraphs — that is correct behavior
- Minor inconsistencies in whether instruction text appears in `instruction` vs `shared_text` field

Respond with ONLY a JSON object (no markdown, no extra text):
{{
  "valid": true or false,
  "issues": ["description of issue 1", "description of issue 2"],
  "confidence": 0.0 to 1.0
}}

If there are no issues, return {{"valid": true, "issues": [], "confidence": 1.0}}"""

    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=prompt,
    )

    raw = response.text.strip()
    # Strip markdown code fences if present
    raw = re.sub(r'^```(?:json)?\n?', '', raw)
    raw = re.sub(r'\n?```$', '', raw)

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        # If Gemini returns something non-parseable, treat as uncertain
        return {
            "valid": False,
            "issues": [f"AI validator returned non-JSON response: {raw[:200]}"],
            "confidence": 0.0,
        }

    # Normalize shape
    return {
        "valid": bool(result.get("valid", False)),
        "issues": result.get("issues", []),
        "confidence": float(result.get("confidence", 0.5)),
    }
