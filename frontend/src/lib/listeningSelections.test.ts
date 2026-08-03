import { describe, expect, it } from "vitest";
import { getListeningSelectionUpdate } from "./listeningSelections";

describe("getListeningSelectionUpdate", () => {
  it("fills the first empty answer slot", () => {
    expect(getListeningSelectionUpdate([11, 12], {}, "C", 2)).toEqual({ questionId: 11, answer: "C" });
    expect(getListeningSelectionUpdate([11, 12], { 11: "C" }, "E", 2)).toEqual({ questionId: 12, answer: "E" });
  });

  it("clears the slot containing an unchecked option", () => {
    expect(getListeningSelectionUpdate([11, 12], { 11: "C", 12: "E" }, "C", 2)).toEqual({
      questionId: 11,
      answer: "",
    });
  });

  it("does not exceed the shared selection limit", () => {
    expect(getListeningSelectionUpdate([11, 12], { 11: "C", 12: "E" }, "A", 2)).toBeNull();
  });
});
