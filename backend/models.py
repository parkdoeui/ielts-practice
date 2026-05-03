from sqlalchemy import Column, Integer, String, Float, JSON, DateTime
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
