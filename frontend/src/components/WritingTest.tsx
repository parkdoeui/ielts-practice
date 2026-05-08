import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { submitWritingSession } from "../services/api";
import { TimerBar } from "./TimerBar";
import type { WritingSession, WritingTest as WritingTestType } from "../types";

const writingFiles = import.meta.glob<{ default: WritingTestType }>(
  "../data/writing-tests/*.json",
  { eager: true },
);

function isWritingTest(value: unknown): value is WritingTestType {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<WritingTestType>;
  return typeof candidate.id === "string" && Array.isArray(candidate.tasks);
}

export function WritingTest() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [test, setTest] = useState<WritingTestType | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({ "1": "", "2": "" });
  const [startedAt] = useState(new Date().toISOString());
  const [startMs] = useState(Date.now());
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const found = Object.values(writingFiles)
      .map((m) => m.default)
      .filter(isWritingTest)
      .find((file) => file.id === id);
    setTest(found ?? null);
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
        grading: {
          overall_band: 0,
          task_1: { band: 0, criteria: { task_response: 0, coherence_cohesion: 0, lexical_resource: 0, grammar_accuracy: 0 }, strengths: [], improvements: ["Submission failed."], sample_answer: "" },
          task_2: { band: 0, criteria: { task_response: 0, coherence_cohesion: 0, lexical_resource: 0, grammar_accuracy: 0 }, strengths: [], improvements: ["Submission failed."], sample_answer: "" },
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
        onExpire={handleSubmit}
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
          {test.tasks.map((task) => (
            <section key={task.task_number} className="space-y-2">
              <label className="text-sm font-medium text-gray-700">Task {task.task_number} answer</label>
              <textarea
                value={answers[String(task.task_number)] ?? ""}
                onChange={(e) => setAnswers((prev) => ({ ...prev, [String(task.task_number)]: e.target.value }))}
                className="w-full min-h-[220px] rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder={`Write your Task ${task.task_number} response here...`}
              />
            </section>
          ))}
        </div>
      </div>
    </div>
  );
}
