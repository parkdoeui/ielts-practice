import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router";
import type { ReadingTest, TestSession } from "../types";

const testFiles = import.meta.glob<{ default: ReadingTest }>(
  "../data/tests/*.json",
  { eager: true }
);

type SelectorTab = "not-started" | "completed";

interface CompletedTestSummary {
  sessionId: string;
  completedAt: string;
  correct: number;
  total: number;
  bandEstimate: number;
}

interface TestListItem {
  test: ReadingTest;
  completion: CompletedTestSummary | null;
  testNumber: number;
}

function getTestNumber(test: ReadingTest): number {
  const idMatch = test.id.match(/test-(\d+)/i);
  if (idMatch) {
    return Number(idMatch[1]);
  }

  const titleMatch = test.title.match(/test\s*(\d+)/i);
  return titleMatch ? Number(titleMatch[1]) : Number.MAX_SAFE_INTEGER;
}

function getStoredSessions(): TestSession[] {
  const passcode = localStorage.getItem("ielts_passcode") ?? "";
  const sessions: TestSession[] = [];

  for (let i = 0; i < localStorage.length; i += 1) {
    const key = localStorage.key(i);
    if (!key?.startsWith("ielts_session_")) {
      continue;
    }

    try {
      const session = JSON.parse(localStorage.getItem(key) ?? "") as TestSession;
      if (!passcode || session.passcode === passcode) {
        sessions.push(session);
      }
    } catch {
      // Ignore malformed session entries.
    }
  }

  return sessions;
}

function buildLatestSessionMap(sessions: TestSession[]) {
  const latestByTestId = new Map<string, CompletedTestSummary>();

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
        correct: session.score.correct,
        total: session.score.total,
        bandEstimate: session.score.band_estimate,
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

function sortTestsAscending(a: TestListItem, b: TestListItem) {
  if (a.testNumber !== b.testNumber) {
    return a.testNumber - b.testNumber;
  }
  return a.test.title.localeCompare(b.test.title);
}

export function TestSelector() {
  const [tests, setTests] = useState<ReadingTest[]>([]);
  const [tab, setTab] = useState<SelectorTab>("not-started");
  const [sessions, setSessions] = useState<TestSession[]>([]);
  const navigate = useNavigate();

  useEffect(() => {
    const loaded = Object.values(testFiles)
      .map((m) => m.default)
      .sort((a, b) => getTestNumber(a) - getTestNumber(b) || a.title.localeCompare(b.title));
    setTests(loaded);
    setSessions(getStoredSessions());
  }, []);

  const testItems = useMemo(() => {
    const latestByTestId = buildLatestSessionMap(sessions);

    return tests
      .map((test) => ({
        test,
        completion: latestByTestId.get(test.id) ?? null,
        testNumber: getTestNumber(test),
      }))
      .sort(sortTestsAscending);
  }, [tests, sessions]);

  const notStartedTests = testItems.filter((item) => item.completion === null);
  const completedTests = testItems.filter((item) => item.completion !== null);
  const visibleTests = tab === "not-started" ? notStartedTests : completedTests;

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">IELTS Reading Tests</h1>
        <p className="text-sm text-gray-500 mt-1">
          Browse tests in order and review your completed results separately.
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
            ? "No not-started tests found."
            : "No completed tests found yet."}
        </div>
      ) : (
        <div className="grid gap-4">
          {visibleTests.map(({ test, completion, testNumber }) => {
            const totalQuestions = test.question_groups.reduce(
              (sum, group) => sum + group.questions.length,
              0
            );

            return (
              <button
                key={test.id}
                onClick={() => navigate(`/test/${test.id}`)}
                className="text-left bg-white border border-gray-200 rounded-xl p-5 hover:border-blue-400 hover:shadow-md transition-all"
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">
                      Test {testNumber}
                    </p>
                    <h2 className="font-semibold text-gray-900 mt-1">{test.title}</h2>
                    <p className="text-sm text-gray-500 mt-1">
                      {test.passages.length} passages · {totalQuestions} questions · {test.time_limit_minutes} min
                    </p>

                    {completion && (
                      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-gray-600">
                        <span className="px-2 py-1 rounded-full bg-emerald-50 text-emerald-700 font-medium">
                          Band {completion.bandEstimate.toFixed(1)}
                        </span>
                        <span className="px-2 py-1 rounded-full bg-blue-50 text-blue-700 font-medium">
                          {completion.correct}/{completion.total} correct
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
