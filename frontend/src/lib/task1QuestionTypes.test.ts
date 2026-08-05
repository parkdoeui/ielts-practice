import { describe, expect, it } from "vitest";
import type { WritingTest } from "../types";
import {
  filterAndSortTask1Tests,
  getTask1QuestionType,
  TASK1_TYPE_ORDER,
} from "./task1QuestionTypes";

function test(id: number): WritingTest {
  return {
    id: `writing-test-${id}`,
    title: `Writing Test ${id}`,
    test_type: "academic",
    tasks: [],
    time_limit_minutes: 60,
    source_url: "https://example.com",
  };
}

describe("Task 1 question types", () => {
  it("classifies all 60 prompts with the audited distribution", () => {
    const counts = Object.fromEntries(TASK1_TYPE_ORDER.map((type) => [type, 0])) as Record<string, number>;
    for (let number = 1; number <= 60; number += 1) counts[getTask1QuestionType(`writing-test-${number}`)] += 1;
    expect(counts).toEqual({
      "line-graph": 17,
      "bar-chart": 14,
      table: 7,
      "pie-chart": 5,
      "map-plan": 7,
      "process-diagram": 7,
      "mixed-visuals": 3,
    });
  });

  it("filters by type and sorts type groups deterministically", () => {
    const tests = [test(1), test(3), test(2), test(7)];
    expect(filterAndSortTask1Tests(tests, "map-plan", "test-number").map((item) => item.id)).toEqual(["writing-test-1"]);
    expect(filterAndSortTask1Tests(tests, "all", "question-type").map((item) => item.id)).toEqual([
      "writing-test-2",
      "writing-test-3",
      "writing-test-1",
      "writing-test-7",
    ]);
  });
});
