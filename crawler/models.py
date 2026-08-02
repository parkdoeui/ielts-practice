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
    options: Optional[dict[str, str]] = None  # per-question MC choices when not shared by the group


class QuestionGroup(BaseModel):
    id: str
    type: str  # "true-false-ng", "multiple-choice", "matching-information", "matching-headings",
               # "summary-completion", "sentence-completion", "diagram-labeling",
               # "classification", "matching-sentence-endings"
    passage_id: str
    instruction: str
    questions: list[SimpleQuestion]
    shared_text: Optional[str] = None       # summary/note passage shown once for the group
    word_list: Optional[list[str]] = None   # word bank (e.g., A-I) for summary completion
    image_url: Optional[str] = None         # diagram image for the group
    options: Optional[dict[str, str]] = None  # shared options (MC choices, paragraph letters, headings)


class ListeningPart(BaseModel):
    id: str
    number: int
    title: Optional[str] = None


class ListeningTest(BaseModel):
    id: str
    title: str
    audio_url: str
    parts: list[ListeningPart]
    # For listening groups, passage_id stores the owning ListeningPart id.
    question_groups: list[QuestionGroup]
    time_limit_minutes: int = 30
    source_url: str


class ReadingTest(BaseModel):
    id: str
    title: str
    test_type: Literal["academic", "general"]
    passages: list[Passage]
    question_groups: list[QuestionGroup]
    time_limit_minutes: int
    source_url: str


class WritingTask(BaseModel):
    task_number: Literal[1, 2]
    task_type: Literal["academic-task-1", "essay"]
    prompt: str
    instructions: list[str]
    min_words: int
    image_url: Optional[str] = None
    table: Optional[list[list[str]]] = None


class WritingTest(BaseModel):
    id: str
    title: str
    test_type: Literal["academic", "general"]
    tasks: list[WritingTask]
    time_limit_minutes: int
    source_url: str
