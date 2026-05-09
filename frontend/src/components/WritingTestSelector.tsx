import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router";
import { getWritingSessions } from "../services/api";
import type { WritingSession, WritingTest } from "../types";

const writingFiles = import.meta.glob<{ default: WritingTest }>(
  "../data/writing-tests/*.json",
  { eager: true },
);

function isWritingTest(value: unknown): value is WritingTest {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<WritingTest>;
  return (
    typeof candidate.id === "string" &&
    typeof candidate.title === "string" &&
    Array.isArray(candidate.tasks)
  );
}

function getTestNumber(test: WritingTest): number {
  const idMatch = test.id.match(/writing-test-(\d+)/i);
  if (idMatch) return Number(idMatch[1]);
  const titleMatch = test.title.match(/test\s*(\d+)/i);
  return titleMatch ? Number(titleMatch[1]) : Number.MAX_SAFE_INTEGER;
}

type SelectorTab = "not-started" | "completed";

interface CompletedWritingSummary {
  sessionId: string;
  completedAt: string;
  overallBand: number;
}

interface WritingListItem {
  test: WritingTest;
  completion: CompletedWritingSummary | null;
  testNumber: number;
}

function buildLatestWritingSessionMap(sessions: WritingSession[]) {
  const latestByTestId = new Map<string, CompletedWritingSummary>();

  for (const session of sessions) {
    const existing = latestByTestId.get(session.test_id);
    if (
      !existing ||
      new Date(session.completed_at).getTime() >
        new Date(existing.completedAt).getTime()
    ) {
      latestByTestId.set(session.test_id, {
        sessionId: session.id,
        completedAt: session.completed_at,
        overallBand: session.grading.overall_band,
      });
    }
  }

  return latestByTestId;
}

function formatCompletedDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function sortWritingTestsAscending(a: WritingListItem, b: WritingListItem) {
  if (a.testNumber !== b.testNumber) {
    return a.testNumber - b.testNumber;
  }
  return a.test.title.localeCompare(b.test.title);
}

export function WritingTestSelector() {
  const navigate = useNavigate();
  const [tests, setTests] = useState<WritingTest[]>([]);
  const [tab, setTab] = useState<SelectorTab>("not-started");
  const [sessions, setSessions] = useState<WritingSession[]>([]);

  useEffect(() => {
    const loaded = Object.values(writingFiles)
      .map((m) => m.default)
      .filter(isWritingTest)
      .sort((a, b) => getTestNumber(a) - getTestNumber(b));
    setTests(loaded);

    getWritingSessions().then(setSessions).catch(() => setSessions([]));
  }, []);

  const testItems = useMemo(() => {
    const latestByTest = buildLatestWritingSessionMap(sessions);

    return tests
      .map((test) => ({
        test,
        completion: latestByTest.get(test.id) ?? null,
        testNumber: getTestNumber(test),
      }))
      .sort(sortWritingTestsAscending);
  }, [tests, sessions]);

  const notStartedTests = testItems.filter((item) => item.completion === null);
  const completedTests = testItems.filter((item) => item.completion !== null);
  const visibleTests = tab === "not-started" ? notStartedTests : completedTests;

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">IELTS Writing Tests</h1>
        <p className="text-sm text-gray-500 mt-1">
          Browse writing tests in order and review your completed AI feedback separately.
        </p>
      </div>

      <div className="flex gap-2 mb-6 rounded-xl bg-gray-100 p-1 w-full sm:w-fit">
        <button
          onClick={() => setTab("not-started")}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
            tab === "not-started"
              ? "bg-white text-gray-900 shadow-sm"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          Not Started ({notStartedTests.length})
        </button>
        <button
          onClick={() => setTab("completed")}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
            tab === "completed"
              ? "bg-white text-gray-900 shadow-sm"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          Completed ({completedTests.length})
        </button>
      </div>

      {visibleTests.length === 0 ? (
        <div className="bg-white border border-gray-200 rounded-xl p-6 text-sm text-gray-500">
          {tab === "not-started"
            ? "No not-started writing tests found."
            : "No completed writing tests found yet."}
        </div>
      ) : (
        <div className="grid gap-4">
          {visibleTests.map(({ test, completion, testNumber }) => {
            return (
              <button
                key={test.id}
                onClick={() =>
                  completion
                    ? navigate(`/writing-results/${completion.sessionId}`)
                    : navigate(`/writing/${test.id}`)
                }
                className="text-left bg-white border border-gray-200 rounded-xl p-5 hover:border-blue-400 hover:shadow-md transition-all"
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">
                      Writing Test {testNumber}
                    </p>
                    <h2 className="font-semibold text-gray-900 mt-1">{test.title}</h2>
                    <p className="text-sm text-gray-500 mt-1">
                      2 tasks · {test.time_limit_minutes} min
                    </p>

                    {completion && (
                      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-gray-600">
                        <span className="px-2 py-1 rounded-full bg-emerald-50 text-emerald-700 font-medium">
                          Band {completion.overallBand.toFixed(1)}
                        </span>
                        <span className="text-gray-400">
                          Completed {formatCompletedDate(completion.completedAt)}
                        </span>
                      </div>
                    )}
                  </div>

                  <span className="shrink-0 px-2 py-1 text-xs font-medium rounded-full bg-blue-50 text-blue-700 capitalize">
                    {test.test_type}
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
