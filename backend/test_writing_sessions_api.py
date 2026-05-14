import os
from pathlib import Path
from fastapi.testclient import TestClient

import main
from main import app
from models import Base
from database import engine


def authed_client() -> TestClient:
    c = TestClient(app)
    res = c.post("/api/auth/login", json={"passcode": "test-passcode"})
    assert res.status_code == 204
    return c


def _payload() -> dict:
    return {
        "id": "writing-session-1",
        "test": {
            "id": "writing-test-1",
            "title": "IELTS Writing Test 1",
            "test_type": "academic",
            "tasks": [
                {
                    "task_number": 1,
                    "task_type": "academic-task-1",
                    "prompt": "Summarise the information.",
                    "instructions": ["Write at least 150 words."],
                    "min_words": 150,
                    "image_url": "https://example.com/task1.png",
                },
                {
                    "task_number": 2,
                    "task_type": "essay",
                    "prompt": "Discuss both views.",
                    "instructions": ["Write at least 250 words."],
                    "min_words": 250,
                },
            ],
            "time_limit_minutes": 60,
            "source_url": "https://practicepteonline.com/ielts-writing-test-1/",
        },
        "started_at": "2026-05-07T00:00:00Z",
        "completed_at": "2026-05-07T01:00:00Z",
        "total_time_ms": 1000,
        "answers": {
            "1": "Task 1 answer",
            "2": "Task 2 answer",
        },
    }


def _fake_grade() -> dict:
    return {
        "overall_band": 6.5,
        "task_1": {
            "band": 6.0,
            "criteria": {
                "task_response": 6.0,
                "coherence_cohesion": 6.0,
                "lexical_resource": 6.0,
                "grammar_accuracy": 6.0,
            },
            "criterion_evidence": {
                "task_response": "Addresses the task but the overview is too broad.",
                "coherence_cohesion": "Progression is clear, though linking is repetitive.",
                "lexical_resource": "Vocabulary is understandable but lacks precision.",
                "grammar_accuracy": "Sentence control is mixed with several article errors.",
            },
            "current_state": "A clear Band 6 report with basic control of the task.",
            "primary_goal": "Write a more specific overview before adding detail.",
        },
        "task_2": {
            "band": 6.5,
            "criteria": {
                "task_response": 6.5,
                "coherence_cohesion": 6.5,
                "lexical_resource": 6.5,
                "grammar_accuracy": 6.5,
            },
            "criterion_evidence": {
                "task_response": "Position is clear, but examples need deeper extension.",
                "coherence_cohesion": "Paragraphing is solid with minor overuse of simple transitions.",
                "lexical_resource": "Range is adequate, though collocations are occasionally awkward.",
                "grammar_accuracy": "Complex sentences are attempted with some punctuation slips.",
            },
            "current_state": "A reasonably coherent essay with a consistent position.",
            "primary_goal": "Support each main point with one concrete example or consequence.",
        },
        "action_points": [
            "Plan ideas before writing.",
            "Use clearer topic sentences.",
            "Proofread grammar and punctuation.",
        ],
    }


def setup_function() -> None:
    main.settings.vertex_api_key = "test-api-key"
    main.settings.vertex_project = None
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_writing_sessions_require_auth_cookie() -> None:
    unauth = TestClient(app)
    response = unauth.get("/api/writing-sessions")
    assert response.status_code == 403


def test_create_writing_session_persists_ai_grade(monkeypatch) -> None:
    monkeypatch.setattr(main, "grade_writing_submission", lambda **kwargs: _fake_grade())
    client = authed_client()
    response = client.post("/api/writing-sessions", json=_payload())
    assert response.status_code == 201
    body = response.json()
    assert body["grading"]["overall_band"] == 6.5
    assert body["grading"]["task_1"]["criterion_evidence"]["task_response"]
    assert body["grading"]["task_2"]["primary_goal"] == "Support each main point with one concrete example or consequence."


def test_get_writing_session_by_id() -> None:
    client = authed_client()
    main.grade_writing_submission = lambda **kwargs: _fake_grade()
    create = client.post("/api/writing-sessions", json=_payload())
    assert create.status_code == 201
    response = client.get("/api/writing-sessions/writing-session-1")
    assert response.status_code == 200
    assert response.json()["id"] == "writing-session-1"
