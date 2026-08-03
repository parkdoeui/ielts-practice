import { describe, expect, it } from "vitest";
import type {
  FullTestSet,
  MockSession,
  TestSession,
  WritingSession,
  WritingTaskFeedback,
} from "../types";
import {
  buildFullTestResult,
  reconcileMockSessionResults,
  synthesizeCompletedFullTests,
} from "./fullTestResults";

const fullTest: FullTestSet = {
  id: "full-test-1",
  title: "Full Test 1",
  listening_test_id: "listening-test-202",
  reading_test_id: "test-295",
  writing_test_id: "writing-test-25",
  speaking_test_id: null,
};

const mock: MockSession = {
  id: "mock-1",
  full_test_id: "full-test-1",
  mode: "strict",
  started_at: "2026-08-03T10:00:00Z",
  sections: [
    { skill: "listening", test_id: "listening-test-202", session_id: "l-1", band: 7.5 },
    { skill: "reading", test_id: "test-295", session_id: "r-1", band: 6.5 },
    { skill: "writing", test_id: "writing-test-25", session_id: "w-1", band: 7 },
    { skill: "speaking", test_id: null, session_id: null, band: null },
  ],
};

function objectiveSession(
  id: string,
  testId: string,
  correct: number,
  band: number,
): TestSession {
  return {
    id,
    test_id: testId,
    started_at: "2026-08-03T10:00:00Z",
    completed_at: "2026-08-03T11:00:00Z",
    total_time_ms: 3_600_000,
    answers: [],
    score: { correct, total: 40, band_estimate: band },
  };
}

function writingFeedback(band: number): WritingTaskFeedback {
  return {
    band,
    criteria: {
      task_response: band,
      coherence_cohesion: band,
      lexical_resource: band,
      grammar_accuracy: band,
    },
    criterion_evidence: {
      task_response: "",
      coherence_cohesion: "",
      lexical_resource: "",
      grammar_accuracy: "",
    },
    detailed_improvement_points: {
      task_response: [],
      coherence_cohesion: [],
      lexical_resource: [],
      grammar_accuracy: [],
    },
    current_state: "",
    primary_goal: "",
    sample_answer: "",
  };
}

const writingSession: WritingSession = {
  id: "w-1",
  test_id: "writing-test-25",
  started_at: "2026-08-03T12:00:00Z",
  completed_at: "2026-08-03T13:00:00Z",
  total_time_ms: 3_600_000,
  answers: { "1": "report", "2": "essay" },
  grading: {
    overall_band: 7,
    task_1: writingFeedback(6.5),
    task_2: writingFeedback(7.5),
    action_points: [],
  },
};

describe("combined Full Test result", () => {
  it("combines objective scores, Writing task bands, and the overall band", () => {
    const result = buildFullTestResult(
      mock,
      {
        "l-1": objectiveSession("l-1", "listening-test-202", 34, 7.5),
        "r-1": objectiveSession("r-1", "test-295", 32, 6.5),
      },
      writingSession,
    );

    expect(result.completed).toBe(true);
    expect(result.overallBand).toBe(7);
    expect(result.sections.find((section) => section.skill === "listening")?.scoreText)
      .toBe("34/40 correct");
    expect(result.sections.find((section) => section.skill === "reading")?.scoreText)
      .toBe("32/40 correct");
    expect(result.sections.find((section) => section.skill === "writing"))
      .toMatchObject({ band: 7, task1Band: 6.5, task2Band: 7.5 });
    expect(result.sections.find((section) => section.skill === "speaking")?.status)
      .toBe("coming-soon");
  });

  it("keeps wrapper bands visible when child detail records are unavailable", () => {
    const result = buildFullTestResult(mock, {}, null);

    expect(result.overallBand).toBe(7);
    expect(result.sections.find((section) => section.skill === "reading"))
      .toMatchObject({ band: 6.5, scoreText: null, status: "completed" });
  });

  it("labels unavailable Writing grading without removing completion", () => {
    const ungraded: MockSession = {
      ...mock,
      sections: mock.sections.map((section) =>
        section.skill === "writing" ? { ...section, band: 0 } : section,
      ),
    };
    const result = buildFullTestResult(ungraded, {}, null);

    expect(result.completed).toBe(true);
    expect(result.overallBand).toBe(7);
    expect(result.sections.find((section) => section.skill === "writing")?.status)
      .toBe("grading-unavailable");
  });

  it("repairs a legacy wrapper from its separately persisted section results", () => {
    const stale: MockSession = {
      ...mock,
      overall_band: null,
      completed_at: null,
      sections: mock.sections.map((section) =>
        section.skill === "listening"
          ? section
          : { ...section, session_id: null, band: null },
      ),
    };
    const restored = reconcileMockSessionResults(
      stale,
      [
        objectiveSession("r-old", "test-295", 40, 9),
        {
          ...objectiveSession("r-1", "test-295", 32, 6.5),
          started_at: "2026-08-03T11:00:00Z",
        },
      ].map((session, index) =>
        index === 0 ? { ...session, started_at: "2026-08-02T11:00:00Z" } : session,
      ),
      [writingSession],
    );

    expect(restored.sections.find((section) => section.skill === "reading"))
      .toMatchObject({ session_id: "r-1", band: 6.5 });
    expect(restored.sections.find((section) => section.skill === "writing"))
      .toMatchObject({ session_id: "w-1", band: 7 });
    expect(restored.completed_at).toBeTruthy();
    expect(restored.overall_band).toBe(7);
  });

  it("does not turn an untouched wrapper into a completed standalone-test bundle", () => {
    const untouched: MockSession = {
      ...mock,
      sections: mock.sections.map((section) => ({
        ...section,
        session_id: null,
        band: null,
      })),
    };

    expect(reconcileMockSessionResults(
      untouched,
      [objectiveSession("r-1", "test-295", 32, 6.5)],
      [writingSession],
    )).toEqual(untouched);
  });

  it("synthesizes a wrapperless completed bundle from all three section records", () => {
    const synthesized = synthesizeCompletedFullTests(
      [fullTest],
      [],
      [
        objectiveSession("l-1", "listening-test-202", 34, 7.5),
        objectiveSession("r-1", "test-295", 32, 6.5),
      ],
      [writingSession],
    );

    expect(synthesized).toHaveLength(1);
    expect(synthesized[0]).toMatchObject({
      id: "mock-restored-full-test-1",
      full_test_id: "full-test-1",
      completed_at: writingSession.completed_at,
      overall_band: 7,
    });
    expect(synthesized[0].sections.map((section) => section.session_id))
      .toEqual(["l-1", "r-1", "w-1", null]);
  });

  it("does not synthesize a partial bundle or duplicate a completed wrapper", () => {
    const objective = [
      objectiveSession("l-1", "listening-test-202", 34, 7.5),
      objectiveSession("r-1", "test-295", 32, 6.5),
    ];

    expect(synthesizeCompletedFullTests([fullTest], [], objective, [])).toEqual([]);
    expect(synthesizeCompletedFullTests([fullTest], [mock], objective, [writingSession]))
      .toEqual([]);
  });

  it("upgrades an existing incomplete wrapper instead of creating a retake", () => {
    const incomplete: MockSession = {
      ...mock,
      id: "existing-mock",
      sections: mock.sections.map((section) => ({
        ...section,
        session_id: null,
        band: null,
      })),
    };
    const [restored] = synthesizeCompletedFullTests(
      [fullTest],
      [incomplete],
      [
        objectiveSession("l-1", "listening-test-202", 34, 7.5),
        objectiveSession("r-1", "test-295", 32, 6.5),
      ],
      [writingSession],
    );

    expect(restored.id).toBe("existing-mock");
    expect(restored.sections.every(
      (section) => section.test_id === null || section.session_id !== null,
    )).toBe(true);
  });
});
