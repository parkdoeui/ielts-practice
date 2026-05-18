from __future__ import annotations

import json
import pathlib
import re
from typing import Any

from pydantic import BaseModel, Field


class WritingGraderError(Exception):
    pass


def _provider_error_message(exc: Exception) -> str:
    message = str(exc).strip()
    if not message:
        return exc.__class__.__name__
    return message[:500]


def _load_vertex_credentials(credentials_json: str | None) -> Any:
    if not credentials_json:
        return None

    from google.oauth2 import service_account

    try:
        info = json.loads(credentials_json)
    except json.JSONDecodeError as exc:
        raise WritingGraderError("VERTEX_CREDENTIALS_JSON is not valid JSON") from exc

    return service_account.Credentials.from_service_account_info(
        info,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )


class WritingCriteriaSchema(BaseModel):
    task_response: float = 0.0
    coherence_cohesion: float = 0.0
    lexical_resource: float = 0.0
    grammar_accuracy: float = 0.0


class WritingCriterionEvidenceSchema(BaseModel):
    task_response: str = ""
    coherence_cohesion: str = ""
    lexical_resource: str = ""
    grammar_accuracy: str = ""


class WritingDetailedImprovementPointsSchema(BaseModel):
    task_response: list[str] = Field(default_factory=list)
    coherence_cohesion: list[str] = Field(default_factory=list)
    lexical_resource: list[str] = Field(default_factory=list)
    grammar_accuracy: list[str] = Field(default_factory=list)


class WritingTaskGradeSchema(BaseModel):
    band: float = 0.0
    criteria: WritingCriteriaSchema = Field(default_factory=WritingCriteriaSchema)
    criterion_evidence: WritingCriterionEvidenceSchema = Field(
        default_factory=WritingCriterionEvidenceSchema
    )
    detailed_improvement_points: WritingDetailedImprovementPointsSchema = Field(
        default_factory=WritingDetailedImprovementPointsSchema
    )
    current_state: str = ""
    primary_goal: str = ""
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
        result[key] = _normalize_band_score(payload.get(key, 5.0))
    return result


def _normalize_band_score(value: Any, default: float = 5.0) -> float:
    try:
        raw = float(value)
    except (TypeError, ValueError):
        raw = default

    rounded = int(raw * 2 + 0.5) / 2
    return max(5.0, min(9.0, rounded))


def _normalize_criterion_evidence(payload: dict[str, Any]) -> dict[str, str]:
    keys = ["task_response", "coherence_cohesion", "lexical_resource", "grammar_accuracy"]
    result: dict[str, str] = {}
    for key in keys:
        result[key] = str(payload.get(key, "")).strip()
    return result


def _normalize_detailed_improvement_points(payload: dict[str, Any]) -> dict[str, list[str]]:
    keys = ["task_response", "coherence_cohesion", "lexical_resource", "grammar_accuracy"]
    result: dict[str, list[str]] = {}
    for key in keys:
        values = payload.get(key, [])
        if not isinstance(values, list):
            values = [values]
        result[key] = [str(value).strip() for value in values if str(value).strip()][:3]
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
    credentials_json: str | None = None,
) -> dict[str, Any]:
    from google import genai
    from google.genai import types

    try:
        if project:
            credentials = _load_vertex_credentials(credentials_json)
            client = genai.Client(
                vertexai=True,
                project=project,
                location=location,
                credentials=credentials,
                http_options=types.HttpOptions(api_version="v1"),
            )
        elif api_key:
            client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(api_version="v1alpha"),
            )
        else:
            raise WritingGraderError("Writing grader is not configured")
    except Exception as exc:  # pragma: no cover - SDK/env failures
        raise WritingGraderError(
            f"Failed to initialize writing grader client: {_provider_error_message(exc)}"
        ) from exc

    prompt_path = pathlib.Path(__file__).parent / "prompts" / "writing_grader.txt"
    try:
        prompt_template = prompt_path.read_text(encoding="utf-8")
    except Exception as exc:
        raise WritingGraderError(f"Failed to load prompt template: {exc}") from exc

    prompt = prompt_template.format(
        test_json=json.dumps(test, ensure_ascii=False),
        answers_json=json.dumps(answers, ensure_ascii=False),
    )

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
        raise WritingGraderError(
            f"Writing grader request failed: {_provider_error_message(exc)}"
        ) from exc

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
    task_1_band = _normalize_band_score(task_1.get("band", 5.0))
    task_2_band = _normalize_band_score(task_2.get("band", 5.0))
    result = {
        "overall_band": _normalize_band_score((task_1_band + task_2_band * 2) / 3),
        "task_1": {
            "band": task_1_band,
            "criteria": _normalize_band(task_1.get("criteria", {})),
            "criterion_evidence": _normalize_criterion_evidence(
                task_1.get("criterion_evidence", {})
            ),
            "detailed_improvement_points": _normalize_detailed_improvement_points(
                task_1.get("detailed_improvement_points", {})
            ),
            "current_state": str(task_1.get("current_state", "")).strip(),
            "primary_goal": str(task_1.get("primary_goal", "")).strip(),
            "sample_answer": str(task_1.get("sample_answer", "")).strip(),
        },
        "task_2": {
            "band": task_2_band,
            "criteria": _normalize_band(task_2.get("criteria", {})),
            "criterion_evidence": _normalize_criterion_evidence(
                task_2.get("criterion_evidence", {})
            ),
            "detailed_improvement_points": _normalize_detailed_improvement_points(
                task_2.get("detailed_improvement_points", {})
            ),
            "current_state": str(task_2.get("current_state", "")).strip(),
            "primary_goal": str(task_2.get("primary_goal", "")).strip(),
            "sample_answer": str(task_2.get("sample_answer", "")).strip(),
        },
        "action_points": action_points,
    }
    return result
