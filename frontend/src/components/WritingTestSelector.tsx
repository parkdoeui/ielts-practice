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

export function WritingTestSelector() {
  const navigate = useNavigate();
  const [tests, setTests] = useState<WritingTest[]>([]);
  const [sessions, setSessions] = useState<WritingSession[]>([]);

  useEffect(() => {
    const loaded = Object.values(writingFiles)
      .map((m) => m.default)
      .filter(isWritingTest)
      .sort((a, b) => getTestNumber(a) - getTestNumber(b));
    setTests(loaded);

    getWritingSessions().then(setSessions).catch(() => setSessions([]));
  }, []);

  const latestByTest = useMemo(() => {
    const map = new Map<string, WritingSession>();
    for (const session of sessions) {
      const existing = map.get(session.test_id);
      if (!existing || new Date(session.completed_at).getTime() > new Date(existing.completed_at).getTime()) {
        map.set(session.test_id, session);
      }
    }
    return map;
  }, [sessions]);

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">IELTS Writing Tests</h1>
        <p className="text-sm text-gray-500 mt-1">Task 1 + Task 2 timed writing mocks with AI feedback.</p>
      </div>
      <div className="grid gap-4">
        {tests.map((test) => {
          const completed = latestByTest.get(test.id);
          return (
            <button
              key={test.id}
              onClick={() => completed ? navigate(`/writing-results/${completed.id}`) : navigate(`/writing/${test.id}`)}
              className="text-left bg-white border border-gray-200 rounded-xl p-5 hover:border-blue-400 hover:shadow-md transition-all"
            >
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Writing Test {getTestNumber(test)}</p>
              <h2 className="font-semibold text-gray-900 mt-1">{test.title}</h2>
              <p className="text-sm text-gray-500 mt-1">2 tasks · {test.time_limit_minutes} min</p>
              {completed && (
                <div className="mt-3 text-xs text-emerald-700 font-medium">
                  Completed · Overall band {completed.grading.overall_band.toFixed(1)}
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
