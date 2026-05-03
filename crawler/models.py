from __future__ import annotations
from pydantic import BaseModel
from typing import Literal, Optional


class Passage(BaseModel):
    id: str
    title: str
    text: str
    paragraphs: list[str]


class SimpleQuestion(BaseModel):
    id: int
    statement: str
    answer: str


class QuestionGroup(BaseModel):
    id: str
    type: str  # "true-false-ng", "multiple-choice", "matching-information", "matching-headings",
               # "summary-completion", "sentence-completion", "diagram-labeling"
    passage_id: str
    instruction: str
    questions: list[SimpleQuestion]
    shared_text: Optional[str] = None       # summary/note passage shown once for the group
    word_list: Optional[list[str]] = None   # word bank (e.g., A-I) for summary completion
    image_url: Optional[str] = None         # diagram image for the group
    options: Optional[dict[str, str]] = None  # shared options (MC choices, paragraph letters, headings)


class ReadingTest(BaseModel):
    id: str
    title: str
    test_type: Literal["academic", "general"]
    passages: list[Passage]
    question_groups: list[QuestionGroup]
    time_limit_minutes: int
    source_url: str
