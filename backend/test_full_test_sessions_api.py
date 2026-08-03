from fastapi.testclient import TestClient

from database import engine
from main import app, round_overall_band
from models import Base


def authed_client() -> TestClient:
    client = TestClient(app)
    response = client.post("/api/auth/login", json={"passcode": "test-passcode"})
    assert response.status_code == 204
    return client


def _payload(*, completed: bool = False, session_id: str = "mock-1") -> dict:
    return {
        "id": session_id,
        "full_test_id": "full-test-1",
        "mode": "strict",
        "started_at": "2026-08-03T10:00:00Z",
        # Client-computed aggregate values must be ignored by the API.
        "completed_at": "1999-01-01T00:00:00Z",
        "overall_band": 9.0,
        "sections": [
            {
                "skill": "listening",
                "test_id": "listening-test-202",
                "session_id": "listening-session",
                "band": 7.5,
            },
            {
                "skill": "reading",
                "test_id": "test-295",
                "session_id": "reading-session" if completed else None,
                "band": 6.5 if completed else None,
            },
            {
                "skill": "writing",
                "test_id": "writing-test-25",
                "session_id": "writing-session" if completed else None,
                "band": 7.0 if completed else None,
            },
            {
                "skill": "speaking",
                "test_id": None,
                "session_id": None,
                "band": None,
            },
        ],
    }


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_full_test_session_routes_require_authentication() -> None:
    client = TestClient(app)

    assert client.get("/api/full-test-sessions").status_code == 403
    assert client.get("/api/full-test-sessions/mock-1").status_code == 403
    assert client.put("/api/full-test-sessions/mock-1", json=_payload()).status_code == 403


def test_full_test_progress_can_be_created_listed_and_completed() -> None:
    client = authed_client()

    started = client.put("/api/full-test-sessions/mock-1", json=_payload())
    assert started.status_code == 200
    assert started.json()["completed_at"] is None
    assert started.json()["overall_band"] is None
    assert started.json()["sections"][0]["session_id"] == "listening-session"

    listed = client.get("/api/full-test-sessions")
    assert listed.status_code == 200
    assert [session["id"] for session in listed.json()] == ["mock-1"]

    completed = client.put(
        "/api/full-test-sessions/mock-1",
        json=_payload(completed=True),
    )
    assert completed.status_code == 200
    assert completed.json()["completed_at"] is not None
    assert completed.json()["overall_band"] == 7.0

    restored = client.get("/api/full-test-sessions/mock-1")
    assert restored.status_code == 200
    assert restored.json() == completed.json()


def test_completed_full_test_is_immutable_and_rejects_a_retake() -> None:
    client = authed_client()
    completed = client.put(
        "/api/full-test-sessions/mock-1",
        json=_payload(completed=True),
    )
    assert completed.status_code == 200

    regressed = client.put("/api/full-test-sessions/mock-1", json=_payload())
    assert regressed.status_code == 200
    assert regressed.json()["completed_at"] == completed.json()["completed_at"]
    assert regressed.json()["sections"] == completed.json()["sections"]

    duplicate = client.put(
        "/api/full-test-sessions/mock-2",
        json=_payload(session_id="mock-2"),
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["session_id"] == "mock-1"


def test_in_progress_full_test_also_rejects_a_second_attempt() -> None:
    client = authed_client()
    assert client.put("/api/full-test-sessions/mock-1", json=_payload()).status_code == 200

    duplicate = client.put(
        "/api/full-test-sessions/mock-2",
        json=_payload(session_id="mock-2"),
    )
    assert duplicate.status_code == 409


def test_full_test_session_validates_id_and_unique_skills() -> None:
    client = authed_client()

    mismatch = client.put("/api/full-test-sessions/other", json=_payload())
    assert mismatch.status_code == 400

    duplicate_skills = _payload()
    duplicate_skills["sections"][1]["skill"] = "listening"
    invalid = client.put("/api/full-test-sessions/mock-1", json=duplicate_skills)
    assert invalid.status_code == 422


def test_overall_band_uses_ielts_half_band_rounding() -> None:
    assert round_overall_band([6.0, 6.5]) == 6.5
    assert round_overall_band([6.5, 7.0]) == 7.0
    assert round_overall_band([]) is None
