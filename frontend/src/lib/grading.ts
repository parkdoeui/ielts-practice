import type { QuestionType } from "../types";

const COMPLETION_TYPES: QuestionType[] = [
  "sentence-completion",
  "summary-completion",
  "table-completion",
  "diagram-labeling",
  "note-completion",
];

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
  return COMPLETION_TYPES.includes(questionType);
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

/**
 * IELTS overall band = the mean of the skill bands rounded to the nearest half band
 * (a .25 average rounds up to .5, a .75 average rounds up to the next whole band).
 * `Math.round(avg * 2) / 2` reproduces that rule exactly. Returns null when no bands
 * are available yet (e.g. only coming-soon sections).
 */
export function roundToOverallBand(bands: number[]): number | null {
  const present = bands.filter(
    (band): band is number => typeof band === "number" && !Number.isNaN(band),
  );
  if (present.length === 0) return null;
  const avg = present.reduce((sum, band) => sum + band, 0) / present.length;
  return Math.round(avg * 2) / 2;
}
