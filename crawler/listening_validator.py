from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import re

from models import ListeningTest, QuestionGroup


RESIDUAL_PREFIX_RE = re.compile(r"^(?:[•●○◦▪▫·]|[oO]\s|va(?:\s|$))", re.IGNORECASE)
RESIDUAL_TEXT_RE = re.compile(
    r"(?:\btidesbasic\b|\bskillsincluding\b|\bavailablefor\b|\batthe\b|"
    r"\binternal wails\b|\btoo tow\b)",
    re.IGNORECASE,
)


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def report(self) -> str:
        parts: list[str] = []
        if self.errors:
            parts.append("errors=" + "; ".join(self.errors))
        if self.warnings:
            parts.append("warnings=" + "; ".join(self.warnings))
        return " | ".join(parts) if parts else "ok"


def _group_option_keys(group: QuestionGroup) -> set[str]:
    keys = set(group.options or {})
    for question in group.questions:
        keys.update(question.options or {})
    return keys


def validate_listening_test(test: ListeningTest) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    if len(test.parts) != 4:
        errors.append(f"Expected exactly 4 listening parts, got {len(test.parts)}")
    part_numbers = [part.number for part in test.parts]
    if sorted(part_numbers) != [1, 2, 3, 4]:
        errors.append(f"Expected part numbers 1..4, got {part_numbers}")

    if not test.audio_url.startswith(("http://", "https://")):
        errors.append("audio_url must be an absolute http(s) URL")

    part_ids = {part.id for part in test.parts}
    for group in test.question_groups:
        if group.passage_id not in part_ids:
            errors.append(f"{group.id} references unknown part {group.passage_id}")

    questions = [question for group in test.question_groups for question in group.questions]
    ids = [question.id for question in questions]
    counts = Counter(ids)
    duplicates = sorted(number for number, count in counts.items() if count > 1)
    missing = sorted(set(range(1, 41)) - set(ids))
    unexpected = sorted(set(ids) - set(range(1, 41)))
    if duplicates:
        errors.append(f"Duplicate question ids: {duplicates}")
    if missing:
        errors.append(f"Missing question ids: {missing}")
    if unexpected:
        errors.append(f"Unexpected question ids: {unexpected}")

    for question in questions:
        if not question.answer.strip():
            errors.append(f"Question {question.id} has an empty answer")
        if len(question.answer.split()) > 3:
            warnings.append(f"Question {question.id} completion answer is longer than three words")
        if RESIDUAL_PREFIX_RE.match(question.statement):
            errors.append(f"Question {question.id} has a residual list/OCR prefix")
        if RESIDUAL_TEXT_RE.search(question.statement):
            errors.append(f"Question {question.id} has residual fused/OCR text")

    for group in test.question_groups:
        if len(group.questions) > 10:
            warnings.append(f"{group.id} spans more than 10 questions")

        if group.type not in {"multiple-choice", "matching"}:
            continue
        option_keys = _group_option_keys(group)
        if not option_keys:
            errors.append(f"{group.id} requires non-empty options")
            continue
        for question in group.questions:
            answer_letters = [letter for letter in question.answer.upper().replace("/", ",").split(",") if letter.strip()]
            unknown = sorted(set(letter.strip() for letter in answer_letters) - option_keys)
            if unknown:
                warnings.append(f"{group.id} question {question.id} answer letters not in options: {unknown}")

    return ValidationResult(valid=not errors, errors=errors, warnings=warnings)
