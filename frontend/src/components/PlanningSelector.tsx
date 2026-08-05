import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router";
import { getPlanningSessions } from "../services/api";
import type { PlanningSession, WritingTest } from "../types";

const writingFiles = import.meta.glob<{ default: WritingTest }>(
  "../data/writing-tests/*.json",
  { eager: true },
);

const writingTests = Object.values(writingFiles)
  .map((module) => module.default)
  .filter((test): test is WritingTest => Boolean(test?.id && test?.tasks?.length === 2))
  .sort((a, b) => Number(a.id.split("-").pop()) - Number(b.id.split("-").pop()));

function testNumber(test: WritingTest): number {
  return Number(test.id.match(/(\d+)$/)?.[1] ?? 0);
}

function latestByPrompt(sessions: PlanningSession[]): Map<string, PlanningSession> {
  const latest = new Map<string, PlanningSession>();
  for (const session of sessions) {
    const key = `${session.test_id}:${session.task_number}`;
    const current = latest.get(key);
    if (!current || new Date(session.completed_at).getTime() > new Date(current.completed_at).getTime()) {
      latest.set(key, session);
    }
  }
  return latest;
}

export function PlanningSelector() {
  const navigate = useNavigate();
  const [taskNumber, setTaskNumber] = useState<1 | 2>(2);
  const [sessions, setSessions] = useState<PlanningSession[]>([]);

  useEffect(() => {
    getPlanningSessions(taskNumber).then(setSessions).catch(() => setSessions([]));
  }, [taskNumber]);

  const latest = useMemo(() => latestByPrompt(sessions), [sessions]);

  return (
    <div className="max-w-5xl mx-auto w-full py-8 px-4">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Writing Idea Planning</h1>
        <p className="mt-1 text-sm text-gray-500">
          Spend five minutes generating relevant ideas and organizing your response before writing.
        </p>
      </div>

      <div className="mb-6 flex w-full gap-2 rounded-xl bg-gray-100 p-1 sm:w-fit">
        {[1, 2].map((value) => (
          <button
            key={value}
            type="button"
            onClick={() => setTaskNumber(value as 1 | 2)}
            className={`rounded-lg px-4 py-2 text-sm font-medium ${
              taskNumber === value ? "bg-white text-gray-900 shadow-sm" : "text-gray-500 hover:text-gray-700"
            }`}
          >
            Task {value} planning
          </button>
        ))}
      </div>

      <div className="mb-5 rounded-xl border border-blue-100 bg-blue-50 px-4 py-3 text-sm text-blue-900">
        {taskNumber === 1
          ? "Plan the visual subject, overview, and grouped details. No conclusion is needed."
          : "Plan the introduction, two developed arguments, and a consistent conclusion."}
      </div>

      <div className="grid gap-4">
        {writingTests.map((test) => {
          const task = test.tasks.find((item) => item.task_number === taskNumber);
          const previous = latest.get(`${test.id}:${taskNumber}`);
          if (!task) return null;
          return (
            <article key={test.id} className="rounded-xl border border-gray-200 bg-white p-5">
              <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
                <div className="min-w-0">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">
                    Writing Test {testNumber(test)} · Task {taskNumber}
                  </p>
                  <h2 className="mt-1 font-semibold text-gray-900">{test.title}</h2>
                  <p className="mt-2 line-clamp-3 text-sm leading-6 text-gray-600">{task.prompt}</p>
                  {previous && (
                    <p className="mt-3 text-xs text-gray-500">
                      Latest planning band <span className="font-semibold text-gray-800">{previous.feedback.planning_band.toFixed(1)}</span>
                      {" · "}{Math.round(previous.total_time_ms / 1000)}s
                    </p>
                  )}
                </div>
                <div className="flex shrink-0 flex-wrap gap-2">
                  {previous && (
                    <button
                      type="button"
                      onClick={() => navigate(`/planning-results/${previous.id}`)}
                      className="rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:border-blue-400 hover:text-blue-700"
                    >
                      Feedback
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => navigate(`/planning/${test.id}/${taskNumber}`)}
                    className="rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"
                  >
                    {previous ? "Practice again" : "Start planning"}
                  </button>
                </div>
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}
