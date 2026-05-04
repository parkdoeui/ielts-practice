"""
Hard validation rules for parsed IELTS reading test output.

Call validate_reading_test() after parsing to catch structural errors
before saving JSON. A ValidationResult with valid=False should trigger
a fail-fast crawl abort.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from models import ReadingTest


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def report(self) -> str:
        lines = []
        for e in self.errors:
            lines.append(f"  ✗ {e}")
        for w in self.warnings:
            lines.append(f"  ⚠ {w}")
        return "\n".join(lines)


def validate_reading_test(test: ReadingTest) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    passage_ids = {p.id for p in test.passages}

    # --- Hard errors ---

    if len(test.passages) != 3:
        errors.append(f"Expected 3 passages, got {len(test.passages)}")

    all_qids = [q.id for g in test.question_groups for q in g.questions]

    if len(all_qids) != 40:
        errors.append(f"Expected 40 questions, got {len(all_qids)}")

    expected_ids = set(range(1, 41))
    actual_ids = set(all_qids)
    missing = sorted(expected_ids - actual_ids)
    extra = sorted(actual_ids - expected_ids)
    if missing:
        errors.append(f"Missing question IDs: {missing}")
    if extra:
        errors.append(f"Extra question IDs: {extra}")

    if len(all_qids) != len(set(all_qids)):
        from collections import Counter
        dupes = [qid for qid, count in Counter(all_qids).items() if count > 1]
        errors.append(f"Duplicate question IDs: {sorted(dupes)}")

    unknown_answers = [q.id for g in test.question_groups for q in g.questions if q.answer == "UNKNOWN"]
    if unknown_answers:
        errors.append(f"UNKNOWN answers for question IDs: {sorted(unknown_answers)}")

    for g in test.question_groups:
        if g.passage_id not in passage_ids:
            errors.append(f"Group {g.id} references non-existent passage_id '{g.passage_id}'")

    for g in test.question_groups:
        if g.shared_text and g.shared_text.lower().startswith("show answers"):
            errors.append(f"Group {g.id}: shared_text starts with 'Show Answers' (answer section leaked)")

    for g in test.question_groups:
        if g.type == "diagram-labeling":
            url = g.image_url or ""
            if not re.match(r"^https?://", url):
                errors.append(f"Group {g.id}: diagram-labeling group has no valid image_url (got: '{url[:40]}')")

    for p in test.passages:
        if len(p.text.strip()) < 100:
            errors.append(f"Passage '{p.id}' has trivially short text ({len(p.text)} chars) — likely parsing failure")

    # Check for overlapping question groups
    seen: dict[int, str] = {}
    for g in test.question_groups:
        for q in g.questions:
            if q.id in seen:
                errors.append(f"Question ID {q.id} appears in both {seen[q.id]} and {g.id}")
            seen[q.id] = g.id

    # --- Warnings ---

    for i, p in enumerate(test.passages, start=1):
        if p.title in (f"Passage {i}", f"passage-{i}", "Passage"):
            warnings.append(f"Passage {i} has a generic fallback title — title extraction may have failed")

    for g in test.question_groups:
        if len(g.questions) > 13:
            warnings.append(f"Group {g.id} spans {len(g.questions)} questions — may be two merged groups")

    for g in test.question_groups:
        if g.type == "summary-completion":
            if "from the list" in (g.instruction or "").lower() and not g.word_list:
                warnings.append(f"Group {g.id}: summary-completion with 'from the list' instruction but no word_list extracted")

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)
