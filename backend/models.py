from sqlalchemy import Boolean, Column, Integer, String, Float, JSON, DateTime, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class TestSessionRecord(Base):
    __tablename__ = "test_sessions"
    id = Column(String, primary_key=True)
    test_id = Column(String, nullable=False)
    passcode = Column(String, nullable=False, index=True)
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=False)
    total_time_ms = Column(Integer, nullable=False)
    score_correct = Column(Integer, nullable=False)
    score_total = Column(Integer, nullable=False)
    band_estimate = Column(Float, nullable=False)
    answers_json = Column(JSON, nullable=False)


class WritingSessionRecord(Base):
    __tablename__ = "writing_sessions"
    id = Column(String, primary_key=True)
    test_id = Column(String, nullable=False, index=True)
    passcode = Column(String, nullable=False, index=True)
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=False)
    total_time_ms = Column(Integer, nullable=False)
    answers_json = Column(JSON, nullable=False)
    grading_json = Column(JSON, nullable=False)


class PlanningSessionRecord(Base):
    __tablename__ = "planning_sessions"
    id = Column(String, primary_key=True)
    test_id = Column(String, nullable=False, index=True)
    task_number = Column(Integer, nullable=False, index=True)
    parent_session_id = Column(String, nullable=True)
    passcode = Column(String, nullable=False, index=True)
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=False)
    total_time_ms = Column(Integer, nullable=False)
    within_time_target = Column(Boolean, nullable=False)
    task_json = Column(JSON, nullable=False)
    plan_json = Column(JSON, nullable=False)
    feedback_json = Column(JSON, nullable=False)


class FullTestSessionRecord(Base):
    __tablename__ = "full_test_sessions"
    __table_args__ = (
        UniqueConstraint("passcode", "full_test_id", name="uq_full_test_session_owner_bundle"),
    )

    id = Column(String, primary_key=True)
    full_test_id = Column(String, nullable=False, index=True)
    passcode = Column(String, nullable=False, index=True)
    mode = Column(String, nullable=False)
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    overall_band = Column(Float, nullable=True)
    sections_json = Column(JSON, nullable=False)
