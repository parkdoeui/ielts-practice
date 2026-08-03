import { describe, expect, it } from "vitest";
import type { QuestionGroup } from "../types";
import { getWordListChoice, usesLetterCodedWordList } from "./readingWordList";

function summaryGroup(answers: string[]): QuestionGroup {
  return {
    id: "group-1-2",
    type: "summary-completion",
    passage_id: "passage-1",
    instruction: "Choose from the word bank.",
    questions: answers.map((answer, index) => ({
      id: index + 1,
      statement: "",
      answer,
    })),
    word_list: ["Axis", "Projection"],
  };
}

describe("Reading word-list choices", () => {
  it("submits option letters when the answer key is letter-coded", () => {
    const group = summaryGroup(["A", "B"]);

    expect(usesLetterCodedWordList(group)).toBe(true);
    expect(getWordListChoice(group, "Projection", 1)).toEqual({
      label: "B. Projection",
      value: "B",
    });
  });

  it("submits words when the answer key contains source words", () => {
    const group = summaryGroup(["Projection", "Axis"]);

    expect(usesLetterCodedWordList(group)).toBe(false);
    expect(getWordListChoice(group, "Projection", 1)).toEqual({
      label: "Projection",
      value: "Projection",
    });
  });
});
