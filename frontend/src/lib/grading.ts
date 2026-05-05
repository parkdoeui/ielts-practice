import type { QuestionType } from "../types";

export function estimateBand(correct: number, total: number): number {
  const score = Math.round((correct / total) * 40);
  if (score >= 39) return 9.0;
  if (score >= 37) return 8.5;
  if (score >= 35) return 8.0;
  if (score >= 33) return 7.5;
  if (score >= 30) return 7.0;
  if (score >= 27) return 6.5;
  if (score >= 23) return 6.0;
  if (score >= 19) return 5.5;
  if (score >= 15) return 5.0;
  if (score >= 13) return 4.5;
  return 4.0;
}

export function isCompletionType(questionType: QuestionType): boolean {
  return (
    questionType === "sentence-completion" ||
    questionType === "summary-completion"
  );
}

export function normalizeCompletionAnswer(value: string): string {
  return value
    .toLowerCase()
    .trim()
    .replace(/[()]/g, " ")
    .replace(/[.,/#!$%^&*;:{}=_`~[\]\\'"?+-]/g, " ")
    .replace(/\band\b/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function normalizeAnswer(questionType: QuestionType, value: string): string {
  if (isCompletionType(questionType)) {
    return normalizeCompletionAnswer(value);
  }

  return value.trim().toLowerCase();
}

export function isAnswerCorrect(
  questionType: QuestionType,
  userAnswer: string,
  acceptedAnswers: string[],
): boolean {
  const normalizedUserAnswer = normalizeAnswer(questionType, userAnswer);
  return acceptedAnswers.some(
    (answer) => normalizeAnswer(questionType, answer) === normalizedUserAnswer,
  );
}
