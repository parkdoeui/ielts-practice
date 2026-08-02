import { describe, expect, it } from "vitest";
import { isAnswerCorrect, isCompletionType, roundToOverallBand } from "./grading";

describe("grading completion helpers", () => {
  it("treats table completion as a completion type", () => {
    expect(isCompletionType("table-completion")).toBe(true);
  });

  it("treats diagram labeling as a completion type", () => {
    expect(isCompletionType("diagram-labeling")).toBe(true);
  });

  it("normalizes punctuation-heavy table completion answers", () => {
    expect(
      isAnswerCorrect("table-completion", "(big), large enough", [
        "big/ large enough",
      ]),
    ).toBe(true);
  });

  it("normalizes parenthetical diagram labeling answers", () => {
    expect(
      isAnswerCorrect("diagram-labeling", "(leaf) litter", ["leaf litter"]),
    ).toBe(true);
  });
});
