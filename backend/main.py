from datetime import datetime
from typing import Any, Optional

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import settings
from database import engine, get_db
from models import Base, TestSessionRecord

Base.metadata.create_all(bind=engine)

app = FastAPI(title="IELTS Practice API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Pydantic request / response models ----------

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
    passcode: str
    started_at: str   # ISO 8601
    completed_at: str  # ISO 8601
    total_time_ms: int
    answers: list[UserAnswerSchema]
    score: ScoreSchema


class SessionResponse(BaseModel):
    id: str
    test_id: str
    passcode: str
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


# ---------- Helper ----------

def verify_passcode(passcode: str) -> None:
    if passcode != settings.valid_passcode:
        raise HTTPException(status_code=403, detail="Invalid passcode")


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
        passcode=record.passcode,
        started_at=record.started_at.isoformat(),
        completed_at=record.completed_at.isoformat(),
        total_time_ms=record.total_time_ms,
        answers=answers,
        score=score,
    )


# ---------- Routes ----------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/sessions", response_model=SessionResponse, status_code=201)
def create_session(payload: SessionCreate, db: Session = Depends(get_db)):
    verify_passcode(payload.passcode)

    existing = db.get(TestSessionRecord, payload.id)
    if existing:
        raise HTTPException(status_code=409, detail="Session already exists")

    answers_json = [a.model_dump() for a in payload.answers]
    score = score_from_answers(answers_json)

    record = TestSessionRecord(
        id=payload.id,
        test_id=payload.test_id,
        passcode=payload.passcode,
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
):
    verify_passcode(payload.passcode)

    if payload.id != session_id:
        raise HTTPException(status_code=400, detail="Session ID mismatch")

    record = db.get(TestSessionRecord, session_id)
    if not record:
        raise HTTPException(status_code=404, detail="Session not found")
    if record.passcode != payload.passcode:
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
    passcode: str = Query(..., description="User passcode"),
    db: Session = Depends(get_db),
):
    verify_passcode(passcode)

    records = (
        db.query(TestSessionRecord)
        .filter(TestSessionRecord.passcode == passcode)
        .order_by(TestSessionRecord.completed_at.desc())
        .all()
    )
    return [session_to_response(r) for r in records]


@app.get("/api/progress", response_model=ProgressResponse)
def get_progress(
    passcode: str = Query(..., description="User passcode"),
    db: Session = Depends(get_db),
):
    verify_passcode(passcode)

    records = (
        db.query(TestSessionRecord)
        .filter(TestSessionRecord.passcode == passcode)
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
