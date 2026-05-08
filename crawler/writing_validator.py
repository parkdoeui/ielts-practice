from __future__ import annotations

from dataclasses import dataclass, field

from models import WritingTest


def _prompt_has_instruction_leak(prompt: str) -> bool:
    lower = prompt.lower()
    markers = (
        "write at least",
        "you should spend",
        "give reasons for your answer",
        "include relevant examples",
        "sample answer",
        "comments are closed",
    )
    return any(marker in lower for marker in markers)


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


def validate_writing_test(test: WritingTest) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    if len(test.tasks) != 2:
        errors.append(f"Expected exactly 2 writing tasks, got {len(test.tasks)}")
        return ValidationResult(valid=False, errors=errors, warnings=warnings)

    task_1, task_2 = test.tasks
    if task_1.task_number != 1:
        errors.append("First task must be task_number=1")
    if task_2.task_number != 2:
        errors.append("Second task must be task_number=2")
    if task_1.task_type != "academic-task-1":
        errors.append("Task 1 must be academic-task-1")
    if task_2.task_type != "essay":
        errors.append("Task 2 must be essay")
    if not task_1.prompt.strip():
        errors.append("Task 1 prompt is empty")
    if not task_2.prompt.strip():
        errors.append("Task 2 prompt is empty")
    if _prompt_has_instruction_leak(task_1.prompt):
        errors.append("Task 1 prompt appears to include instruction/noise text")
    if _prompt_has_instruction_leak(task_2.prompt):
        errors.append("Task 2 prompt appears to include instruction/noise text")
    if task_1.min_words != 150:
        warnings.append(f"Task 1 min_words expected 150, got {task_1.min_words}")
    if task_2.min_words != 250:
        warnings.append(f"Task 2 min_words expected 250, got {task_2.min_words}")
    if not task_1.image_url:
        errors.append("Task 1 image_url is missing")
    if task_1.image_url and task_1.image_url.startswith("data:"):
        errors.append("Task 1 image_url is data URI")

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)
