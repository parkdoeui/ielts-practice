import { describe, expect, it } from "vitest";
import type { FullTestSet, MockSession } from "../types";
import {
  getFullTestAction,
  getFullTestProgress,
  getSessionFullTest,
  isMockSessionCompleted,
} from "./mockProgress";

const fullTest: FullTestSet = {
  id: "full-test-1",
  title: "Full Test 1",
  listening_test_id: "listening-test-202",
  reading_test_id: "test-295",
  writing_test_id: "writing-test-25",
  speaking_test_id: null,
};

function mockSession(
  startedAt: string,
  completedSkills: Array<"listening" | "reading" | "writing"> = [],
  includeFullTestId = true,
): MockSession {
  return {
    id: `mock-${startedAt}`,
    ...(includeFullTestId ? { full_test_id: fullTest.id } : {}),
    mode: "relaxed",
    started_at: startedAt,
    sections: [
      { skill: "listening", test_id: fullTest.listening_test_id, session_id: completedSkills.includes("listening") ? "l-1" : null, band: null },
      { skill: "reading", test_id: fullTest.reading_test_id, session_id: completedSkills.includes("reading") ? "r-1" : null, band: null },
      { skill: "writing", test_id: fullTest.writing_test_id, session_id: completedSkills.includes("writing") ? "w-1" : null, band: null },
      { skill: "speaking", test_id: null, session_id: null, band: null },
    ],
  };
}

describe("Full Test progress", () => {
  it("reports not started without a matching attempt", () => {
    expect(getFullTestProgress(fullTest, [])).toBe("not-started");
  });

  it("reports fresh and partial attempts as in progress", () => {
    expect(getFullTestProgress(fullTest, [mockSession("2026-08-02T10:00:00Z")])).toBe("in-progress");
    expect(getFullTestProgress(fullTest, [mockSession("2026-08-02T10:00:00Z", ["listening"])]))
      .toBe("in-progress");
  });

  it("reports all implemented sections complete even though Speaking is unavailable", () => {
    const completed = mockSession(
      "2026-08-02T10:00:00Z",
      ["listening", "reading", "writing"],
    );
    expect(getFullTestProgress(fullTest, [completed])).toBe("completed");
  });

  it("keeps a completed result canonical over a later incomplete duplicate", () => {
    const completed = mockSession(
      "2026-08-02T10:00:00Z",
      ["listening", "reading", "writing"],
    );
    const retake = mockSession("2026-08-02T11:00:00Z");
    expect(getFullTestProgress(fullTest, [completed, retake])).toBe("completed");
    expect(getFullTestAction(fullTest, [completed, retake])).toEqual({
      kind: "results",
      session: completed,
    });
  });

  it("returns start, resume, and results actions for the bundle lifecycle", () => {
    const inProgress = mockSession("2026-08-02T10:00:00Z", ["listening"]);
    const completed = mockSession(
      "2026-08-02T11:00:00Z",
      ["listening", "reading", "writing"],
    );

    expect(getFullTestAction(fullTest, [])).toEqual({ kind: "start" });
    expect(getFullTestAction(fullTest, [inProgress])).toEqual({
      kind: "resume",
      session: inProgress,
    });
    expect(getFullTestAction(fullTest, [inProgress, completed])).toEqual({
      kind: "results",
      session: completed,
    });
    expect(isMockSessionCompleted(inProgress)).toBe(false);
    expect(isMockSessionCompleted(completed)).toBe(true);
  });

  it("recognizes a restored backend result as the canonical completed action", () => {
    const restored = {
      ...mockSession(
        "2026-08-02T11:00:00Z",
        ["listening", "reading", "writing"],
      ),
      completed_at: "2026-08-02T13:30:00Z",
      overall_band: 7,
    };

    expect(getFullTestAction(fullTest, [restored])).toEqual({
      kind: "results",
      session: restored,
    });
  });

  it("matches older sessions by their section IDs", () => {
    const legacy = mockSession("2026-08-02T10:00:00Z", [], false);
    expect(getSessionFullTest(legacy, [fullTest])).toEqual(fullTest);
  });
});
