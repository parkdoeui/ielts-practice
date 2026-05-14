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
        "criterion_evidence": {
          "task_response": "Addresses the chart requirements but the overview is too generic.",
          "coherence_cohesion": "Paragraphing is clear, though some links feel mechanical.",
          "lexical_resource": "Meaning is clear but vocabulary stays fairly repetitive.",
          "grammar_accuracy": "Uses a mix of simple and complex clauses with noticeable article slips."
        },
        "detailed_improvement_points": {
          "task_response": [
            "Write one overview sentence that names the two most important trends before describing figures.",
            "Remove speculation about why the data changed unless the chart explicitly provides that reason."
          ],
          "coherence_cohesion": [
            "Group similar trends into the same paragraph instead of moving back and forth between categories.",
            "Replace inaccurate linking words with precise comparisons such as 'by contrast' or 'whereas'."
          ],
          "lexical_resource": [
            "Use accurate collocations such as 'number of households' instead of 'amount of households'.",
            "Replace malformed words such as 'dramatical' with the correct adjective or adverb form."
          ],
          "grammar_accuracy": [
            "Use 'between X and Y' rather than 'between X to Y'.",
            "Check time references carefully so the century and year range agree."
          ]
        },
        "current_state": "A controlled Band 6 response with clear structure but limited precision.",
        "primary_goal": "Write a sharper overview and extend each comparison with one specific detail."
      },
      "task_2": {
        "band": 6.5,
        "criteria": {
          "task_response": 6.5,
          "coherence_cohesion": 6.5,
          "lexical_resource": 6.5,
          "grammar_accuracy": 6.5
        },
        "criterion_evidence": {
          "task_response": "Position is clear, but supporting examples need more depth.",
          "coherence_cohesion": "Ideas progress logically across paragraphs with minor repetition in transitions.",
          "lexical_resource": "Shows some flexibility, though collocations are not always natural.",
          "grammar_accuracy": "Sentence range is adequate, but there are recurring agreement and punctuation errors."
        },
        "detailed_improvement_points": {
          "task_response": [
            "Develop each main idea with a concrete example or direct consequence.",
            "Keep the position consistent from the introduction through the conclusion."
          ],
          "coherence_cohesion": [
            "Use topic sentences that state the paragraph's role in the argument.",
            "Avoid repeating the same transition at the start of each paragraph."
          ],
          "lexical_resource": [
            "Revise awkward collocations so they sound natural in an academic essay.",
            "Use topic-specific vocabulary only when it precisely fits the point."
          ],
          "grammar_accuracy": [
            "Proofread subject-verb agreement in every complex sentence.",
            "Use commas to separate dependent clauses from main clauses."
          ]
        },
        "current_state": "A coherent mid-Band 6 essay with a clear position and partially developed support.",
        "primary_goal": "Develop each body paragraph with one concrete example or consequence."
      },
      "action_points": [
        "Plan ideas before writing.",
        "Use clearer topic sentences.",
        "Proofread grammar and punctuation."
      ]
    }"""


def _below_range_response_json() -> str:
    return """{
      "overall_band": 4.5,
      "task_1": {
        "band": 5.0,
        "criteria": {
          "task_response": 5.0,
          "coherence_cohesion": 5.0,
          "lexical_resource": 5.0,
          "grammar_accuracy": 5.0
        },
        "criterion_evidence": {
          "task_response": "Evidence.",
          "coherence_cohesion": "Evidence.",
          "lexical_resource": "Evidence.",
          "grammar_accuracy": "Evidence."
        },
        "detailed_improvement_points": {
          "task_response": ["Improve the overview."],
          "coherence_cohesion": ["Improve paragraph progression."],
          "lexical_resource": ["Improve collocation accuracy."],
          "grammar_accuracy": ["Improve verb forms."]
        },
        "current_state": "Current state.",
        "primary_goal": "Primary goal."
      },
      "task_2": {
        "band": 4.5,
        "criteria": {
          "task_response": 4.0,
          "coherence_cohesion": 5.0,
          "lexical_resource": 5.0,
          "grammar_accuracy": 5.0
        },
        "criterion_evidence": {
          "task_response": "Evidence.",
          "coherence_cohesion": "Evidence.",
          "lexical_resource": "Evidence.",
          "grammar_accuracy": "Evidence."
        },
        "detailed_improvement_points": {
          "task_response": ["Write at least 250 words."],
          "coherence_cohesion": ["Improve logical progression."],
          "lexical_resource": ["Avoid repetition."],
          "grammar_accuracy": ["Proofread verb forms."]
        },
        "current_state": "Current state.",
        "primary_goal": "Primary goal."
      },
      "action_points": [
        "Plan before writing.",
        "Develop each idea.",
        "Proofread grammar."
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
    assert result["task_1"]["criterion_evidence"]["task_response"]
    assert result["task_1"]["detailed_improvement_points"]["task_response"][0].startswith("Write one overview")
    assert result["task_2"]["primary_goal"]


def test_grade_writing_submission_clamps_scores_to_scorecard_floor(monkeypatch) -> None:
    class FakeModels:
        def generate_content(self, **kwargs):
            return SimpleNamespace(text=_below_range_response_json())

    class FakeClient:
        def __init__(self, **kwargs):
            self.models = FakeModels()

    monkeypatch.setattr(genai, "Client", FakeClient)

    result = grade_writing_submission(
        test=_sample_test(),
        answers=_sample_answers(),
        api_key="vertex-api-key",
    )

    assert result["overall_band"] == 5.0
    assert result["task_2"]["band"] == 5.0
    assert result["task_2"]["criteria"]["task_response"] == 5.0


def test_grade_writing_submission_prefers_project_over_api_key(monkeypatch) -> None:
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

    assert captured["client"]["vertexai"] is True
    assert captured["client"]["project"] == "test-project"
    assert "api_key" not in captured["client"]


def test_grade_writing_submission_uses_vertex_credentials_json(monkeypatch) -> None:
    captured: dict = {}
    fake_credentials = object()

    class FakeModels:
        def generate_content(self, **kwargs):
            return SimpleNamespace(text=_sample_response_json())

    class FakeClient:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.models = FakeModels()

    class FakeServiceAccountCredentials:
        @staticmethod
        def from_service_account_info(info, scopes):
            captured["service_account_info"] = info
            captured["scopes"] = scopes
            return fake_credentials

    monkeypatch.setattr(genai, "Client", FakeClient)

    import ai_writing_grader

    monkeypatch.setattr(
        ai_writing_grader,
        "service_account",
        SimpleNamespace(Credentials=FakeServiceAccountCredentials),
        raising=False,
    )

    # Patch the import target inside _load_vertex_credentials.
    import google.oauth2.service_account

    monkeypatch.setattr(
        google.oauth2.service_account,
        "Credentials",
        FakeServiceAccountCredentials,
    )

    grade_writing_submission(
        test=_sample_test(),
        answers=_sample_answers(),
        project="test-project",
        credentials_json='{"client_email":"svc@example.com","private_key":"secret"}',
    )

    assert captured["client"]["credentials"] is fake_credentials
    assert captured["service_account_info"]["client_email"] == "svc@example.com"
    assert captured["scopes"] == ["https://www.googleapis.com/auth/cloud-platform"]


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

    assert result["task_1"]["criterion_evidence"]["lexical_resource"]


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


def test_grade_writing_submission_includes_provider_request_error(monkeypatch) -> None:
    class FakeModels:
        def generate_content(self, **kwargs):
            raise RuntimeError("model not found")

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
        assert "model not found" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected WritingGraderError")
