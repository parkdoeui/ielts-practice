import os
from pathlib import Path

os.environ["VALID_PASSCODE"] = "test-passcode"
os.environ["DATABASE_URL"] = f"sqlite:///{Path(__file__).with_name('test_sessions_api.db')}"

from fastapi.testclient import TestClient

from main import app
from models import Base
from database import engine


client = TestClient(app)


def _session_payload() -> dict:
    return {
        "id": "session-1",
        "test_id": "test-1",
        "passcode": "test-passcode",
        "started_at": "2026-05-05T00:00:00Z",
        "completed_at": "2026-05-05T01:00:00Z",
        "total_time_ms": 1000,
        "answers": [
            {
                "question_id": 1,
                "user_answer": "a",
                "is_correct": True,
                "time_spent_ms": 0,
                "question_type": "summary-completion",
            },
            {
                "question_id": 2,
                "user_answer": "b",
                "is_correct": False,
                "time_spent_ms": 0,
                "question_type": "summary-completion",
            },
        ],
        "score": {
            "correct": 99,
            "total": 99,
            "band_estimate": 9.0,
        },
    }


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def teardown_module() -> None:
    db_path = Path(__file__).with_name("test_sessions_api.db")
    if db_path.exists():
        db_path.unlink()


def test_create_session_recomputes_score_from_answers() -> None:
    response = client.post("/api/sessions", json=_session_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["score"]["correct"] == 1
    assert body["score"]["total"] == 2
    assert body["score"]["band_estimate"] == 5.5


def test_update_session_persists_self_correction_and_recomputes_score() -> None:
    create_response = client.post("/api/sessions", json=_session_payload())
    assert create_response.status_code == 201

    updated = _session_payload()
    updated["answers"][1]["is_correct"] = True
    updated["answers"][1]["self_corrected"] = True
    updated["score"] = {
        "correct": 0,
        "total": 0,
        "band_estimate": 0.0,
    }

    update_response = client.put("/api/sessions/session-1", json=updated)

    assert update_response.status_code == 200
    update_body = update_response.json()
    assert update_body["score"]["correct"] == 2
    assert update_body["score"]["total"] == 2
    assert update_body["answers"][1]["self_corrected"] is True

    list_response = client.get("/api/sessions", params={"passcode": "test-passcode"})
    assert list_response.status_code == 200
    list_body = list_response.json()
    assert list_body[0]["score"]["correct"] == 2
    assert list_body[0]["answers"][1]["self_corrected"] is True


def test_update_session_rejects_mismatched_session_id() -> None:
    create_response = client.post("/api/sessions", json=_session_payload())
    assert create_response.status_code == 201

    updated = _session_payload()
    updated["id"] = "different-session"

    response = client.put("/api/sessions/session-1", json=updated)

    assert response.status_code == 400
