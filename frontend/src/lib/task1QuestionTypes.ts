import type { Task1QuestionType, WritingTest } from "../types";

export type Task1Sort = "test-number" | "question-type";
export type Task1TypeFilter = Task1QuestionType | "all";

export interface Task1TypeMeta {
  label: string;
  guideHeading: string;
}

export const TASK1_TYPE_ORDER: Task1QuestionType[] = [
  "line-graph",
  "bar-chart",
  "table",
  "pie-chart",
  "map-plan",
  "process-manufacturing",
  "natural-lifecycle",
  "mixed-visuals",
];

export const TASK1_TYPE_META: Record<Task1QuestionType, Task1TypeMeta> = {
  "line-graph": {
    label: "Line graph",
    guideHeading: "Line Graphs",
  },
  "bar-chart": {
    label: "Bar chart",
    guideHeading: "Bar Charts",
  },
  table: {
    label: "Table",
    guideHeading: "Tables",
  },
  "pie-chart": {
    label: "Pie chart",
    guideHeading: "Pie Charts",
  },
  "map-plan": {
    label: "Map or plan",
    guideHeading: "Maps and Plans",
  },
  "process-manufacturing": {
    label: "Manufacturing or system",
    guideHeading: "Processes and Manufacturing Diagrams",
  },
  "natural-lifecycle": {
    label: "Natural process or lifecycle",
    guideHeading: "Natural Processes and Lifecycles",
  },
  "mixed-visuals": {
    label: "Mixed visuals",
    guideHeading: "Mixed Visuals",
  },
};

const TEST_NUMBERS_BY_TYPE: Record<Task1QuestionType, number[]> = {
  "line-graph": [2, 6, 8, 14, 17, 22, 24, 26, 32, 33, 39, 42, 46, 47, 50, 52, 60],
  "bar-chart": [3, 5, 11, 12, 23, 31, 35, 36, 38, 40, 45, 48, 55, 57],
  table: [10, 16, 18, 25, 43, 54, 58],
  "pie-chart": [9, 30, 41, 51, 56],
  "map-plan": [1, 4, 13, 20, 27, 34, 37],
  "process-manufacturing": [15, 19, 29, 49, 53],
  "natural-lifecycle": [59],
  "mixed-visuals": [7, 21, 28, 44],
};

const TEST_TYPE_BY_NUMBER = Object.fromEntries(
  Object.entries(TEST_NUMBERS_BY_TYPE).flatMap(([type, numbers]) =>
    numbers.map((number) => [number, type as Task1QuestionType]),
  ),
) as Record<number, Task1QuestionType>;

export function writingTestNumber(testId: string): number {
  return Number(testId.match(/(\d+)$/)?.[1] ?? 0);
}

export function getTask1QuestionType(testId: string): Task1QuestionType {
  const number = writingTestNumber(testId);
  const type = TEST_TYPE_BY_NUMBER[number];
  if (!type) throw new Error(`Missing Task 1 question type for ${testId}`);
  return type;
}

export function filterAndSortTask1Tests(
  tests: WritingTest[],
  filter: Task1TypeFilter,
  sort: Task1Sort,
): WritingTest[] {
  return tests
    .filter((test) => filter === "all" || getTask1QuestionType(test.id) === filter)
    .sort((left, right) => {
      const leftNumber = writingTestNumber(left.id);
      const rightNumber = writingTestNumber(right.id);
      if (sort === "question-type") {
        const typeDifference = TASK1_TYPE_ORDER.indexOf(getTask1QuestionType(left.id))
          - TASK1_TYPE_ORDER.indexOf(getTask1QuestionType(right.id));
        if (typeDifference !== 0) return typeDifference;
      }
      return leftNumber - rightNumber;
    });
}
