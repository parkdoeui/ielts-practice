from __future__ import annotations
from pydantic import BaseModel, Field
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


class ListeningSegment(BaseModel):
    type: Literal["text", "blank"]
    text: Optional[str] = None
    question_id: Optional[int] = None


class ListeningListItem(BaseModel):
    segments: list[ListeningSegment] = Field(default_factory=list)
    children: list["ListeningListItem"] = Field(default_factory=list)


class ListeningTableCell(BaseModel):
    segments: list[ListeningSegment] = Field(default_factory=list)


class ListeningTableRow(BaseModel):
    cells: list[ListeningTableCell] = Field(default_factory=list)


class ListeningLayoutBlock(BaseModel):
    type: Literal["heading", "paragraph", "list", "table"]
    segments: list[ListeningSegment] = Field(default_factory=list)
    items: list[ListeningListItem] = Field(default_factory=list)
    rows: list[ListeningTableRow] = Field(default_factory=list)


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
    # Listening-only presentation structure. Questions remain the grading source of truth.
    layout: Optional[list[ListeningLayoutBlock]] = None
    selection_limit: Optional[int] = None


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
