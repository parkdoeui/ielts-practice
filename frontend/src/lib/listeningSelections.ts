export interface ListeningSelectionUpdate {
  questionId: number;
  answer: string;
}

export function getListeningSelectionUpdate(
  questionIds: number[],
  answers: Record<number, string>,
  option: string,
  limit: number,
): ListeningSelectionUpdate | null {
  const selectedQuestionId = questionIds.find((questionId) => answers[questionId] === option);
  if (selectedQuestionId !== undefined) {
    return { questionId: selectedQuestionId, answer: "" };
  }

  const selectedCount = questionIds.filter((questionId) => Boolean(answers[questionId])).length;
  if (selectedCount >= limit) return null;

  const emptyQuestionId = questionIds.find((questionId) => !answers[questionId]);
  return emptyQuestionId === undefined ? null : { questionId: emptyQuestionId, answer: option };
}
