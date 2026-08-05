from datetime import datetime, timezone
from math import floor
from typing import Any, Literal, Optional

from fastapi import FastAPI, Depends, HTTPException, Response, Cookie, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from config import settings
from database import engine, get_db
from models import Base, FullTestSessionRecord, TestSessionRecord, WritingSessionRecord
from ai_writing_grader import grade_writing_submission, WritingGraderError

Base.metadata.create_all(bind=engine)

app = FastAPI(title="IELTS Practice API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_frontend_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["Content-Type", "X-IELTS-Passcode"],
)


# ---------- Pydantic request / response models ----------

class LoginRequest(BaseModel):
    passcode: str


class AuthSessionResponse(BaseModel):
    authenticated: bool


class UserAnswerSchema(BaseModel):
    question_id: int
    user_answer: str
    is_correct: bool
    time_spent_ms: int
    question_type: Optional[str] = None
    self_corrected: Optional[bool] = None


class ScoreSchema(BaseModel):
    correct: int
    total: int
    band_estimate: float


class SessionCreate(BaseModel):
    id: str
    test_id: str
    started_at: str   # ISO 8601
    completed_at: str  # ISO 8601
    total_time_ms: int
    answers: list[UserAnswerSchema]
    score: ScoreSchema


class SessionResponse(BaseModel):
    id: str
    test_id: str
    started_at: str
    completed_at: str
    total_time_ms: int
    answers: list[dict[str, Any]]
    score: ScoreSchema

    model_config = {"from_attributes": True}


class QuestionTypeBreakdown(BaseModel):
    question_type: str
    correct: int
    total: int
    accuracy: float


class ProgressResponse(BaseModel):
    total_tests: int
    average_band: float
    best_band: float
    score_history: list[dict[str, Any]]
    per_type_accuracy: list[QuestionTypeBreakdown]


class WritingTaskInput(BaseModel):
    task_number: int
    task_type: str
    prompt: str = Field(min_length=10, max_length=5000)
    instructions: list[str] = Field(default_factory=list, max_length=12)
    min_words: int
    image_url: Optional[str] = Field(default=None, max_length=2048)
    table: Optional[list[list[str]]] = Field(default=None, max_length=40)

    @field_validator("table")
    @classmethod
    def validate_table(cls, value: Optional[list[list[str]]]) -> Optional[list[list[str]]]:
        if value is None:
            return None
        if len(value) > 40 or any(len(row) > 20 for row in value):
            raise ValueError("table is too large")
        return [[str(cell).strip()[:500] for cell in row] for row in value]

    @field_validator("instructions")
    @classmethod
    def validate_instructions(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item and item.strip()]
        return cleaned[:12]


class WritingTestInput(BaseModel):
    id: str = Field(pattern=r"^writing-test-\d+$")
    title: str = Field(min_length=1, max_length=300)
    test_type: str
    tasks: list[WritingTaskInput] = Field(min_length=2, max_length=2)
    time_limit_minutes: int = Field(ge=1, le=240)
    source_url: str = Field(max_length=2048)


class WritingSubmitRequest(BaseModel):
    id: str = Field(min_length=1, max_length=120)
    test: WritingTestInput
    started_at: str
    completed_at: str
    total_time_ms: int
    answers: dict[str, str] = Field(default_factory=dict)

    @field_validator("answers")
    @classmethod
    def validate_answers(cls, value: dict[str, str]) -> dict[str, str]:
        keys = set(value.keys())
        if keys != {"1", "2"}:
            raise ValueError("answers must contain exactly keys '1' and '2'")
        task_1 = value.get("1", "").strip()
        task_2 = value.get("2", "").strip()
        if len(task_1) > 12000 or len(task_2) > 20000:
            raise ValueError("answers exceed maximum allowed length")
        return {"1": task_1, "2": task_2}


class WritingTaskCriteria(BaseModel):
    task_response: float = 0.0
    coherence_cohesion: float = 0.0
    lexical_resource: float = 0.0
    grammar_accuracy: float = 0.0


class WritingCriterionEvidence(BaseModel):
    task_response: str = ""
    coherence_cohesion: str = ""
    lexical_resource: str = ""
    grammar_accuracy: str = ""


class WritingDetailedImprovementPoints(BaseModel):
    task_response: list[str] = Field(default_factory=list)
    coherence_cohesion: list[str] = Field(default_factory=list)
    lexical_resource: list[str] = Field(default_factory=list)
    grammar_accuracy: list[str] = Field(default_factory=list)


class WritingTaskFeedback(BaseModel):
    band: float = 0.0
    criteria: WritingTaskCriteria = Field(default_factory=WritingTaskCriteria)
    criterion_evidence: WritingCriterionEvidence = Field(default_factory=WritingCriterionEvidence)
    detailed_improvement_points: WritingDetailedImprovementPoints = Field(
        default_factory=WritingDetailedImprovementPoints
    )
    current_state: str = ""
    primary_goal: str = ""
    sample_answer: str = ""


class WritingGradingResponse(BaseModel):
    overall_band: float = 0.0
    task_1: WritingTaskFeedback = Field(default_factory=WritingTaskFeedback)
    task_2: WritingTaskFeedback = Field(default_factory=WritingTaskFeedback)
    action_points: list[str] = Field(default_factory=list)


class WritingSessionResponse(BaseModel):
    id: str
    test_id: str
    started_at: str
    completed_at: str
    total_time_ms: int
    answers: dict[str, str]
    grading: WritingGradingResponse


class FullTestSectionSchema(BaseModel):
    skill: Literal["listening", "reading", "writing", "speaking"]
    test_id: Optional[str] = Field(default=None, max_length=120)
    session_id: Optional[str] = Field(default=None, max_length=160)
    band: Optional[float] = Field(default=None, ge=0, le=9)


class FullTestSessionUpsert(BaseModel):
    id: str = Field(min_length=1, max_length=160)
    full_test_id: str = Field(pattern=r"^full-test-\d+$")
    mode: Literal["relaxed", "strict"]
    started_at: str
    sections: list[FullTestSectionSchema] = Field(min_length=1, max_length=4)

    @field_validator("sections")
    @classmethod
    def validate_unique_sections(
        cls,
        value: list[FullTestSectionSchema],
    ) -> list[FullTestSectionSchema]:
        skills = [section.skill for section in value]
        if len(skills) != len(set(skills)):
            raise ValueError("sections must contain each skill at most once")
        return value


class FullTestSessionResponse(BaseModel):
    id: str
    full_test_id: str
    mode: Literal["relaxed", "strict"]
    started_at: str
    completed_at: Optional[str] = None
    overall_band: Optional[float] = None
    sections: list[FullTestSectionSchema]


# ---------- Helper ----------

def verify_passcode(passcode: str) -> None:
    if passcode != settings.valid_passcode:
        raise HTTPException(status_code=403, detail="Invalid passcode")


def require_authenticated(
    passcode_cookie: Optional[str] = Cookie(default=None, alias="ielts_passcode"),
    passcode_header: Optional[str] = Header(default=None, alias="X-IELTS-Passcode"),
) -> None:
    if settings.valid_passcode not in {passcode_cookie, passcode_header}:
        raise HTTPException(status_code=403, detail="Authentication required")


def cookie_settings_for_request(request: Request) -> dict[str, Any]:
    origin = request.headers.get("origin", "")
    if origin.startswith("https://"):
        return {"samesite": "none", "secure": True}
    return {"samesite": settings.cookie_samesite, "secure": settings.cookie_secure}


def parse_iso_datetime(value: str) -> datetime:
    if value.endswith("Z"):
        value = f"{value[:-1]}+00:00"
    return datetime.fromisoformat(value)


def estimate_band(correct: int, total: int) -> float:
    score = round((correct / total) * 40) if total else 0
    if score >= 39:
        return 9.0
    if score >= 37:
        return 8.5
    if score >= 35:
        return 8.0
    if score >= 33:
        return 7.5
    if score >= 30:
        return 7.0
    if score >= 27:
        return 6.5
    if score >= 23:
        return 6.0
    if score >= 19:
        return 5.5
    if score >= 15:
        return 5.0
    if score >= 13:
        return 4.5
    return 4.0


def score_from_answers(answers: list[dict[str, Any]]) -> ScoreSchema:
    correct = sum(1 for answer in answers if answer.get("is_correct"))
    total = len(answers)
    return ScoreSchema(
        correct=correct,
        total=total,
        band_estimate=estimate_band(correct, total),
    )


def session_to_response(record: TestSessionRecord) -> SessionResponse:
    answers: list[dict[str, Any]] = record.answers_json  # type: ignore[assignment]
    score = score_from_answers(answers)
    return SessionResponse(
        id=record.id,
        test_id=record.test_id,
        started_at=record.started_at.isoformat(),
        completed_at=record.completed_at.isoformat(),
        total_time_ms=record.total_time_ms,
        answers=answers,
        score=score,
    )


def writing_session_to_response(record: WritingSessionRecord) -> WritingSessionResponse:
    answers = extract_writing_answers(record.answers_json)
    return WritingSessionResponse(
        id=record.id,
        test_id=record.test_id,
        started_at=record.started_at.isoformat(),
        completed_at=record.completed_at.isoformat(),
        total_time_ms=record.total_time_ms,
        answers=answers,
        grading=record.grading_json,  # type: ignore[arg-type]
    )


def round_overall_band(bands: list[float]) -> Optional[float]:
    valid_bands = [band for band in bands if band > 0]
    if not valid_bands:
        return None
    average = sum(valid_bands) / len(valid_bands)
    return floor((average * 2) + 0.5) / 2


def full_test_session_to_response(
    record: FullTestSessionRecord,
) -> FullTestSessionResponse:
    return FullTestSessionResponse(
        id=record.id,
        full_test_id=record.full_test_id,
        mode=record.mode,
        started_at=record.started_at.isoformat(),
        completed_at=record.completed_at.isoformat() if record.completed_at else None,
        overall_band=record.overall_band,
        sections=record.sections_json,
    )


def build_writing_answers_json(test: WritingTestInput, answers: dict[str, str]) -> dict[str, dict[str, str]]:
    prompts = {str(task.task_number): task.prompt for task in test.tasks}
    return {
        "task1": {
            "prompt": prompts.get("1", ""),
            "answer": answers.get("1", ""),
        },
        "task2": {
            "prompt": prompts.get("2", ""),
            "answer": answers.get("2", ""),
        },
    }


def extract_writing_answers(value: Any) -> dict[str, str]:
    if isinstance(value, dict) and ("task1" in value or "task2" in value):
        task1 = value.get("task1") if isinstance(value.get("task1"), dict) else {}
        task2 = value.get("task2") if isinstance(value.get("task2"), dict) else {}
        return {
            "1": str(task1.get("answer", "")).strip(),
            "2": str(task2.get("answer", "")).strip(),
        }

    if isinstance(value, dict):
        return {
            "1": str(value.get("1", "")).strip(),
            "2": str(value.get("2", "")).strip(),
        }

    return {"1": "", "2": ""}


def sanitize_test_for_grading(test: WritingTestInput) -> dict[str, Any]:
    return {
        "id": test.id,
        "title": test.title,
        "test_type": test.test_type,
        "time_limit_minutes": test.time_limit_minutes,
        "source_url": test.source_url,
        "tasks": [
            {
                "task_number": task.task_number,
                "task_type": task.task_type,
                "prompt": task.prompt,
                "instructions": task.instructions,
                "min_words": task.min_words,
                "image_url": task.image_url,
                "table": task.table,
            }
            for task in test.tasks
        ],
    }


# ---------- Routes ----------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/auth/login", status_code=204)
def login(payload: LoginRequest, request: Request, response: Response):
    verify_passcode(payload.passcode)
    response.set_cookie(
        key="ielts_passcode",
        value=settings.valid_passcode,
        httponly=True,
        **cookie_settings_for_request(request),
    )


@app.get("/api/auth/session", response_model=AuthSessionResponse)
def auth_session(
    passcode_cookie: Optional[str] = Cookie(default=None, alias="ielts_passcode"),
    passcode_header: Optional[str] = Header(default=None, alias="X-IELTS-Passcode"),
):
    return AuthSessionResponse(
        authenticated=(settings.valid_passcode in {passcode_cookie, passcode_header})
    )


@app.get("/api/session", response_model=AuthSessionResponse)
def legacy_auth_session(_: None = Depends(require_authenticated)):
    return AuthSessionResponse(authenticated=True)


@app.post("/api/sessions", response_model=SessionResponse, status_code=201)
def create_session(
    payload: SessionCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_authenticated),
):

    existing = db.get(TestSessionRecord, payload.id)
    if existing:
        raise HTTPException(status_code=409, detail="Session already exists")

    answers_json = [a.model_dump() for a in payload.answers]
    score = score_from_answers(answers_json)

    record = TestSessionRecord(
        id=payload.id,
        test_id=payload.test_id,
        passcode=settings.valid_passcode,
        started_at=parse_iso_datetime(payload.started_at),
        completed_at=parse_iso_datetime(payload.completed_at),
        total_time_ms=payload.total_time_ms,
        score_correct=score.correct,
        score_total=score.total,
        band_estimate=score.band_estimate,
        answers_json=answers_json,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return session_to_response(record)


@app.put("/api/sessions/{session_id}", response_model=SessionResponse)
def update_session(
    session_id: str,
    payload: SessionCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_authenticated),
):
    if payload.id != session_id:
        raise HTTPException(status_code=400, detail="Session ID mismatch")

    record = db.get(TestSessionRecord, session_id)
    if not record:
        raise HTTPException(status_code=404, detail="Session not found")
    if record.passcode != settings.valid_passcode:
        raise HTTPException(status_code=403, detail="Invalid passcode")

    answers_json = [a.model_dump() for a in payload.answers]
    score = score_from_answers(answers_json)

    record.test_id = payload.test_id
    record.started_at = parse_iso_datetime(payload.started_at)
    record.completed_at = parse_iso_datetime(payload.completed_at)
    record.total_time_ms = payload.total_time_ms
    record.score_correct = score.correct
    record.score_total = score.total
    record.band_estimate = score.band_estimate
    record.answers_json = answers_json
    db.commit()
    db.refresh(record)
    return session_to_response(record)


@app.get("/api/sessions", response_model=list[SessionResponse])
def list_sessions(
    db: Session = Depends(get_db),
    _: None = Depends(require_authenticated),
):
    records = (
        db.query(TestSessionRecord)
        .filter(TestSessionRecord.passcode == settings.valid_passcode)
        .order_by(TestSessionRecord.completed_at.desc())
        .all()
    )
    return [session_to_response(r) for r in records]


@app.get("/api/progress", response_model=ProgressResponse)
def get_progress(
    db: Session = Depends(get_db),
    _: None = Depends(require_authenticated),
):
    records = (
        db.query(TestSessionRecord)
        .filter(TestSessionRecord.passcode == settings.valid_passcode)
        .order_by(TestSessionRecord.completed_at.asc())
        .all()
    )

    if not records:
        return ProgressResponse(
            total_tests=0,
            average_band=0.0,
            best_band=0.0,
            score_history=[],
            per_type_accuracy=[],
        )

    bands = [r.band_estimate for r in records]
    average_band = sum(bands) / len(bands)
    best_band = max(bands)

    score_history = [
        {
            "date": r.completed_at.isoformat(),
            "test_id": r.test_id,
            "band": r.band_estimate,
            "correct": r.score_correct,
            "total": r.score_total,
        }
        for r in records
    ]

    # Per question-type accuracy — aggregate across all sessions
    type_stats: dict[str, dict[str, int]] = {}
    for r in records:
        answers: list[dict[str, Any]] = r.answers_json  # type: ignore[assignment]
        for a in answers:
            qtype = a.get("question_type", "unknown")
            if qtype not in type_stats:
                type_stats[qtype] = {"correct": 0, "total": 0}
            type_stats[qtype]["total"] += 1
            if a.get("is_correct"):
                type_stats[qtype]["correct"] += 1

    per_type: list[QuestionTypeBreakdown] = []
    for qtype, stats in type_stats.items():
        accuracy = stats["correct"] / stats["total"] if stats["total"] > 0 else 0.0
        per_type.append(
            QuestionTypeBreakdown(
                question_type=qtype,
                correct=stats["correct"],
                total=stats["total"],
                accuracy=round(accuracy * 100, 1),
            )
        )

    return ProgressResponse(
        total_tests=len(records),
        average_band=round(average_band, 2),
        best_band=best_band,
        score_history=score_history,
        per_type_accuracy=per_type,
    )


@app.put(
    "/api/full-test-sessions/{session_id}",
    response_model=FullTestSessionResponse,
)
def upsert_full_test_session(
    session_id: str,
    payload: FullTestSessionUpsert,
    db: Session = Depends(get_db),
    _: None = Depends(require_authenticated),
):
    if payload.id != session_id:
        raise HTTPException(status_code=400, detail="Full Test session ID mismatch")

    canonical = (
        db.query(FullTestSessionRecord)
        .filter(
            FullTestSessionRecord.passcode == settings.valid_passcode,
            FullTestSessionRecord.full_test_id == payload.full_test_id,
        )
        .first()
    )
    if canonical and canonical.id != session_id:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "This Full Test already has an attempt",
                "session_id": canonical.id,
            },
        )

    # A completed Full Test is immutable. Returning the existing record also makes
    # retries of the final sync idempotent without permitting a retake.
    if canonical and canonical.completed_at is not None:
        return full_test_session_to_response(canonical)

    section_values = [section.model_dump() for section in payload.sections]
    assigned_sections = [section for section in payload.sections if section.test_id is not None]
    is_completed = bool(assigned_sections) and all(
        section.session_id is not None for section in assigned_sections
    )
    overall_band = round_overall_band(
        [
            section.band
            for section in assigned_sections
            if section.session_id is not None and section.band is not None
        ]
    )

    record = canonical or FullTestSessionRecord(
        id=payload.id,
        full_test_id=payload.full_test_id,
        passcode=settings.valid_passcode,
    )
    record.mode = payload.mode
    record.started_at = parse_iso_datetime(payload.started_at)
    record.sections_json = section_values
    record.completed_at = datetime.now(timezone.utc) if is_completed else None
    record.overall_band = overall_band if is_completed else None

    if canonical is None:
        db.add(record)
    db.commit()
    db.refresh(record)
    return full_test_session_to_response(record)


@app.get("/api/full-test-sessions", response_model=list[FullTestSessionResponse])
def list_full_test_sessions(
    db: Session = Depends(get_db),
    _: None = Depends(require_authenticated),
):
    records = (
        db.query(FullTestSessionRecord)
        .filter(FullTestSessionRecord.passcode == settings.valid_passcode)
        .order_by(FullTestSessionRecord.started_at.desc())
        .all()
    )
    return [full_test_session_to_response(record) for record in records]


@app.get(
    "/api/full-test-sessions/{session_id}",
    response_model=FullTestSessionResponse,
)
def get_full_test_session(
    session_id: str,
    db: Session = Depends(get_db),
    _: None = Depends(require_authenticated),
):
    record = db.get(FullTestSessionRecord, session_id)
    if not record or record.passcode != settings.valid_passcode:
        raise HTTPException(status_code=404, detail="Full Test session not found")
    return full_test_session_to_response(record)


@app.post("/api/writing-sessions", response_model=WritingSessionResponse, status_code=201)
def create_writing_session(
    payload: WritingSubmitRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_authenticated),
):
    if not settings.writing_grader_api_key and not settings.effective_vertex_project:
        raise HTTPException(status_code=503, detail="Writing grader is not configured")

    existing = db.get(WritingSessionRecord, payload.id)
    if existing:
        raise HTTPException(status_code=409, detail="Writing session already exists")

    try:
        grading = grade_writing_submission(
            test=sanitize_test_for_grading(payload.test),
            answers=payload.answers,
            api_key=settings.writing_grader_api_key,
            credentials_json=settings.effective_vertex_credentials_json,
            project=settings.effective_vertex_project,
            location=settings.effective_vertex_location,
            model=settings.writing_grader_model,
        )
    except WritingGraderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(status_code=502, detail="Writing grader unavailable") from exc

    test_id = payload.test.id
    record = WritingSessionRecord(
        id=payload.id,
        test_id=test_id,
        passcode=settings.valid_passcode,
        started_at=parse_iso_datetime(payload.started_at),
        completed_at=parse_iso_datetime(payload.completed_at),
        total_time_ms=payload.total_time_ms,
        answers_json=build_writing_answers_json(payload.test, payload.answers),
        grading_json=grading,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return writing_session_to_response(record)


@app.get("/api/writing-sessions", response_model=list[WritingSessionResponse])
def list_writing_sessions(
    db: Session = Depends(get_db),
    _: None = Depends(require_authenticated),
):
    records = (
        db.query(WritingSessionRecord)
        .filter(WritingSessionRecord.passcode == settings.valid_passcode)
        .order_by(WritingSessionRecord.completed_at.desc())
        .all()
    )
    return [writing_session_to_response(r) for r in records]


@app.get("/api/writing-sessions/{session_id}", response_model=WritingSessionResponse)
def get_writing_session(
    session_id: str,
    db: Session = Depends(get_db),
    _: None = Depends(require_authenticated),
):
    record = db.get(WritingSessionRecord, session_id)
    if not record:
        raise HTTPException(status_code=404, detail="Writing session not found")
    if record.passcode != settings.valid_passcode:
        raise HTTPException(status_code=403, detail="Authentication required")
    return writing_session_to_response(record)
