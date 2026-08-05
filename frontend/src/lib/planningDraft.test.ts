import { beforeEach, describe, expect, it, vi } from "vitest";
import { clearPlanningDraft, getPlanningDraft, savePlanningDraft } from "./planningDraft";

const plan = {
  kind: "task_2" as const,
  introduction: { position: "Agree", roadmap: "Two reasons" },
  body_1: { main_idea: "One", explanation: "Why", example: "Example", link_to_position: "Link" },
  body_2: { main_idea: "Two", explanation: "Why", example: "Example", link_to_position: "Link" },
  conclusion: { restated_position: "Agree", synthesis: "Therefore" },
};

describe("planning drafts", () => {
  beforeEach(() => {
    const values = new Map<string, string>();
    vi.stubGlobal("localStorage", {
      setItem: (key: string, value: string) => values.set(key, value),
      getItem: (key: string) => values.get(key) ?? null,
      removeItem: (key: string) => values.delete(key),
    });
  });

  it("round-trips a draft and isolates revisions", () => {
    savePlanningDraft({ testId: "writing-test-1", taskNumber: 2, startedAt: "2026-08-04T00:00:00Z", plan });
    expect(getPlanningDraft("writing-test-1", 2)?.plan).toEqual(plan);
    expect(getPlanningDraft("writing-test-1", 2, "parent-1")).toBeNull();
    clearPlanningDraft("writing-test-1", 2);
    expect(getPlanningDraft("writing-test-1", 2)).toBeNull();
  });
});
