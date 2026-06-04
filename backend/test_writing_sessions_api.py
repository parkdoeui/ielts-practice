import copy

from fastapi.testclient import TestClient

import main
from main import app
from models import Base, WritingSessionRecord
from database import SessionLocal, engine


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
            "detailed_improvement_points": {
                "task_response": [
                    "Write a specific overview that names the biggest trend before describing details.",
                    "Keep unsupported explanations out of Task 1 reports.",
                ],
                "coherence_cohesion": [
                    "Group related figures together before moving to contrasts.",
                    "Use precise comparison links instead of repeating basic sequence markers.",
                ],
                "lexical_resource": [
                    "Use accurate chart collocations such as 'number of households'.",
                    "Check word forms before using less common vocabulary.",
                ],
                "grammar_accuracy": [
                    "Review preposition patterns such as 'between X and Y'.",
                    "Proofread article and plural choices in data descriptions.",
                ],
            },
            "current_state": "A clear Band 6 report with basic control of the task.",
            "primary_goal": "Write a more specific overview before adding detail.",
            "sample_answer": "The map comparison shows how access to the city hospital changed from 2007 to 2010. Overall, the area became more organised and convenient because traffic circulation was improved and separate facilities were added for different users.\n\nIn 2007, Hospital Road connected City Road and Ring Road through two ordinary junctions. There was also one shared car park used by both staff and visitors.\n\nBy 2010, two roundabouts had replaced the previous junctions, which likely made movement along the road easier. In addition, a bus station was added to the west of the hospital, with bus stops on either side of Hospital Road. Parking was also reorganised: the former shared car park was replaced by a public car park, and a separate staff car park was built near Ring Road.\n\nOverall, the main changes involved better road management, improved public transport access, and more clearly divided parking areas.",
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
            "detailed_improvement_points": {
                "task_response": [
                    "Develop each body paragraph with one concrete example.",
                    "Make sure every paragraph directly supports the same position.",
                ],
                "coherence_cohesion": [
                    "Use clearer topic sentences to signal each paragraph's purpose.",
                    "Replace repeated transitions with logical connectors.",
                ],
                "lexical_resource": [
                    "Revise awkward collocations in argument sentences.",
                    "Use topic-specific vocabulary only where meaning stays precise.",
                ],
                "grammar_accuracy": [
                    "Check punctuation around dependent clauses.",
                    "Proofread verb forms in complex sentences.",
                ],
            },
            "current_state": "A reasonably coherent essay with a consistent position.",
            "primary_goal": "Support each main point with one concrete example or consequence.",
            "sample_answer": "Living in a country where people must use a foreign language can create both practical and social problems. I agree with this statement because communication difficulties affect daily tasks and can also make people feel isolated.\n\nFirst, practical problems are common when someone cannot use the local language well. It may be hard to speak to doctors, understand official documents, or solve problems at work and school. Even simple situations such as renting a flat or opening a bank account can become stressful if a person cannot explain what they need clearly.\n\nSecond, social problems can be just as serious. People who lack confidence in the local language may avoid conversations and struggle to build friendships. As a result, they may feel lonely or remain disconnected from the wider community. This can also reduce their confidence and make adaptation slower.\n\nHowever, these issues can become less severe over time as language skills improve. With enough practice and support, many people are able to integrate successfully.\n\nIn conclusion, I believe that living in a foreign-language environment can cause major practical and social difficulties, especially at first, although these challenges can gradually be overcome.",
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
    assert body["grading"]["task_1"]["detailed_improvement_points"]["task_response"][0].startswith("Write a specific")
    assert body["grading"]["task_2"]["primary_goal"] == "Support each main point with one concrete example or consequence."
    assert body["grading"]["task_1"]["sample_answer"].startswith("The map comparison shows")
    assert body["answers"] == {"1": "Task 1 answer", "2": "Task 2 answer"}

    db = SessionLocal()
    try:
        record = db.get(WritingSessionRecord, "writing-session-1")
        assert record is not None
        assert record.answers_json == {
            "task1": {
                "prompt": "Summarise the information.",
                "answer": "Task 1 answer",
            },
            "task2": {
                "prompt": "Discuss both views.",
                "answer": "Task 2 answer",
            },
        }
    finally:
        db.close()


def test_get_writing_session_by_id() -> None:
    client = authed_client()
    main.grade_writing_submission = lambda **kwargs: _fake_grade()
    create = client.post("/api/writing-sessions", json=_payload())
    assert create.status_code == 201
    response = client.get("/api/writing-sessions/writing-session-1")
    assert response.status_code == 200
    assert response.json()["id"] == "writing-session-1"
    assert response.json()["answers"] == {"1": "Task 1 answer", "2": "Task 2 answer"}


def test_create_writing_session_allows_retake_same_test_id(monkeypatch) -> None:
    monkeypatch.setattr(main, "grade_writing_submission", lambda **kwargs: _fake_grade())
    client = authed_client()
    first = _payload()
    second = copy.deepcopy(first)
    second["id"] = "writing-session-2"

    first_response = client.post("/api/writing-sessions", json=first)
    second_response = client.post("/api/writing-sessions", json=second)

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    list_response = client.get("/api/writing-sessions")
    assert list_response.status_code == 200
    session_ids = {item["id"] for item in list_response.json()}
    assert {"writing-session-1", "writing-session-2"} <= session_ids


def test_get_legacy_writing_session_answers_shape() -> None:
    db = SessionLocal()
    try:
        db.add(
            WritingSessionRecord(
                id="legacy-writing-session",
                test_id="writing-test-1",
                passcode="test-passcode",
                started_at=main.parse_iso_datetime("2026-05-07T00:00:00Z"),
                completed_at=main.parse_iso_datetime("2026-05-07T01:00:00Z"),
                total_time_ms=1000,
                answers_json={"1": "Legacy task 1", "2": "Legacy task 2"},
                grading_json=_fake_grade(),
            )
        )
        db.commit()
    finally:
        db.close()

    client = authed_client()
    response = client.get("/api/writing-sessions/legacy-writing-session")
    assert response.status_code == 200
    assert response.json()["answers"] == {"1": "Legacy task 1", "2": "Legacy task 2"}
