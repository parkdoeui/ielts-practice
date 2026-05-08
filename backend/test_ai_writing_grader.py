from types import SimpleNamespace

from google import genai

from ai_writing_grader import WritingGraderError, grade_writing_submission


def _sample_test() -> dict:
    return {
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
        "source_url": "https://example.com/test",
    }


def _sample_answers() -> dict[str, str]:
    return {"1": "Task 1 answer", "2": "Task 2 answer"}


def _sample_response_json() -> str:
    return """{
      "overall_band": 6.5,
      "task_1": {
        "band": 6.0,
        "criteria": {
          "task_response": 6.0,
          "coherence_cohesion": 6.0,
          "lexical_resource": 6.0,
          "grammar_accuracy": 6.0
        },
        "strengths": ["Good structure."],
        "improvements": ["Use more precise vocabulary."],
        "sample_answer": "Sample answer for task 1."
      },
      "task_2": {
        "band": 6.5,
        "criteria": {
          "task_response": 6.5,
          "coherence_cohesion": 6.5,
          "lexical_resource": 6.5,
          "grammar_accuracy": 6.5
        },
        "strengths": ["Clear argument."],
        "improvements": ["Develop examples in detail."],
        "sample_answer": "Sample answer for task 2."
      },
      "action_points": [
        "Plan ideas before writing.",
        "Use clearer topic sentences.",
        "Proofread grammar and punctuation."
      ]
    }"""


def test_grade_writing_submission_uses_gemini_api_for_api_key(monkeypatch) -> None:
    captured: dict = {}

    class FakeModels:
        def generate_content(self, **kwargs):
            captured["generate_content"] = kwargs
            return SimpleNamespace(text=_sample_response_json())

    class FakeClient:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.models = FakeModels()

    monkeypatch.setattr(genai, "Client", FakeClient)

    result = grade_writing_submission(
        test=_sample_test(),
        answers=_sample_answers(),
        api_key="vertex-api-key",
    )

    assert captured["client"]["api_key"] == "vertex-api-key"
    assert "vertexai" not in captured["client"]
    assert captured["client"]["http_options"].api_version == "v1alpha"
    assert captured["generate_content"]["config"].response_mime_type == "application/json"
    assert result["overall_band"] == 6.5


def test_grade_writing_submission_prefers_api_key_over_project(monkeypatch) -> None:
    captured: dict = {}

    class FakeModels:
        def generate_content(self, **kwargs):
            return SimpleNamespace(text=_sample_response_json())

    class FakeClient:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.models = FakeModels()

    monkeypatch.setattr(genai, "Client", FakeClient)

    grade_writing_submission(
        test=_sample_test(),
        answers=_sample_answers(),
        project="test-project",
        api_key="vertex-api-key",
    )

    assert captured["client"]["api_key"] == "vertex-api-key"
    assert "project" not in captured["client"]


def test_grade_writing_submission_reads_candidate_parts_when_text_missing(monkeypatch) -> None:
    class FakePart:
        def __init__(self, text: str):
            self.text = text

    class FakeContent:
        def __init__(self, parts):
            self.parts = parts

    class FakeCandidate:
        def __init__(self, text: str):
            self.content = FakeContent([FakePart(text)])
            self.finish_reason = "STOP"

    class FakeModels:
        def generate_content(self, **kwargs):
            return SimpleNamespace(text=None, candidates=[FakeCandidate(_sample_response_json())])

    class FakeClient:
        def __init__(self, **kwargs):
            self.models = FakeModels()

    monkeypatch.setattr(genai, "Client", FakeClient)

    result = grade_writing_submission(
        test=_sample_test(),
        answers=_sample_answers(),
        api_key="vertex-api-key",
    )

    assert result["task_1"]["sample_answer"] == "Sample answer for task 1."


def test_grade_writing_submission_raises_for_blocked_response(monkeypatch) -> None:
    class FakeModels:
        def generate_content(self, **kwargs):
            return SimpleNamespace(text=None, candidates=[], prompt_feedback={"block_reason": "SAFETY"})

    class FakeClient:
        def __init__(self, **kwargs):
            self.models = FakeModels()

    monkeypatch.setattr(genai, "Client", FakeClient)

    try:
        grade_writing_submission(
            test=_sample_test(),
            answers=_sample_answers(),
            api_key="vertex-api-key",
        )
    except WritingGraderError as exc:
        assert "blocked" in str(exc).lower()
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected WritingGraderError")
