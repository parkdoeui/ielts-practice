from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass
from math import floor
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from ai_writing_grader import _extract_text_from_response, _load_vertex_credentials, _strip_json_fence


class PlanningGraderError(Exception):
    pass


class PlanningCriterionSchema(BaseModel):
    band: float = 0.0
    feedback: str = ""


class PlanningFeedbackSchema(BaseModel):
    planning_band: float = 0.0
    task_achievement: PlanningCriterionSchema = Field(default_factory=PlanningCriterionSchema)
    coherence_cohesion: PlanningCriterionSchema = Field(default_factory=PlanningCriterionSchema)
    summary: str = ""
    relevant_ideas: list[str] = Field(default_factory=list)
    missing_or_weak_ideas: list[str] = Field(default_factory=list)
    organization_feedback: str = ""
    next_attempt_focus: str = ""
    improved_plan: dict[str, Any] = Field(default_factory=dict)


@dataclass
class ImagePayload:
    data: bytes
    mime_type: str


def fetch_allowed_task_image(url: str | None) -> ImagePayload | None:
    if not url:
        return None
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in {"practicepteonline.com", "www.practicepteonline.com"}:
        raise PlanningGraderError("Task visual must use an approved HTTPS source")

    import httpx

    try:
        response = httpx.get(
            url,
            headers={"User-Agent": "IELTS-Practice/1.0"},
            timeout=8.0,
            follow_redirects=False,
        )
        response.raise_for_status()
    except Exception as exc:
        raise PlanningGraderError(f"Task visual could not be loaded: {exc}") from exc

    mime_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
    if mime_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise PlanningGraderError("Task visual has an unsupported image type")
    data = response.content
    if len(data) > 5 * 1024 * 1024:
        raise PlanningGraderError("Task visual is too large")
    return ImagePayload(data=data, mime_type=mime_type)


def _normalize_band(value: Any) -> float:
    try:
        raw = float(value)
    except (TypeError, ValueError):
        raw = 0.0
    rounded = floor(max(0.0, min(9.0, raw)) * 2 + 0.5) / 2
    return rounded


def _normalize_list(value: Any, fallback: str = "") -> list[str]:
    if not isinstance(value, list):
        value = [value] if value else []
    values = [str(item).strip() for item in value if str(item).strip()]
    return values[:3] or ([fallback] if fallback else [])


def _normalize_plan(plan: Any, submitted_plan: dict[str, Any], task_number: int) -> dict[str, Any]:
    if not isinstance(plan, dict) or plan.get("kind") != f"task_{task_number}":
        return submitted_plan
    if task_number == 1:
        required_fields = ("introduction", "overview", "detail_1", "detail_2")
        if not all(isinstance(plan.get(field), str) for field in required_fields):
            return submitted_plan
    return plan


def _build_prompt(task: dict[str, Any], plan: dict[str, Any]) -> str:
    task_number = task.get("task_number")
    question_type = str(task.get("question_type") or "unclassified visual")
    task_guidance = (
        "For Task 1, check the introduction note, one selective overview, and two logically grouped "
        f"detail notes. The question type is {question_type}; judge the overview and grouping accordingly. "
        "Do not require a conclusion. The improved_plan must contain exactly kind, introduction, overview, "
        "detail_1, and detail_2, with the four plan fields returned as concise strings."
        if task_number == 1
        else "For Task 2, check the introduction position and roadmap, coverage of every question part, "
        "two developed body ideas, and a conclusion that restates rather than changes the position."
    )
    prompt_path = pathlib.Path(__file__).parent / "prompts" / "planning_grader.txt"
    try:
        template = prompt_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PlanningGraderError(f"Failed to load planning prompt: {exc}") from exc
    return template.format(
        task_guidance=task_guidance,
        task_json=json.dumps(task, ensure_ascii=False),
        plan_json=json.dumps(plan, ensure_ascii=False),
    )


def normalize_planning_feedback(payload: dict[str, Any], submitted_plan: dict[str, Any], task_number: int) -> dict[str, Any]:
    task_achievement = payload.get("task_achievement", {})
    coherence = payload.get("coherence_cohesion", {})
    ta_band = _normalize_band(task_achievement.get("band"))
    cc_band = _normalize_band(coherence.get("band"))
    overall = floor(((ta_band + cc_band) / 2) * 2 + 0.5) / 2
    return {
        "planning_band": overall,
        "task_achievement": {
            "band": ta_band,
            "feedback": str(task_achievement.get("feedback", "")).strip(),
        },
        "coherence_cohesion": {
            "band": cc_band,
            "feedback": str(coherence.get("feedback", "")).strip(),
        },
        "summary": str(payload.get("summary", "")).strip(),
        "relevant_ideas": _normalize_list(payload.get("relevant_ideas")),
        "missing_or_weak_ideas": _normalize_list(payload.get("missing_or_weak_ideas")),
        "organization_feedback": str(payload.get("organization_feedback", "")).strip(),
        "next_attempt_focus": str(payload.get("next_attempt_focus", "")).strip(),
        "improved_plan": _normalize_plan(payload.get("improved_plan"), submitted_plan, task_number),
    }


def _parse_feedback(raw: str, submitted_plan: dict[str, Any], task_number: int) -> dict[str, Any]:
    try:
        payload = json.loads(_strip_json_fence(raw))
    except json.JSONDecodeError as exc:
        raise PlanningGraderError("Planning grader returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise PlanningGraderError("Planning grader returned a non-object JSON response")
    return normalize_planning_feedback(payload, submitted_plan, task_number)


def grade_planning_submission(
    *,
    task: dict[str, Any],
    plan: dict[str, Any],
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
            client = genai.Client(
                vertexai=True,
                project=project,
                location=location,
                credentials=_load_vertex_credentials(credentials_json),
                http_options=types.HttpOptions(api_version="v1"),
            )
        elif api_key:
            client = genai.Client(api_key=api_key, http_options=types.HttpOptions(api_version="v1alpha"))
        else:
            raise PlanningGraderError("Planning grader is not configured")
    except PlanningGraderError:
        raise
    except Exception as exc:
        raise PlanningGraderError(f"Failed to initialize planning grader: {exc}") from exc

    contents: list[Any] = [types.Part.from_text(text=_build_prompt(task, plan))]
    if task.get("task_number") == 1 and task.get("image_url"):
        image = fetch_allowed_task_image(task["image_url"])
        if image:
            contents.append(types.Part.from_bytes(data=image.data, mime_type=image.mime_type))
    try:
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=PlanningFeedbackSchema,
                temperature=0,
            ),
        )
    except PlanningGraderError:
        raise
    except Exception as exc:
        raise PlanningGraderError(f"Planning grader request failed: {exc}") from exc
    return _parse_feedback(_extract_text_from_response(response), plan, int(task["task_number"]))
