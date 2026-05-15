import json
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
    return json.dumps({
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
                "task_response": "Addresses the chart requirements but the overview is too generic.",
                "coherence_cohesion": "Paragraphing is clear, though some links feel mechanical.",
                "lexical_resource": "Meaning is clear but vocabulary stays fairly repetitive.",
                "grammar_accuracy": "Uses a mix of simple and complex clauses with noticeable article slips.",
            },
            "detailed_improvement_points": {
                "task_response": [
                    "Write one overview sentence that names the two most important trends before describing figures.",
                    "Remove speculation about why the data changed unless the chart explicitly provides that reason.",
                ],
                "coherence_cohesion": [
                    "Group similar trends into the same paragraph instead of moving back and forth between categories.",
                    "Replace inaccurate linking words with precise comparisons such as 'by contrast' or 'whereas'.",
                ],
                "lexical_resource": [
                    "Use accurate collocations such as 'number of households' instead of 'amount of households'.",
                    "Replace malformed words such as 'dramatical' with the correct adjective or adverb form.",
                ],
                "grammar_accuracy": [
                    "Use 'between X and Y' rather than 'between X to Y'.",
                    "Check time references carefully so the century and year range agree.",
                ],
            },
            "current_state": "A controlled Band 6 response with clear structure but limited precision.",
            "primary_goal": "Write a sharper overview and extend each comparison with one specific detail.",
            "sample_answer": "The maps illustrate how access to a city hospital changed between 2007 and 2010. Overall, the hospital became easier to reach because the road system was reorganised and public transport facilities were added. In particular, two roundabouts replaced the former junctions, while separate parking areas for staff and the public were introduced.\n\nIn 2007, Hospital Road was connected directly to both City Road and Ring Road by simple crossroads. There was also a single car park for both staff and visitors on the eastern side of the hospital.\n\nBy 2010, this layout had been improved considerably. Two roundabouts had been constructed, one at the intersection with City Road and the other at the junction with Ring Road, which helped traffic flow more smoothly. In addition, bus stops were built on both sides of Hospital Road and linked by a bus station to the west of the hospital. Another notable change was that the original shared car park was replaced by a larger public car park, while a smaller staff car park was added on the opposite side near Ring Road.",
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
                "task_response": "Position is clear, but supporting examples need more depth.",
                "coherence_cohesion": "Ideas progress logically across paragraphs with minor repetition in transitions.",
                "lexical_resource": "Shows some flexibility, though collocations are not always natural.",
                "grammar_accuracy": "Sentence range is adequate, but there are recurring agreement and punctuation errors.",
            },
            "detailed_improvement_points": {
                "task_response": [
                    "Develop each main idea with a concrete example or direct consequence.",
                    "Keep the position consistent from the introduction through the conclusion.",
                ],
                "coherence_cohesion": [
                    "Use topic sentences that state the paragraph's role in the argument.",
                    "Avoid repeating the same transition at the start of each paragraph.",
                ],
                "lexical_resource": [
                    "Revise awkward collocations so they sound natural in an academic essay.",
                    "Use topic-specific vocabulary only when it precisely fits the point.",
                ],
                "grammar_accuracy": [
                    "Proofread subject-verb agreement in every complex sentence.",
                    "Use commas to separate dependent clauses from main clauses.",
                ],
            },
            "current_state": "A coherent mid-Band 6 essay with a clear position and partially developed support.",
            "primary_goal": "Develop each body paragraph with one concrete example or consequence.",
            "sample_answer": "Living in a foreign country often requires people to use a language that is not their mother tongue, and this can create both social and practical difficulties. I largely agree with this view because language barriers can make daily life inconvenient and can also prevent people from forming close relationships.\n\nFrom a practical perspective, people who cannot communicate confidently in the local language may struggle with essential tasks. For example, they may find it difficult to visit a doctor, understand legal documents, or deal with banking and transport systems. Even simple activities such as shopping or asking for directions can become stressful when someone is unable to express a problem clearly. As a result, daily life may take more time and effort than it does for native speakers.\n\nLanguage barriers can also lead to social isolation. If people cannot join conversations naturally, they may avoid community events or limit themselves to a small group from the same background. This can slow down integration and create a sense of loneliness. In workplaces or classrooms, misunderstandings may also occur, which can affect cooperation and confidence.\n\nHowever, these problems are not always permanent. With time, practice, and support from the local community, many people improve their language ability and adapt successfully. Although the early stages can be difficult, the experience may eventually help them become more independent and culturally aware.\n\nIn conclusion, speaking a foreign language in another country can cause serious social and practical problems, especially at the beginning. Nevertheless, these challenges can gradually be reduced if people are given enough opportunities to learn and participate in society.",
        },
        "action_points": [
            "Plan ideas before writing.",
            "Use clearer topic sentences.",
            "Proofread grammar and punctuation.",
        ],
    })


def _below_range_response_json() -> str:
    return json.dumps({
        "overall_band": 4.5,
        "task_1": {
            "band": 5.0,
            "criteria": {
                "task_response": 5.0,
                "coherence_cohesion": 5.0,
                "lexical_resource": 5.0,
                "grammar_accuracy": 5.0,
            },
            "criterion_evidence": {
                "task_response": "Evidence.",
                "coherence_cohesion": "Evidence.",
                "lexical_resource": "Evidence.",
                "grammar_accuracy": "Evidence.",
            },
            "detailed_improvement_points": {
                "task_response": ["Improve the overview."],
                "coherence_cohesion": ["Improve paragraph progression."],
                "lexical_resource": ["Improve collocation accuracy."],
                "grammar_accuracy": ["Improve verb forms."],
            },
            "current_state": "Current state.",
            "primary_goal": "Primary goal.",
            "sample_answer": "The chart shows a general change over the period, although some figures remained relatively stable. Overall, the most noticeable feature is that the main category increased, whereas the others changed more moderately. Looking first at the initial year, the figures were lower in several areas. By the end of the period, however, the leading category had risen and the gap between the groups became clearer.",
        },
        "task_2": {
            "band": 4.5,
            "criteria": {
                "task_response": 4.0,
                "coherence_cohesion": 5.0,
                "lexical_resource": 5.0,
                "grammar_accuracy": 5.0,
            },
            "criterion_evidence": {
                "task_response": "Evidence.",
                "coherence_cohesion": "Evidence.",
                "lexical_resource": "Evidence.",
                "grammar_accuracy": "Evidence.",
            },
            "detailed_improvement_points": {
                "task_response": ["Write at least 250 words."],
                "coherence_cohesion": ["Improve logical progression."],
                "lexical_resource": ["Avoid repetition."],
                "grammar_accuracy": ["Proofread verb forms."],
            },
            "current_state": "Current state.",
            "primary_goal": "Primary goal.",
            "sample_answer": "Some people believe this issue should be handled in one way, while others support an alternative view. In my opinion, the better approach depends on the situation, but I generally agree with the first view because it brings more long-term benefits.\n\nOne reason is that it can improve people's lives in a practical way. When the right support is provided, individuals are more likely to make progress and avoid future problems. For example, better guidance or planning can help people make more effective decisions in education and work.\n\nOn the other hand, the opposite view also has some advantages, especially in cases where people need more freedom or flexibility. Even so, without a clear structure, the results may be less reliable.\n\nIn conclusion, both sides have merit, but I believe the first position is stronger because it is more likely to produce stable and positive outcomes.",
        },
        "action_points": [
            "Plan before writing.",
            "Develop each idea.",
            "Proofread grammar.",
        ],
    })


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
    assert "aiming for roughly one IELTS band higher than the awarded band" in captured["generate_content"]["contents"]
    assert "constructive, hopeful, and encouraging" in captured["generate_content"]["contents"]
    assert result["overall_band"] == 6.5
    assert result["task_1"]["criterion_evidence"]["task_response"]
    assert result["task_1"]["detailed_improvement_points"]["task_response"][0].startswith("Write one overview")
    assert result["task_2"]["primary_goal"]
    assert result["task_1"]["sample_answer"].startswith("The maps illustrate")
    assert result["task_2"]["sample_answer"].startswith("Living in a foreign country")


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
    assert result["task_1"]["sample_answer"]


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
    import google.oauth2.service_account

    monkeypatch.setattr(
        ai_writing_grader,
        "service_account",
        SimpleNamespace(Credentials=FakeServiceAccountCredentials),
        raising=False,
    )
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
    assert result["task_2"]["sample_answer"]


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
