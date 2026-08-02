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

describe("roundToOverallBand", () => {
  it("rounds a .25 average up to the next half band", () => {
    // avg 6.25 → 6.5
    expect(roundToOverallBand([6, 6, 6.5, 6.5])).toBe(6.5);
  });

  it("rounds a .75 average up to the next whole band", () => {
    // avg 6.75 → 7.0
    expect(roundToOverallBand([6.5, 6.5, 7, 7])).toBe(7);
  });

  it("rounds a .125 average down to the nearest half band", () => {
    // avg 6.125 → 6.0
    expect(roundToOverallBand([6, 6, 6, 6.5])).toBe(6);
  });

  it("averages only the bands present (ignores missing skills)", () => {
    expect(roundToOverallBand([7, 8])).toBe(7.5);
  });

  it("returns null when no bands are available", () => {
    expect(roundToOverallBand([])).toBeNull();
  });
});
