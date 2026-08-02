import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { getWritingSessions, submitWritingSession } from "../services/api";
import { TimerBar } from "./TimerBar";
import { CbtStatusBar, FONT_SCALE_ZOOM, type FontScale } from "./CbtStatusBar";
import type { WritingAnswersJson, WritingSession, WritingTest as WritingTestType } from "../types";

export interface WritingSectionResult {
  skill: "writing";
  sessionId: string;
  band: number;
}

interface WritingTestProps {
  embeddedTestId?: string;
  onComplete?: (result: WritingSectionResult) => void;
}

const writingFiles = import.meta.glob<{ default: WritingTestType }>(
  "../data/writing-tests/*.json",
  { eager: true },
);

function isWritingTest(value: unknown): value is WritingTestType {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<WritingTestType>;
  return typeof candidate.id === "string" && Array.isArray(candidate.tasks);
}

function countWords(value: string): number {
  const words = value.trim().match(/\b[\w'-]+\b/g);
  return words ? words.length : 0;
}

function buildWritingAnswersJson(
  test: WritingTestType,
  answers: Record<string, string>,
): WritingAnswersJson {
  const promptByTask = Object.fromEntries(
    test.tasks.map((task) => [String(task.task_number), task.prompt]),
  );

  return {
    task1: {
      prompt: promptByTask["1"] ?? "",
      answer: answers["1"] ?? "",
    },
    task2: {
      prompt: promptByTask["2"] ?? "",
      answer: answers["2"] ?? "",
    },
  };
}

interface PreviousWritingAttempt {
  actionPoints: string[];
}

function getActionPointsForTask(points: string[], taskNumber: 1 | 2): string[] {
  if (points.length <= 1) return taskNumber === 2 ? points : [];
  const midpoint = Math.ceil(points.length / 2);
  return taskNumber === 1 ? points.slice(0, midpoint) : points.slice(midpoint);
}

export function WritingTest({ embeddedTestId, onComplete }: WritingTestProps = {}) {
  const params = useParams<{ id: string }>();
  const id = embeddedTestId ?? params.id;
  const embedded = Boolean(onComplete);
  const navigate = useNavigate();
  const [answers, setAnswers] = useState<Record<string, string>>({ "1": "", "2": "" });
  const [startedAt] = useState(() => new Date().toISOString());
  const [startMs] = useState(() => Date.now());
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [previousAttempt, setPreviousAttempt] = useState<PreviousWritingAttempt | null>(null);
  const [fontScale, setFontScale] = useState<FontScale>("base");

  const test = useMemo(
    () =>
      Object.values(writingFiles)
      .map((m) => m.default)
      .filter(isWritingTest)
        .find((file) => file.id === id) ?? null,
    [id],
  );

  useEffect(() => {
    if (!id) {
      return;
    }

    let cancelled = false;
    getWritingSessions()
      .then((sessions) => {
        if (cancelled) return;
        const latest = sessions
          .filter((session) => session.test_id === id)
          .sort(
            (a, b) =>
              new Date(b.completed_at).getTime() - new Date(a.completed_at).getTime(),
          )[0];

        const actionPoints = latest?.grading.action_points?.filter((point) => point.trim()) ?? [];
        setPreviousAttempt(
          latest && actionPoints.length > 0
            ? {
                actionPoints,
              }
            : null,
        );
      })
      .catch(() => {
        if (!cancelled) setPreviousAttempt(null);
      });

    return () => {
      cancelled = true;
    };
  }, [id]);

  const answeredCount = useMemo(() => {
    let count = 0;
    if (answers["1"]?.trim()) count += 1;
    if (answers["2"]?.trim()) count += 1;
    return count;
  }, [answers]);

  async function handleSubmit() {
    if (!test || submitting) return;
    setSubmitting(true);
    setError("");
    const payload = {
      id: `${test.id}-${Date.now()}`,
      test,
      started_at: startedAt,
      completed_at: new Date().toISOString(),
      total_time_ms: Date.now() - startMs,
      answers,
    };

    try {
      const session = await submitWritingSession(payload);
      const synced: WritingSession = { ...session, sync_status: "synced" };
      localStorage.setItem(`ielts_writing_session_${session.id}`, JSON.stringify(synced));
      navigate(`/writing-results/${session.id}`);
    } catch (e) {
      const message = e instanceof Error ? e.message : "Failed to submit writing test.";
      localStorage.setItem(`ielts_writing_session_${payload.id}`, JSON.stringify({
        ...payload,
        test_id: test.id,
        answers_json: buildWritingAnswersJson(test, answers),
        grading: {
          overall_band: 0,
          task_1: {
            band: 0,
            criteria: { task_response: 0, coherence_cohesion: 0, lexical_resource: 0, grammar_accuracy: 0 },
            criterion_evidence: {
              task_response: "Submission failed.",
              coherence_cohesion: "Submission failed.",
              lexical_resource: "Submission failed.",
              grammar_accuracy: "Submission failed.",
            },
            detailed_improvement_points: {
              task_response: [],
              coherence_cohesion: [],
              lexical_resource: [],
              grammar_accuracy: [],
            },
            current_state: "Feedback unavailable because backend grading failed.",
            primary_goal: "Retry submission when backend grading is available.",
            sample_answer: "",
          },
          task_2: {
            band: 0,
            criteria: { task_response: 0, coherence_cohesion: 0, lexical_resource: 0, grammar_accuracy: 0 },
            criterion_evidence: {
              task_response: "Submission failed.",
              coherence_cohesion: "Submission failed.",
              lexical_resource: "Submission failed.",
              grammar_accuracy: "Submission failed.",
            },
            detailed_improvement_points: {
              task_response: [],
              coherence_cohesion: [],
              lexical_resource: [],
              grammar_accuracy: [],
            },
            current_state: "Feedback unavailable because backend grading failed.",
            primary_goal: "Retry submission when backend grading is available.",
            sample_answer: "",
          },
          action_points: ["Retry submission when backend is available."],
        },
        sync_status: "local-only",
        sync_error: message,
      }));
      setError("Saved locally only. Backend grading failed.");
      navigate(`/writing-results/${payload.id}`);
    } finally {
      setSubmitting(false);
    }
  }

  if (!test) return <div className="p-8 text-gray-500">Loading writing test...</div>;

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {submitting && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-gray-950/45 px-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="writing-grading-title"
        >
          <div className="w-full max-w-sm rounded-xl bg-white p-6 text-center shadow-xl">
            <div className="mx-auto mb-4 h-10 w-10 animate-spin rounded-full border-4 border-blue-100 border-t-blue-600" />
            <h2 id="writing-grading-title" className="text-lg font-semibold text-gray-900">
              Grading your writing
            </h2>
            <p className="mt-2 text-sm leading-6 text-gray-600">
              Your Task 1 and Task 2 responses are being reviewed. This usually takes about 3 minutes.
            </p>
            <p className="mt-3 text-xs text-gray-500">
              Keep this tab open while feedback is generated.
            </p>
          </div>
        </div>
      )}
      <div className="border-b border-gray-200 bg-white px-4 md:px-6 py-3">
        <div className="flex items-center justify-between">
          <h1 className="font-semibold text-gray-900 text-sm md:text-base">{test.title}</h1>
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium disabled:opacity-60"
          >
            {submitting ? "Submitting..." : "Submit"}
          </button>
        </div>
      </div>
      <TimerBar
        totalSeconds={test.time_limit_minutes * 60}
        answeredCount={answeredCount}
        totalCount={2}
        paused={submitting}
      />
      {error && <div className="px-4 md:px-6 py-2 text-sm text-amber-700">{error}</div>}
      <div className="grid md:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)] flex-1 min-h-0">
        <div className="overflow-y-auto border-r border-gray-200 bg-white p-4 md:p-6 space-y-6">
          {test.tasks.map((task) => (
            <section key={task.task_number} className="space-y-3">
              <h2 className="text-sm font-semibold uppercase tracking-[0.16em] text-gray-500">Task {task.task_number}</h2>
              <p className="text-gray-900 leading-relaxed whitespace-pre-wrap">{task.prompt}</p>
              {task.image_url && (
                <img
                  src={task.image_url}
                  alt={`Task ${task.task_number} diagram`}
                  className="w-full rounded-lg border border-gray-200"
                />
              )}
              {task.table && task.table.length > 0 && (
                <div className="overflow-x-auto rounded-lg border border-gray-200">
                  <table className="min-w-full divide-y divide-gray-200 text-sm">
                    <thead className="bg-gray-50">
                      <tr>
                        {task.table[0].map((cell, idx) => (
                          <th key={idx} scope="col" className="px-3 py-2 text-left font-semibold text-gray-700">
                            {cell}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200 bg-white">
                      {task.table.slice(1).map((row, rowIdx) => (
                        <tr key={rowIdx}>
                          {row.map((cell, cellIdx) => (
                            <td key={cellIdx} className="px-3 py-2 text-gray-800">
                              {cell}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              <div className="space-y-1">
                {task.instructions.map((item, idx) => (
                  <p key={idx} className="text-sm text-gray-700">{item}</p>
                ))}
              </div>
              <p className="text-xs text-gray-500">Minimum words: {task.min_words}</p>
            </section>
          ))}
        </div>
        <div className="overflow-y-auto p-4 md:p-6 space-y-5">
          {test.tasks.map((task) => {
            const wordCount = countWords(answers[String(task.task_number)] ?? "");
            const taskActionPoints = previousAttempt
              ? getActionPointsForTask(previousAttempt.actionPoints, task.task_number).slice(0, 2)
              : [];

            return (
              <section key={task.task_number} className="space-y-2">
                <div className="flex items-center justify-between gap-3">
                  <label className="text-sm font-medium text-gray-700">Task {task.task_number} answer</label>
                  <p className="rounded-md border border-gray-200 bg-gray-50 px-2 py-1 text-xs font-medium tabular-nums text-gray-700">
                    {wordCount} words
                  </p>
                </div>
                <div className="space-y-2">
                  <textarea
                    value={answers[String(task.task_number)] ?? ""}
                    onChange={(e) => setAnswers((prev) => ({ ...prev, [String(task.task_number)]: e.target.value }))}
                    className="w-full min-h-[220px] rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder={`Write your Task ${task.task_number} response here...`}
                  />
                  <div className="flex justify-end">
                    <p className="text-xs tabular-nums text-gray-500">
                      Minimum {task.min_words} words
                    </p>
                  </div>
                </div>
                {taskActionPoints.length > 0 && (
                  <div className="rounded-md border border-blue-100 bg-blue-50/60 px-2.5 py-2">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-blue-700">
                      Previous feedback
                    </p>
                    <ul className="mt-1 list-disc space-y-0.5 pl-4 text-xs leading-5 text-blue-950">
                      {taskActionPoints.map((point) => (
                        <li key={point}>{point}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </section>
            );
          })}
        </div>
      </div>
    </div>
  );
}
