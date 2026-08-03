import {
  IMPLEMENTED_SKILLS,
  type FullTestSet,
  type MockSession,
} from "../types";

export type FullTestProgress = "not-started" | "in-progress" | "completed";

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

function isCompleted(session: MockSession): boolean {
  const implementedSections = session.sections.filter((section) =>
    IMPLEMENTED_SKILLS.has(section.skill),
  );
  return implementedSections.length > 0 && implementedSections.every(
    (section) => section.session_id !== null,
  );
}

export function getFullTestProgress(
  test: FullTestSet,
  sessions: MockSession[],
): FullTestProgress {
  const latest = sessions
    .filter((session) => getSessionFullTest(session, [test]) !== null)
    .sort(
      (a, b) =>
        new Date(b.started_at).getTime() - new Date(a.started_at).getTime(),
    )[0];

  if (!latest) return "not-started";
  return isCompleted(latest) ? "completed" : "in-progress";
}
