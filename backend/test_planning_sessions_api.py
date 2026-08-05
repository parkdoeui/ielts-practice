from __future__ import annotations

from fastapi.testclient import TestClient

import main
from database import engine
from main import app
from models import Base, PlanningSessionRecord


def authed_client() -> TestClient:
    client = TestClient(app)
    response = client.post("/api/auth/login", json={"passcode": "test-passcode"})
    assert response.status_code == 204
    return client


def _task(task_number: int = 2) -> dict:
    if task_number == 1:
        return {
            "task_number": 1,
            "task_type": "academic-task-1",
            "question_type": "line-graph",
            "prompt": "The chart shows changes in household recycling.",
            "instructions": ["Write at least 150 words."],
            "min_words": 150,
            "image_url": None,
            "table": [["Year", "Rate"], ["2000", "20%"]],
        }
    return {
        "task_number": 2,
        "task_type": "essay",
        "prompt": "Some people prefer to work from home. Discuss both views and give your opinion.",
        "instructions": ["Write at least 250 words."],
        "min_words": 250,
    }


def _plan(task_number: int = 2) -> dict:
    if task_number == 1:
        return {
            "kind": "task_1",
            "introduction": "Recycling rates over time.",
            "overview": "Rates rose overall and the final year was highest.",
            "detail_1": "Early years: the rate started at 20 percent.",
            "detail_2": "Later years: the rate reached 50 percent after a gradual rise.",
        }
    return {
        "kind": "task_2",
        "introduction": {"position": "I partly agree.", "roadmap": "Home work helps flexibility but can reduce collaboration."},
        "body_1": {"main_idea": "It saves commuting time.", "explanation": "Workers can use that time productively.", "example": "Parents can work near home.", "link_to_position": "This supports working from home."},
        "body_2": {"main_idea": "It can reduce teamwork.", "explanation": "Informal discussion is less frequent.", "example": "New staff may struggle to learn remotely.", "link_to_position": "Offices remain useful for collaboration."},
        "conclusion": {"restated_position": "Both arrangements have value.", "synthesis": "The best choice depends on the work."},
    }


def _payload(*, task_number: int = 2, session_id: str = "planning-1", parent: str | None = None) -> dict:
    return {
        "id": session_id,
        "test_id": "writing-test-1",
        "task": _task(task_number),
        "parent_session_id": parent,
        "started_at": "2026-08-04T10:00:00Z",
        "completed_at": "2026-08-04T10:05:01Z",
        "total_time_ms": 300001,
        "plan": _plan(task_number),
    }


def _fake_grade(**kwargs) -> dict:
    return {
        "planning_band": 99.0,
        "task_achievement": {"band": 7.0, "feedback": "Relevant coverage."},
        "coherence_cohesion": {"band": 6.5, "feedback": "Clear grouping."},
        "summary": "Good initial structure.",
        "relevant_ideas": ["The commuting point is relevant."],
        "missing_or_weak_ideas": ["Develop the collaboration limitation."],
        "organization_feedback": "The progression is easy to follow.",
        "next_attempt_focus": "Connect each example to the position.",
        "improved_plan": _plan(2),
    }


def setup_function() -> None:
    main.settings.vertex_api_key = "test-api-key"
    main.settings.vertex_project = None
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_planning_routes_require_authentication() -> None:
    client = TestClient(app)
    assert client.get("/api/planning-sessions").status_code == 403
    assert client.get("/api/planning-sessions/planning-1").status_code == 403


def test_create_planning_session_normalizes_band_and_persists(monkeypatch) -> None:
    monkeypatch.setattr(main, "grade_planning_submission", _fake_grade)
    client = authed_client()
    response = client.post("/api/planning-sessions", json=_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["feedback"]["planning_band"] == 7.0
    assert body["within_time_target"] is False
    assert body["plan"]["kind"] == "task_2"

    record = PlanningSessionRecord
    from database import SessionLocal
    db = SessionLocal()
    try:
        assert db.get(record, "planning-1") is not None
    finally:
        db.close()


def test_planning_list_filter_and_get(monkeypatch) -> None:
    monkeypatch.setattr(main, "grade_planning_submission", _fake_grade)
    client = authed_client()
    assert client.post("/api/planning-sessions", json=_payload()).status_code == 201
    task_one = _payload(task_number=1, session_id="planning-2")
    assert client.post("/api/planning-sessions", json=task_one).status_code == 201

    filtered = client.get("/api/planning-sessions?task_number=1")
    assert [item["id"] for item in filtered.json()] == ["planning-2"]
    assert client.get("/api/planning-sessions/planning-1").json()["task_number"] == 2


def test_revision_requires_same_task(monkeypatch) -> None:
    monkeypatch.setattr(main, "grade_planning_submission", _fake_grade)
    client = authed_client()
    assert client.post("/api/planning-sessions", json=_payload()).status_code == 201
    revision = _payload(task_number=1, session_id="planning-2", parent="planning-1")
    assert client.post("/api/planning-sessions", json=revision).status_code == 400


def test_plan_kind_must_match_task() -> None:
    client = authed_client()
    payload = _payload(task_number=2)
    payload["plan"] = _plan(1)
    assert client.post("/api/planning-sessions", json=payload).status_code == 422


def test_table_task_is_retained(monkeypatch) -> None:
    captured = {}

    def fake_grade(**kwargs):
        captured.update(kwargs)
        return _fake_grade()

    monkeypatch.setattr(main, "grade_planning_submission", fake_grade)
    client = authed_client()
    response = client.post("/api/planning-sessions", json=_payload(task_number=1, session_id="planning-3"))
    assert response.status_code == 201
    assert captured["task"]["table"] == [["Year", "Rate"], ["2000", "20%"]]
    assert captured["task"]["question_type"] == "line-graph"
