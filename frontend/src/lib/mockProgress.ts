import {
  IMPLEMENTED_SKILLS,
  type FullTestSet,
  type MockSession,
} from "../types";

export type FullTestProgress = "not-started" | "in-progress" | "completed";
export type FullTestAction =
  | { kind: "start" }
  | { kind: "resume"; session: MockSession }
  | { kind: "results"; session: MockSession };

export function getSessionFullTest(
  session: MockSession,
  fullTests: FullTestSet[],
): FullTestSet | null {
  const storedMatch = fullTests.find((test) => test.id === session.full_test_id);
  if (storedMatch) return storedMatch;

  const testIdBySkill = new Map(
    session.sections.map((section) => [section.skill, section.test_id]),
  );
  return fullTests.find((test) =>
    testIdBySkill.get("listening") === test.listening_test_id &&
    testIdBySkill.get("reading") === test.reading_test_id &&
    testIdBySkill.get("writing") === test.writing_test_id &&
    testIdBySkill.get("speaking") === test.speaking_test_id
  ) ?? null;
}

export function isMockSessionCompleted(session: MockSession): boolean {
  const implementedSections = session.sections.filter((section) =>
    IMPLEMENTED_SKILLS.has(section.skill),
  );
  return implementedSections.length > 0 && implementedSections.every(
    (section) => section.session_id !== null,
  );
}

function newestFirst(a: MockSession, b: MockSession): number {
  return new Date(b.started_at).getTime() - new Date(a.started_at).getTime();
}

export function getFullTestAction(
  test: FullTestSet,
  sessions: MockSession[],
): FullTestAction {
  const matching = sessions
    .filter((session) => getSessionFullTest(session, [test]) !== null)
    .sort(newestFirst);
  const completed = matching.find(isMockSessionCompleted);

  if (completed) return { kind: "results", session: completed };
  if (matching[0]) return { kind: "resume", session: matching[0] };
  return { kind: "start" };
}

export function getFullTestProgress(
  test: FullTestSet,
  sessions: MockSession[],
): FullTestProgress {
  const action = getFullTestAction(test, sessions);
  if (action.kind === "results") return "completed";
  if (action.kind === "resume") return "in-progress";
  return "not-started";
}
