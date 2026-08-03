import type { QuestionGroup } from "../types";

export function usesLetterCodedWordList(group: QuestionGroup): boolean {
  const acceptedAnswers = group.questions.flatMap((question) =>
    question.accepted_answers?.length ? question.accepted_answers : [question.answer],
  );
  return (
    acceptedAnswers.length > 0 &&
    acceptedAnswers.every((answer) => /^[A-Z]$/i.test(answer.trim()))
  );
}

export function getWordListChoice(
  group: QuestionGroup,
  word: string,
  index: number,
): { label: string; value: string } {
  if (!usesLetterCodedWordList(group)) {
    return { label: word, value: word };
  }

  const letter = String.fromCharCode(65 + index);
  return { label: `${letter}. ${word}`, value: letter };
}
