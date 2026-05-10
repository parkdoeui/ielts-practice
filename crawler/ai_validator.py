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


def _build_validation_prompt(test: ReadingTest, page_text: str) -> str:
    test_json = json.dumps(test.model_dump(), indent=2)

    return f"""You are validating a parsed IELTS Academic Reading test JSON against its source page.
Focus ONLY on structural parsing failures — things the parser got wrong. Do NOT flag issues that are in the source HTML itself (typos in source text, answers that exceed word limits as written in source, Cyrillic/encoding quirks in source).

SOURCE PAGE TEXT (first 10000 + last 10000 chars if long):
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
7. Multiple-choice groups where each numbered question has its own visible A/B/C/D option block in the source, but the JSON only preserves one shared option set or omits options for earlier questions. In this case, each question must have its own `options` object.
8. Matching-sentence-ending groups where the source shows one shared endings list below the numbered sentence stems, but JSON attaches that list to only one question instead of `group.options`. The numbered stems should stay as `questions[].statement`; the A-I/A-G endings should be shared group options.
9. Classification groups where the source header says "Classify the following statements as referring to" followed by A/B/C/D labels, but those labels are absent from `group.options` or attached to individual questions. The category labels must be preserved as shared group options so users can see what each letter means.

Do NOT flag:
- Typos or encoding issues in the source HTML (those get copied faithfully)
- Answers that exceed word limits (the source answer key may have verbose answers)
- YES/NO/NOT GIVEN vs TRUE/FALSE/NOT GIVEN distinction (treat as equivalent)
- Shared-option multiple-choice lists where the instruction asks for multiple answers from one common list (for example, "Choose TWO letters" or "Choose FIVE letters")
- Matching-sentence-ending questions having short unfinished sentence stems (for example, "X feeds on") — this is expected when the endings list is present in `group.options`
- Minor type classification differences (e.g. "sentence-completion" vs "short-answer" — only flag if completely wrong)
- Completion subtype naming differences. This schema does not have separate `flow-chart-completion`, `table-completion`, or `form-completion` types, so `sentence-completion` is valid for those instructions when the question IDs, answers, and shared context are otherwise preserved.
- Issues with portions of the source page that are truncated/not visible in the excerpt above — trust the JSON for sections you cannot see
- The `paragraphs` array: it is a raw list of HTML paragraph elements. Multiple items without paragraph labels is ALWAYS correct and expected — never flag paragraph splitting
- Minor inconsistencies in whether instruction text appears in `instruction` vs `shared_text` field
- Form/table completion questions (where blanks are marked as (20)… etc.) having empty question statements — this is expected when the form context is captured in shared_text or instruction

Respond with ONLY a JSON object (no markdown, no extra text):
{{
  "valid": true or false,
  "issues": ["description of issue 1", "description of issue 2"],
  "confidence": 0.0 to 1.0
}}

If there are no issues, return {{"valid": true, "issues": [], "confidence": 1.0}}"""


def ai_validate(
    test: ReadingTest,
    source_html: str,
    project: str,
    location: str = "us-central1",
    model: str = "gemini-2.5-pro",
    page_text_max_chars: int = 20000,
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

    # Strip HTML down to just .entry-content text to save tokens.
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(source_html, "html.parser")
    entry = soup.find("div", class_="entry-content")
    if entry:
        full_text = entry.get_text(separator="\n", strip=True)
        if len(full_text) > page_text_max_chars:
            half = page_text_max_chars // 2
            page_text = full_text[:half] + "\n...[middle truncated]...\n" + full_text[-half:]
        else:
            page_text = full_text
    else:
        page_text = source_html[:page_text_max_chars]

    prompt = _build_validation_prompt(test, page_text)

    response = client.models.generate_content(
        model=model,
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
