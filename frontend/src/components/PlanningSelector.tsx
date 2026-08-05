import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router";
import {
  filterAndSortTask1Tests,
  getTask1QuestionType,
  TASK1_TYPE_META,
  TASK1_TYPE_ORDER,
  type Task1Sort,
  type Task1TypeFilter,
} from "../lib/task1QuestionTypes";
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
  const [questionType, setQuestionType] = useState<Task1TypeFilter>("all");
  const [sortBy, setSortBy] = useState<Task1Sort>("test-number");

  useEffect(() => {
    getPlanningSessions(taskNumber).then(setSessions).catch(() => setSessions([]));
  }, [taskNumber]);

  const latest = useMemo(() => latestByPrompt(sessions), [sessions]);
  const visibleTests = useMemo(
    () => taskNumber === 1
      ? filterAndSortTask1Tests(writingTests, questionType, sortBy)
      : writingTests,
    [questionType, sortBy, taskNumber],
  );

  return (
    <div className="max-w-5xl mx-auto w-full py-8 px-4">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Writing Idea Planning</h1>
        <p className="mt-1 text-sm text-gray-500">
          Generate relevant ideas and organize your response before writing. The timer simply records elapsed time.
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
          ? "Use four notes: introduction, overview, detail paragraph 1, and detail paragraph 2. No conclusion is needed."
          : "Plan the introduction, two developed arguments, and a consistent conclusion."}
      </div>

      {taskNumber === 1 && (
        <div className="mb-5 grid gap-3 rounded-xl border border-gray-200 bg-white p-4 sm:grid-cols-2">
          <label className="space-y-1 text-sm font-medium text-gray-700">
            <span className="block text-xs font-semibold uppercase tracking-[0.12em] text-gray-500">Question type</span>
            <select value={questionType} onChange={(event) => setQuestionType(event.target.value as Task1TypeFilter)} className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm">
              <option value="all">All question types</option>
              {TASK1_TYPE_ORDER.map((type) => <option key={type} value={type}>{TASK1_TYPE_META[type].label}</option>)}
            </select>
          </label>
          <label className="space-y-1 text-sm font-medium text-gray-700">
            <span className="block text-xs font-semibold uppercase tracking-[0.12em] text-gray-500">Sort by</span>
            <select value={sortBy} onChange={(event) => setSortBy(event.target.value as Task1Sort)} className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm">
              <option value="test-number">Test number</option>
              <option value="question-type">Question type</option>
            </select>
          </label>
        </div>
      )}

      <div className="grid gap-4">
        {visibleTests.map((test) => {
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
                  {taskNumber === 1 && (
                    <span className="mt-2 inline-flex rounded-full bg-violet-50 px-2.5 py-1 text-xs font-semibold text-violet-700">
                      {TASK1_TYPE_META[getTask1QuestionType(test.id)].label}
                    </span>
                  )}
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
        {visibleTests.length === 0 && (
          <div className="rounded-xl border border-gray-200 bg-white p-6 text-sm text-gray-500">No prompts match this question type.</div>
        )}
      </div>
    </div>
  );
}
