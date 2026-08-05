from __future__ import annotations

import pytest

from ai_planning_grader import PlanningGraderError, _build_prompt, fetch_allowed_task_image, normalize_planning_feedback


def _plan() -> dict:
    return {
        "kind": "task_2",
        "introduction": {"position": "I agree.", "roadmap": "Two reasons."},
        "body_1": {"main_idea": "One", "explanation": "Why", "example": "Example", "link_to_position": "Link"},
        "body_2": {"main_idea": "Two", "explanation": "Why", "example": "Example", "link_to_position": "Link"},
        "conclusion": {"restated_position": "I agree.", "synthesis": "Therefore."},
    }


def test_normalize_planning_feedback_calculates_average_and_preserves_outline() -> None:
    result = normalize_planning_feedback(
        {
            "planning_band": 1,
            "task_achievement": {"band": 7.1, "feedback": "Relevant."},
            "coherence_cohesion": {"band": 6.4, "feedback": "Logical."},
            "summary": "Good.",
            "relevant_ideas": ["One"],
            "missing_or_weak_ideas": ["Two"],
            "organization_feedback": "Clear.",
            "next_attempt_focus": "Link ideas.",
            "improved_plan": _plan(),
        },
        _plan(),
        2,
    )
    assert result["task_achievement"]["band"] == 7.0
    assert result["coherence_cohesion"]["band"] == 6.5
    assert result["planning_band"] == 7.0
    assert result["improved_plan"]["kind"] == "task_2"


def test_normalize_planning_feedback_falls_back_to_submitted_plan_for_wrong_kind() -> None:
    result = normalize_planning_feedback(
        {"task_achievement": {}, "coherence_cohesion": {}, "improved_plan": {"kind": "task_1"}},
        _plan(),
        2,
    )
    assert result["improved_plan"] == _plan()


def test_task_one_requires_four_note_improved_plan_and_prompt_names_type() -> None:
    submitted = {
        "kind": "task_1",
        "introduction": "A line graph of recycling.",
        "overview": "The rate rose overall.",
        "detail_1": "Early years.",
        "detail_2": "Later years.",
    }
    result = normalize_planning_feedback(
        {
            "task_achievement": {},
            "coherence_cohesion": {},
            "improved_plan": {"kind": "task_1", "overview": {"big_picture_1": "Legacy"}},
        },
        submitted,
        1,
    )
    assert result["improved_plan"] == submitted

    prompt = _build_prompt(
        {"task_number": 1, "question_type": "line-graph", "prompt": "A recycling graph."},
        submitted,
    )
    assert "question type is line-graph" in prompt
    assert "detail_1" in prompt


def test_task_visual_rejects_unapproved_hosts() -> None:
    with pytest.raises(PlanningGraderError):
        fetch_allowed_task_image("https://example.com/image.png")


def test_task_visual_rejects_non_https_urls() -> None:
    with pytest.raises(PlanningGraderError):
        fetch_allowed_task_image("http://practicepteonline.com/image.png")
