import { useEffect, useState, type ReactNode } from "react";
import { useNavigate, useParams } from "react-router";
import { simplifyTask1Plan } from "../lib/planningPlans";
import { getPlanningSessionById } from "../services/api";
import type { PlanningSession, Task2Plan, WritingPlan } from "../types";

function elapsedLabel(ms: number): string {
  const seconds = Math.round(ms / 1000);
  return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}

function Outline({ plan }: { plan: WritingPlan }) {
  if (plan.kind === "task_1") {
    const task = simplifyTask1Plan(plan);
    return (
      <div className="space-y-4 text-sm leading-6">
        <OutlineSection title="Introduction note"><p>{task.introduction || "—"}</p></OutlineSection>
        <OutlineSection title="Overview"><p>{task.overview || "—"}</p></OutlineSection>
        <OutlineSection title="Detail paragraph 1"><p>{task.detail_1 || "—"}</p></OutlineSection>
        <OutlineSection title="Detail paragraph 2"><p>{task.detail_2 || "—"}</p></OutlineSection>
      </div>
    );
  }
  const task = plan as Task2Plan;
  return (
    <div className="space-y-4 text-sm leading-6">
      <OutlineSection title="Introduction"><p><strong>Position:</strong> {task.introduction.position || "—"}</p><p><strong>Roadmap:</strong> {task.introduction.roadmap || "—"}</p></OutlineSection>
      {[task.body_1, task.body_2].map((body, index) => (
        <OutlineSection key={index} title={`Body paragraph ${index + 1}`}>
          <p><strong>Main idea:</strong> {body.main_idea || "—"}</p>
          <p><strong>Explanation:</strong> {body.explanation || "—"}</p>
          <p><strong>Example:</strong> {body.example || "—"}</p>
          <p><strong>Link:</strong> {body.link_to_position || "—"}</p>
        </OutlineSection>
      ))}
      <OutlineSection title="Conclusion"><p><strong>Restated position:</strong> {task.conclusion.restated_position || "—"}</p><p><strong>Synthesis:</strong> {task.conclusion.synthesis || "—"}</p></OutlineSection>
    </div>
  );
}

function OutlineSection({ title, children }: { title: string; children: ReactNode }) {
  return <section className="rounded-lg border border-gray-200 bg-gray-50 p-3"><h3 className="mb-1 text-xs font-semibold uppercase tracking-[0.12em] text-gray-500">{title}</h3>{children}</section>;
}

export function PlanningResultsView() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [session, setSession] = useState<PlanningSession | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!id) return;
    getPlanningSessionById(id).then(setSession).catch((reason) => setError(reason instanceof Error ? reason.message : "Could not load feedback."));
  }, [id]);

  if (error) return <div className="mx-auto w-full max-w-3xl p-8 text-amber-800">{error}</div>;
  if (!session) return <div className="mx-auto w-full max-w-3xl p-8 text-gray-500">Loading planning feedback...</div>;

  const nextNumber = Number(session.test_id.match(/(\d+)$/)?.[1] ?? 1) % 60 + 1;
  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-8">
      <div className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Planning feedback</p>
          <h1 className="mt-1 text-2xl font-bold text-gray-900">Task {session.task_number} · {session.test_id}</h1>
          <p className="mt-2 text-sm text-gray-500">Completed in {elapsedLabel(session.total_time_ms)}</p>
        </div>
        <div className="rounded-xl border border-blue-100 bg-blue-50 px-5 py-3 text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-blue-700">Estimated planning band</p>
          <p className="mt-1 text-3xl font-bold text-blue-950">{session.feedback.planning_band.toFixed(1)}</p>
          <p className="text-xs text-blue-800">Task Achievement/Response + Coherence & Cohesion</p>
        </div>
      </div>

      <section className="mb-6 rounded-xl border border-gray-200 bg-white p-5">
        <h2 className="text-lg font-semibold text-gray-900">What to work on</h2>
        <p className="mt-2 text-sm leading-7 text-gray-700">{session.feedback.summary}</p>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <FeedbackList title="Keep these ideas" items={session.feedback.relevant_ideas} tone="green" />
          <FeedbackList title="Strengthen these areas" items={session.feedback.missing_or_weak_ideas} tone="amber" />
        </div>
        <div className="mt-4 rounded-lg bg-gray-50 p-4 text-sm leading-6 text-gray-700">
          <p><strong>Organization:</strong> {session.feedback.organization_feedback}</p>
          <p className="mt-2"><strong>Next focus:</strong> {session.feedback.next_attempt_focus}</p>
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-xl border border-gray-200 bg-white p-5">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">Your outline</h2>
          <Outline plan={session.plan} />
        </section>
        <section className="rounded-xl border border-blue-100 bg-blue-50/40 p-5">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">Improved outline</h2>
          <Outline plan={session.feedback.improved_plan} />
        </section>
      </div>

      <section className="mt-6 rounded-xl border border-gray-200 bg-white p-5">
        <div className="grid gap-3 sm:grid-cols-2">
          <Band label={session.task_number === 1 ? "Task Achievement" : "Task Response"} value={session.feedback.task_achievement.band} feedback={session.feedback.task_achievement.feedback} />
          <Band label="Coherence & Cohesion" value={session.feedback.coherence_cohesion.band} feedback={session.feedback.coherence_cohesion.feedback} />
        </div>
        <p className="mt-4 text-xs leading-5 text-gray-500">This is a planning estimate only. It excludes Lexical Resource and Grammatical Range & Accuracy, so it is not a complete Writing band.</p>
      </section>

      <div className="mt-6 flex flex-wrap gap-3">
        <button type="button" onClick={() => navigate(`/planning/${session.test_id}/${session.task_number}?revisionOf=${session.id}`)} className="rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-700">Revise this plan</button>
        <button type="button" onClick={() => navigate(`/planning/${session.test_id.replace(/\d+$/, String(nextNumber))}/${session.task_number}`)} className="rounded-lg border border-gray-300 px-4 py-2.5 text-sm font-semibold text-gray-700 hover:border-blue-400 hover:text-blue-700">Next prompt</button>
        <button type="button" onClick={() => navigate("/planning")} className="rounded-lg border border-gray-300 px-4 py-2.5 text-sm font-semibold text-gray-700 hover:border-blue-400 hover:text-blue-700">Back to planning</button>
      </div>
    </div>
  );
}

function FeedbackList({ title, items, tone }: { title: string; items: string[]; tone: "green" | "amber" }) {
  return (
    <div className={`rounded-lg p-4 ${tone === "green" ? "bg-emerald-50" : "bg-amber-50"}`}>
      <h3 className={`text-sm font-semibold ${tone === "green" ? "text-emerald-900" : "text-amber-900"}`}>{title}</h3>
      <ul className="mt-2 list-disc space-y-1 pl-5 text-sm leading-6 text-gray-700">
        {(items.length ? items : ["No specific notes were returned."]).map((item) => <li key={item}>{item}</li>)}
      </ul>
    </div>
  );
}

function Band({ label, value, feedback }: { label: string; value: number; feedback: string }) {
  return <div className="rounded-lg border border-gray-200 p-4"><div className="flex items-center justify-between gap-3"><h3 className="text-sm font-semibold text-gray-800">{label}</h3><span className="text-xl font-bold text-gray-900">{value.toFixed(1)}</span></div><p className="mt-2 text-sm leading-6 text-gray-600">{feedback}</p></div>;
}
