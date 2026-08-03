import type {
  FullTestSet,
  MockSession,
  SkillName,
  TestSession,
  WritingSession,
} from "../types";
import { roundToOverallBand } from "./grading";

export type FullTestSectionStatus =
  | "completed"
  | "grading-unavailable"
  | "not-taken"
  | "coming-soon";

export interface FullTestSectionResult {
  skill: SkillName;
  testId: string | null;
  sessionId: string | null;
  band: number | null;
  status: FullTestSectionStatus;
  correct: number | null;
  total: number | null;
  scoreText: string | null;
  task1Band: number | null;
  task2Band: number | null;
  detailPath: string | null;
}

export interface FullTestResult {
  overallBand: number | null;
  completed: boolean;
  sections: FullTestSectionResult[];
}

function startedAfterMock(startedAt: string, mockStartedAt: string): boolean {
  return new Date(startedAt).getTime() >= new Date(mockStartedAt).getTime();
}

export function reconcileMockSessionResults(
  mock: MockSession,
  objectiveSessions: TestSession[],
  writingSessions: WritingSession[],
): MockSession {
  // A completely untouched wrapper is still only an abandoned start. Requiring at
  // least one linked child avoids claiming unrelated standalone tests as a mock.
  if (!mock.sections.some((section) => section.session_id !== null)) return mock;

  const sections = mock.sections.map((section) => {
    if (section.session_id || !section.test_id) return section;

    if (section.skill === "listening" || section.skill === "reading") {
      const candidate = objectiveSessions
        .filter(
          (session) =>
            session.test_id === section.test_id &&
            startedAfterMock(session.started_at, mock.started_at),
        )
        .sort(
          (a, b) => new Date(a.started_at).getTime() - new Date(b.started_at).getTime(),
        )[0];
      return candidate
        ? { ...section, session_id: candidate.id, band: candidate.score.band_estimate }
        : section;
    }

    if (section.skill === "writing") {
      const candidate = writingSessions
        .filter(
          (session) =>
            session.test_id === section.test_id &&
            startedAfterMock(session.started_at, mock.started_at),
        )
        .sort(
          (a, b) => new Date(a.started_at).getTime() - new Date(b.started_at).getTime(),
        )[0];
      return candidate
        ? { ...section, session_id: candidate.id, band: candidate.grading.overall_band }
        : section;
    }

    return section;
  });
  const assigned = sections.filter((section) => section.test_id !== null);
  const completed = assigned.length > 0 && assigned.every((section) => section.session_id);
  const overallBand = roundToOverallBand(
    assigned
      .map((section) => section.band)
      .filter((band): band is number => band !== null && band > 0),
  );
  const linkedSessionIds = new Set(
    assigned.map((section) => section.session_id).filter(Boolean),
  );
  const completedAt = [...objectiveSessions, ...writingSessions]
    .filter((session) => linkedSessionIds.has(session.id))
    .sort(
      (a, b) =>
        new Date(b.completed_at).getTime() - new Date(a.completed_at).getTime(),
    )[0]?.completed_at;

  return {
    ...mock,
    sections,
    completed_at: completed ? mock.completed_at ?? completedAt ?? mock.started_at : mock.completed_at,
    overall_band: completed ? mock.overall_band ?? overallBand : mock.overall_band,
  };
}

function matchesFullTest(session: MockSession, test: FullTestSet): boolean {
  if (session.full_test_id === test.id) return true;
  const testIds = new Map(
    session.sections.map((section) => [section.skill, section.test_id]),
  );
  return (
    testIds.get("listening") === test.listening_test_id &&
    testIds.get("reading") === test.reading_test_id &&
    testIds.get("writing") === test.writing_test_id
  );
}

function latestByCompletedAt<T extends { completed_at: string }>(sessions: T[]): T | null {
  return [...sessions].sort(
    (a, b) =>
      new Date(b.completed_at).getTime() - new Date(a.completed_at).getTime(),
  )[0] ?? null;
}

export function synthesizeCompletedFullTests(
  fullTests: FullTestSet[],
  existing: MockSession[],
  objectiveSessions: TestSession[],
  writingSessions: WritingSession[],
): MockSession[] {
  const synthesized: MockSession[] = [];

  fullTests.forEach((test) => {
    const wrapper = existing.find((session) => matchesFullTest(session, test)) ?? null;
    const alreadyCompleted = wrapper?.sections
      .filter((section) => section.test_id !== null)
      .every((section) => section.session_id !== null);
    if (alreadyCompleted) return;

    const listening = latestByCompletedAt(
      objectiveSessions.filter((session) => session.test_id === test.listening_test_id),
    );
    const reading = latestByCompletedAt(
      objectiveSessions.filter((session) => session.test_id === test.reading_test_id),
    );
    const writing = latestByCompletedAt(
      writingSessions.filter((session) => session.test_id === test.writing_test_id),
    );
    if (!listening || !reading || !writing) return;

    const childSessions = [listening, reading, writing];
    const startedAt = childSessions
      .map((session) => session.started_at)
      .sort((a, b) => new Date(a).getTime() - new Date(b).getTime())[0];
    const completedAt = childSessions
      .map((session) => session.completed_at)
      .sort((a, b) => new Date(b).getTime() - new Date(a).getTime())[0];
    const bands = [
      listening.score.band_estimate,
      reading.score.band_estimate,
      writing.grading.overall_band,
    ];

    synthesized.push({
      id: wrapper?.id ?? `mock-restored-${test.id}`,
      full_test_id: test.id,
      mode: wrapper?.mode ?? "relaxed",
      started_at: wrapper?.started_at ?? startedAt,
      completed_at: completedAt,
      overall_band: roundToOverallBand(bands.filter((band) => band > 0)),
      sections: [
        {
          skill: "listening",
          test_id: test.listening_test_id,
          session_id: listening.id,
          band: listening.score.band_estimate,
        },
        {
          skill: "reading",
          test_id: test.reading_test_id,
          session_id: reading.id,
          band: reading.score.band_estimate,
        },
        {
          skill: "writing",
          test_id: test.writing_test_id,
          session_id: writing.id,
          band: writing.grading.overall_band,
        },
        {
          skill: "speaking",
          test_id: test.speaking_test_id,
          session_id: null,
          band: null,
        },
      ],
    });
  });

  return synthesized;
}

function resultPath(skill: SkillName, sessionId: string | null): string | null {
  if (!sessionId) return null;
  if (skill === "reading") return `/results/${sessionId}`;
  if (skill === "writing") return `/writing-results/${sessionId}`;
  return null;
}

export function buildFullTestResult(
  mock: MockSession,
  objectiveSessions: Record<string, TestSession | null>,
  writingSession: WritingSession | null,
): FullTestResult {
  const sections = mock.sections.map<FullTestSectionResult>((section) => {
    if (section.test_id === null) {
      return {
        skill: section.skill,
        testId: null,
        sessionId: null,
        band: null,
        status: "coming-soon",
        correct: null,
        total: null,
        scoreText: null,
        task1Band: null,
        task2Band: null,
        detailPath: null,
      };
    }

    const objective = section.session_id
      ? objectiveSessions[section.session_id] ?? null
      : null;
    const isWritingSession =
      section.skill === "writing" && writingSession?.id === section.session_id;
    const band = isWritingSession
      ? writingSession.grading.overall_band
      : objective?.score.band_estimate ?? section.band;
    const status: FullTestSectionStatus = !section.session_id
      ? "not-taken"
      : band === null || band <= 0
        ? "grading-unavailable"
        : "completed";

    return {
      skill: section.skill,
      testId: section.test_id,
      sessionId: section.session_id,
      band,
      status,
      correct: objective?.score.correct ?? null,
      total: objective?.score.total ?? null,
      scoreText: objective
        ? `${objective.score.correct}/${objective.score.total} correct`
        : null,
      task1Band: isWritingSession ? writingSession.grading.task_1.band : null,
      task2Band: isWritingSession ? writingSession.grading.task_2.band : null,
      detailPath: resultPath(section.skill, section.session_id),
    };
  });

  const computedOverall = roundToOverallBand(
    sections
      .map((section) => section.band)
      .filter((band): band is number => band !== null && band > 0),
  );
  const completedSections = sections.filter((section) => section.testId !== null);

  return {
    overallBand: mock.overall_band ?? computedOverall,
    completed:
      completedSections.length > 0 &&
      completedSections.every((section) => section.sessionId !== null),
    sections,
  };
}
