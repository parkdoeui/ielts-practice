from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, Field


class WritingGraderError(Exception):
    pass


class WritingCriteriaSchema(BaseModel):
    task_response: float = 0.0
    coherence_cohesion: float = 0.0
    lexical_resource: float = 0.0
    grammar_accuracy: float = 0.0


class WritingTaskGradeSchema(BaseModel):
    band: float = 0.0
    criteria: WritingCriteriaSchema = Field(default_factory=WritingCriteriaSchema)
    strengths: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    sample_answer: str = ""


class WritingGradeSchema(BaseModel):
    overall_band: float = 0.0
    task_1: WritingTaskGradeSchema = Field(default_factory=WritingTaskGradeSchema)
    task_2: WritingTaskGradeSchema = Field(default_factory=WritingTaskGradeSchema)
    action_points: list[str] = Field(default_factory=list)


def _strip_json_fence(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    return raw.strip()


def _normalize_band(payload: dict[str, Any]) -> dict[str, float]:
    keys = ["task_response", "coherence_cohesion", "lexical_resource", "grammar_accuracy"]
    result: dict[str, float] = {}
    for key in keys:
        result[key] = float(payload.get(key, 0.0))
    return result


def _extract_text_from_response(response: Any) -> str:
    text = getattr(response, "text", None)
    if text:
        return str(text)

    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        prompt_feedback = getattr(response, "prompt_feedback", None)
        if prompt_feedback:
            raise WritingGraderError("Writing grader response was blocked by Vertex AI")
        raise WritingGraderError("Writing grader returned no candidates")

    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) or []
        chunks: list[str] = []
        for part in parts:
            part_text = getattr(part, "text", None)
            if part_text:
                chunks.append(str(part_text))
        if chunks:
            return "\n".join(chunks)

        finish_reason = getattr(candidate, "finish_reason", None)
        if finish_reason and str(finish_reason) != "STOP":
            raise WritingGraderError(f"Writing grader stopped without usable text: {finish_reason}")

    raise WritingGraderError("Writing grader returned no text")


def grade_writing_submission(
    test: dict[str, Any],
    answers: dict[str, str],
    project: str | None = None,
    location: str = "us-central1",
    model: str = "gemini-2.5-pro",
    api_key: str | None = None,
) -> dict[str, Any]:
    from google import genai
    from google.genai import types

    try:
        if api_key:
            client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(api_version="v1alpha"),
            )
        elif project:
            client = genai.Client(
                vertexai=True,
                project=project,
                location=location,
                http_options=types.HttpOptions(api_version="v1"),
            )
        else:
            raise WritingGraderError("Writing grader is not configured")
    except Exception as exc:  # pragma: no cover - SDK/env failures
        raise WritingGraderError("Failed to initialize writing grader client") from exc
    prompt = f"""You are an IELTS Writing examiner assistant.
Grade the submission using IELTS writing criteria and return STRICT JSON.

Test JSON:
{json.dumps(test, ensure_ascii=False)}

Student answers JSON:
{json.dumps(answers, ensure_ascii=False)}

Rules:
- Use IELTS writing criteria: Task Response/Achievement, Coherence and Cohesion, Lexical Resource, Grammatical Range and Accuracy.
- Return separate criterion scores for Task 1 and Task 2.
- Return overall band where Task 2 has double weight.
- Provide concise, specific feedback.
- Provide sample answers for both tasks.
- Provide exactly 3 or 4 action points.

Return only JSON with this shape:
{{
  "overall_band": 0.0,
  "task_1": {{
    "band": 0.0,
    "criteria": {{
      "task_response": 0.0,
      "coherence_cohesion": 0.0,
      "lexical_resource": 0.0,
      "grammar_accuracy": 0.0
    }},
    "strengths": ["..."],
    "improvements": ["..."],
    "sample_answer": "..."
  }},
  "task_2": {{
    "band": 0.0,
    "criteria": {{
      "task_response": 0.0,
      "coherence_cohesion": 0.0,
      "lexical_resource": 0.0,
      "grammar_accuracy": 0.0
    }},
    "strengths": ["..."],
    "improvements": ["..."],
    "sample_answer": "..."
  }},
  "action_points": ["...", "...", "..."]
}}"""

    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=WritingGradeSchema,
                temperature=0,
            ),
        )
    except Exception as exc:  # pragma: no cover - network/provider failures
        raise WritingGraderError("Writing grader request failed") from exc

    raw = _strip_json_fence(_extract_text_from_response(response))
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise WritingGraderError("Writing grader returned invalid JSON") from exc

    action_points = list(payload.get("action_points", []))
    if len(action_points) < 3:
        action_points = action_points + [
            "Plan your essay before writing.",
            "Use varied sentence structures and linking words.",
            "Reserve time to proofread for grammar and spelling.",
        ]
    action_points = action_points[:4]

    task_1 = payload.get("task_1", {})
    task_2 = payload.get("task_2", {})
    result = {
        "overall_band": float(payload.get("overall_band", 0.0)),
        "task_1": {
            "band": float(task_1.get("band", 0.0)),
            "criteria": _normalize_band(task_1.get("criteria", {})),
            "strengths": list(task_1.get("strengths", [])),
            "improvements": list(task_1.get("improvements", [])),
            "sample_answer": str(task_1.get("sample_answer", "")),
        },
        "task_2": {
            "band": float(task_2.get("band", 0.0)),
            "criteria": _normalize_band(task_2.get("criteria", {})),
            "strengths": list(task_2.get("strengths", [])),
            "improvements": list(task_2.get("improvements", [])),
            "sample_answer": str(task_2.get("sample_answer", "")),
        },
        "action_points": action_points,
    }
    return result
