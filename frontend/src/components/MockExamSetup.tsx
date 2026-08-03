import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router";
import { listMockSessions, saveMockSession } from "../services/api";
import {
  IMPLEMENTED_SKILLS,
  type FullTestSet,
  type MockMode,
  type MockSession,
} from "../types";
import {
  getFullTestAction,
  getFullTestProgress,
  getSessionFullTest,
  type FullTestProgress,
} from "../lib/mockProgress";
import { FULL_TESTS } from "../lib/fullTests";

const MODES: { value: MockMode; title: string; blurb: string }[] = [
  { value: "relaxed", title: "Relaxed", blurb: "Pause and resume between sections. Per-section timers." },
  { value: "strict", title: "Strict", blurb: "Continuous sitting in exam order — no leaving between sections." },
];

const PROGRESS_LABELS: Record<FullTestProgress, string> = {
  "not-started": "Not started",
  "in-progress": "In progress",
  completed: "Completed",
};

const PROGRESS_STYLES: Record<FullTestProgress, string> = {
  "not-started": "bg-gray-100 text-gray-600",
  "in-progress": "bg-amber-100 text-amber-800",
  completed: "bg-emerald-100 text-emerald-800",
};

function createMockSession(fullTest: FullTestSet, mode: MockMode): MockSession {
  const startedAt = new Date();
  return {
    id: `mock-${startedAt.getTime()}`,
    full_test_id: fullTest.id,
    mode,
    started_at: startedAt.toISOString(),
    sections: [
      { skill: "listening", test_id: fullTest.listening_test_id, session_id: null, band: null },
      { skill: "reading", test_id: fullTest.reading_test_id, session_id: null, band: null },
      { skill: "writing", test_id: fullTest.writing_test_id, session_id: null, band: null },
      { skill: "speaking", test_id: fullTest.speaking_test_id, session_id: null, band: null },
    ],
  };
}

export function MockExamSetup() {
  const navigate = useNavigate();
  const fullTests = FULL_TESTS;
  const mockSessions = useMemo(() => listMockSessions(), []);
  const firstStartableId = fullTests.find(
    (test) => getFullTestAction(test, mockSessions).kind === "start",
  )?.id ?? "";
  const [mode, setMode] = useState<MockMode>("relaxed");
  const [fullTestId, setFullTestId] = useState(firstStartableId);
  const selectedFullTest = fullTests.find((test) => test.id === fullTestId) ?? null;

  const inProgress = useMemo(
    () =>
      fullTests
        .map((test) => getFullTestAction(test, mockSessions))
        .filter((action) => action.kind === "resume")
        .map((action) => action.session)
        .sort(
          (a, b) =>
            new Date(b.started_at).getTime() - new Date(a.started_at).getTime(),
        )
        .slice(0, 1),
    [fullTests, mockSessions],
  );

  function startMock() {
    if (!selectedFullTest) return;
    const existing = getFullTestAction(selectedFullTest, listMockSessions());
    if (existing.kind === "results") {
      navigate(`/mock-results/${existing.session.id}`);
      return;
    }
    if (existing.kind === "resume") {
      navigate(`/mock/${existing.session.id}`);
      return;
    }
    const mock = createMockSession(selectedFullTest, mode);
    saveMockSession(mock);
    navigate(`/mock/${mock.id}`);
  }

  const canStart = Boolean(
    selectedFullTest && getFullTestAction(selectedFullTest, mockSessions).kind === "start",
  );

  return (
    <div className="mx-auto max-w-2xl px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Full Test</h1>
        <p className="mt-1 text-sm text-gray-500">
          Sit a mock in exam order — Listening, Reading, Writing, Speaking — and get a combined band.
          Speaking is coming soon and is skipped for now.
        </p>
      </div>

      {inProgress.length > 0 && (
        <section className="mb-6">
          <h2 className="mb-2 text-sm font-semibold text-gray-700">Resume</h2>
          <div className="space-y-2">
            {inProgress.map((session) => {
              const sessionFullTest = getSessionFullTest(session, fullTests);
              const done = session.sections.filter(
                (s) => IMPLEMENTED_SKILLS.has(s.skill) && s.session_id !== null,
              ).length;
              const total = session.sections.filter((s) => IMPLEMENTED_SKILLS.has(s.skill)).length;
              return (
                <Link
                  key={session.id}
                  to={`/mock/${session.id}`}
                  className="flex items-center justify-between rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 hover:border-amber-300"
                >
                  <span>
                    <span className="block text-sm font-semibold text-gray-900">
                      {sessionFullTest?.title ?? "Full Test"}
                    </span>
                    <span className="mt-0.5 block text-xs text-gray-600">
                      In progress · {session.mode} · {done}/{total} sections done
                    </span>
                  </span>
                  <span className="text-sm font-medium text-amber-700">Resume →</span>
                </Link>
              );
            })}
          </div>
        </section>
      )}

      <section className="mb-6">
        <h2 className="mb-2 text-sm font-semibold text-gray-700">Mode</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          {MODES.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => setMode(option.value)}
              className={`rounded-xl border p-4 text-left transition-colors ${
                mode === option.value
                  ? "border-blue-500 bg-blue-50"
                  : "border-gray-200 bg-white hover:border-gray-300"
              }`}
            >
              <p className="font-semibold text-gray-900">{option.title}</p>
              <p className="mt-1 text-xs leading-5 text-gray-500">{option.blurb}</p>
            </button>
          ))}
        </div>
      </section>

      <section className="mb-6">
        <h2 className="mb-2 text-sm font-semibold text-gray-700">Choose a Full Test</h2>
        <div className="space-y-2">
          {fullTests.map((test) => {
            const selected = test.id === fullTestId;
            const progress = getFullTestProgress(test, mockSessions);
            const action = getFullTestAction(test, mockSessions);
            const cardClass = `flex w-full items-center justify-between rounded-xl border px-4 py-3 text-left transition-colors ${
              selected
                ? "border-blue-500 bg-blue-50 text-blue-900"
                : "border-gray-200 bg-white text-gray-900 hover:border-gray-300"
            }`;
            const cardContent = (
              <>
                <span className="text-sm font-semibold">{test.title}</span>
                <span className="flex items-center gap-3">
                  <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${PROGRESS_STYLES[progress]}`}>
                    {PROGRESS_LABELS[progress]}
                  </span>
                  {action.kind === "start" ? (
                    <span
                      aria-hidden="true"
                      className={`flex h-5 w-5 items-center justify-center rounded-full border ${
                        selected ? "border-blue-600" : "border-gray-300"
                      }`}
                    >
                      {selected && <span className="h-2.5 w-2.5 rounded-full bg-blue-600" />}
                    </span>
                  ) : (
                    <span className={`text-xs font-semibold ${
                      action.kind === "results" ? "text-emerald-700" : "text-amber-700"
                    }`}>
                      {action.kind === "results" ? "View result →" : "Resume →"}
                    </span>
                  )}
                </span>
              </>
            );

            if (action.kind === "results") {
              return (
                <Link key={test.id} to={`/mock-results/${action.session.id}`} className={cardClass}>
                  {cardContent}
                </Link>
              );
            }

            if (action.kind === "resume") {
              return (
                <Link key={test.id} to={`/mock/${action.session.id}`} className={cardClass}>
                  {cardContent}
                </Link>
              );
            }

            return (
              <button
                key={test.id}
                type="button"
                aria-pressed={selected}
                onClick={() => setFullTestId(test.id)}
                className={cardClass}
              >
                {cardContent}
              </button>
            );
          })}
        </div>
      </section>

      {canStart ? (
        <button
          type="button"
          onClick={startMock}
          className="rounded-lg bg-blue-600 px-6 py-3 text-sm font-medium text-white hover:bg-blue-700"
        >
          Start Full Test
        </button>
      ) : (
        <p className="text-sm text-gray-500">
          Completed Full Tests are available through their View result links and cannot be retaken.
        </p>
      )}
    </div>
  );
}
