import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { getStoredWritingSessionById, getWritingSessionById } from "../services/api";
import type { WritingSession, WritingTaskFeedback } from "../types";

function Criterion({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-gray-600">{label}</span>
      <span className="font-semibold text-gray-900">{value.toFixed(1)}</span>
    </div>
  );
}

export function WritingResultsView() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [session, setSession] = useState<WritingSession | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) {
      setLoading(false);
      return;
    }
    const local = getStoredWritingSessionById(id);
    if (local) {
      setSession(local);
      setLoading(false);
      return;
    }
    getWritingSessionById(id)
      .then(setSession)
      .catch(() => setSession(null))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="max-w-3xl mx-auto py-16 px-4 text-gray-500">Loading writing result...</div>;
  if (!session) {
    return (
      <div className="max-w-3xl mx-auto py-16 px-4 text-center">
        <p className="text-gray-500">Writing session not found.</p>
        <button onClick={() => navigate("/writing")} className="mt-4 text-blue-600 text-sm">Back to writing tests</button>
      </div>
    );
  }

  const taskSections: Array<{ label: "Task 1" | "Task 2"; task: WritingTaskFeedback; answerKey: "1" | "2" }> = [
    { label: "Task 1", task: session.grading.task_1, answerKey: "1" },
    { label: "Task 2", task: session.grading.task_2, answerKey: "2" },
  ];

  return (
    <div className="max-w-3xl mx-auto py-8 px-4 space-y-6">
      <section className="bg-white rounded-xl border border-gray-200 p-6">
        <h1 className="text-xl font-bold text-gray-900 mb-3">Writing Result</h1>
        <p className="text-sm text-gray-600 mb-2">Overall band</p>
        <p className="text-3xl font-bold text-blue-600">{session.grading.overall_band.toFixed(1)}</p>
      </section>

      {taskSections.map(({ label, task, answerKey }) => (
        <section key={label} className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">{label}</h2>
            <p className="text-sm text-gray-600">Band {task.band.toFixed(1)}</p>
          </div>
          <div className="grid sm:grid-cols-2 gap-3">
            <Criterion label="Task response" value={task.criteria.task_response} />
            <Criterion label="Coherence and cohesion" value={task.criteria.coherence_cohesion} />
            <Criterion label="Lexical resource" value={task.criteria.lexical_resource} />
            <Criterion label="Grammar accuracy" value={task.criteria.grammar_accuracy} />
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.16em] text-gray-500 mb-1">Your answer</p>
            <p className="text-sm text-gray-800 whitespace-pre-wrap">{session.answers[answerKey] ?? "(blank)"}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.16em] text-gray-500 mb-1">Sample answer</p>
            <p className="text-sm text-gray-700 whitespace-pre-wrap">{task.sample_answer || "(not provided)"}</p>
          </div>
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.16em] text-gray-500 mb-1">What you did well</p>
              <ul className="text-sm text-gray-700 list-disc ml-5 space-y-1">
                {task.strengths.length ? task.strengths.map((item: string, idx: number) => <li key={idx}>{item}</li>) : <li>No strengths provided.</li>}
              </ul>
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.16em] text-gray-500 mb-1">Needs improvement</p>
              <ul className="text-sm text-gray-700 list-disc ml-5 space-y-1">
                {task.improvements.length ? task.improvements.map((item: string, idx: number) => <li key={idx}>{item}</li>) : <li>No improvements provided.</li>}
              </ul>
            </div>
          </div>
        </section>
      ))}

      <section className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-sm font-semibold uppercase tracking-[0.16em] text-gray-600 mb-2">Action points for next mock test</h3>
        <ol className="text-sm text-gray-700 list-decimal ml-5 space-y-1">
          {session.grading.action_points.slice(0, 4).map((item, idx) => (
            <li key={idx}>{item}</li>
          ))}
        </ol>
      </section>
    </div>
  );
}
