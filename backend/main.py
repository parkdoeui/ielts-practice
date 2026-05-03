from datetime import datetime
from typing import Any
import uuid

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

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

def session_to_response(record: TestSessionRecord) -> SessionResponse:
    answers: list[dict[str, Any]] = record.answers_json  # type: ignore[assignment]
    correct = sum(1 for a in answers if a.get("is_correct"))
    total = len(answers)
    return SessionResponse(
        id=record.id,
        test_id=record.test_id,
        passcode=record.passcode,
        started_at=record.started_at.isoformat(),
        completed_at=record.completed_at.isoformat(),
        total_time_ms=record.total_time_ms,
        answers=answers,
        score=ScoreSchema(
            correct=record.score_correct,
            total=record.score_total,
            band_estimate=record.band_estimate,
        ),
    )


# ---------- Routes ----------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/sessions", response_model=SessionResponse, status_code=201)
def create_session(payload: SessionCreate, db: Session = Depends(get_db)):
    # Upsert — if the client sends the same id twice, we overwrite
    existing = db.get(TestSessionRecord, payload.id)
    if existing:
        raise HTTPException(status_code=409, detail="Session already exists")

    record = TestSessionRecord(
        id=payload.id,
        test_id=payload.test_id,
        passcode=payload.passcode,
        started_at=datetime.fromisoformat(payload.started_at),
        completed_at=datetime.fromisoformat(payload.completed_at),
        total_time_ms=payload.total_time_ms,
        score_correct=payload.score.correct,
        score_total=payload.score.total,
        band_estimate=payload.score.band_estimate,
        answers_json=[a.model_dump() for a in payload.answers],
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return session_to_response(record)


@app.get("/api/sessions", response_model=list[SessionResponse])
def list_sessions(
    passcode: str = Query(..., description="User passcode"),
    db: Session = Depends(get_db),
):
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
