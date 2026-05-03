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
    page_text = entry.get_text(separator="\n", strip=True)[:6000] if entry else source_html[:6000]

    test_json = json.dumps(test.model_dump(), indent=2)

    prompt = f"""You are validating a parsed IELTS Academic Reading test JSON against its source page.

SOURCE PAGE TEXT (truncated to first 6000 chars):
{page_text}

PARSED JSON:
{test_json[:8000]}

Check for any of these issues:
1. Wrong number of passages (should be 3)
2. Passage text is garbled, truncated, or empty
3. Questions assigned to wrong passage
4. Question type classification looks wrong (e.g. labelled "true-false-ng" but instruction says "complete the summary")
5. Instructions missing key details (e.g. "NO MORE THAN TWO WORDS" limit)
6. shared_text or word_list present in source but missing in JSON
7. Answer key values that look wrong or inconsistent

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
