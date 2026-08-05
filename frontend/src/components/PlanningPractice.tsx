import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router";
import { Task1GuideModal } from "./Task1GuideModal";
import { getPlanningSessionById, submitPlanningSession } from "../services/api";
import { clearPlanningDraft, getPlanningDraft, savePlanningDraft, type PlanningDraft } from "../lib/planningDraft";
import { EMPTY_TASK1_PLAN, normalizePlanningPlanForEdit, simplifyTask1Plan } from "../lib/planningPlans";
import { getPlanningClock } from "../lib/planningTimer";
import { getTask1QuestionType } from "../lib/task1QuestionTypes";
import type { PlanningSession, Task1Plan, Task2Plan, WritingPlan, WritingTask, WritingTest } from "../types";

const writingFiles = import.meta.glob<{ default: WritingTest }>(
  "../data/writing-tests/*.json",
  { eager: true },
);

const EMPTY_TASK2: Task2Plan = {
  kind: "task_2",
  introduction: { position: "", roadmap: "" },
  body_1: { main_idea: "", explanation: "", example: "", link_to_position: "" },
  body_2: { main_idea: "", explanation: "", example: "", link_to_position: "" },
  conclusion: { restated_position: "", synthesis: "" },
};

function Field({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  return (
    <label className="block space-y-1.5">
      <span className="text-xs font-semibold uppercase tracking-[0.12em] text-gray-500">{label}</span>
      <textarea
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        rows={2}
        maxLength={1000}
        className="w-full resize-y rounded-lg border border-gray-300 px-3 py-2 text-sm leading-6 text-gray-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
      />
    </label>
  );
}

function VisualPrompt({ task }: { task: WritingTask }) {
  return (
    <div className="space-y-4">
      <p className="whitespace-pre-wrap text-sm leading-7 text-gray-900">{task.prompt}</p>
      {task.image_url && (
        <img src={task.image_url} alt="Task 1 visual" className="w-full rounded-lg border border-gray-200" />
      )}
      {task.table && task.table.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <tbody className="divide-y divide-gray-200">
              {task.table.map((row, rowIndex) => (
                <tr key={rowIndex}>
                  {row.map((cell, cellIndex) => (
                    <td key={cellIndex} className="px-3 py-2 text-gray-800">{cell}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <div className="space-y-1 text-xs leading-5 text-gray-500">
        {task.instructions.map((instruction) => <p key={instruction}>{instruction}</p>)}
      </div>
    </div>
  );
}

function Task1Form({ plan, onChange }: { plan: Task1Plan; onChange: (plan: Task1Plan) => void }) {
  return (
    <section className="space-y-4 rounded-xl border border-gray-200 bg-white p-4">
      <Field label="Introduction note" placeholder="What does the visual show?" value={plan.introduction} onChange={(value) => onChange({ ...plan, introduction: value })} />
      <Field label="Overview — main pattern or change" placeholder="What are the most important overall features?" value={plan.overview} onChange={(value) => onChange({ ...plan, overview: value })} />
      <Field label="Detail paragraph 1 — grouped evidence" placeholder="Which related facts belong together?" value={plan.detail_1} onChange={(value) => onChange({ ...plan, detail_1: value })} />
      <Field label="Detail paragraph 2 — grouped evidence" placeholder="What remaining comparison, area, or stage belongs here?" value={plan.detail_2} onChange={(value) => onChange({ ...plan, detail_2: value })} />
      <p className="text-xs text-gray-500">Four planning notes are enough for a 150-word report. A separate conclusion is not required.</p>
    </section>
  );
}

function Task2Form({ plan, onChange }: { plan: Task2Plan; onChange: (plan: Task2Plan) => void }) {
  const updateBody = (key: "body_1" | "body_2", field: keyof Task2Plan["body_1"], value: string) => {
    onChange({ ...plan, [key]: { ...plan[key], [field]: value } });
  };
  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-blue-100 bg-blue-50/60 p-4">
        <h2 className="mb-3 font-semibold text-gray-900">Introduction</h2>
        <div className="space-y-3">
          <Field label="Position / direct answer" value={plan.introduction.position} onChange={(value) => onChange({ ...plan, introduction: { ...plan.introduction, position: value } })} />
          <Field label="Roadmap" value={plan.introduction.roadmap} onChange={(value) => onChange({ ...plan, introduction: { ...plan.introduction, roadmap: value } })} />
        </div>
      </section>
      {(["body_1", "body_2"] as const).map((key, index) => (
        <section key={key} className="rounded-xl border border-gray-200 bg-white p-4">
          <h2 className="mb-3 font-semibold text-gray-900">Body paragraph {index + 1}</h2>
          <div className="space-y-3">
            <Field label="Main idea" value={plan[key].main_idea} onChange={(value) => updateBody(key, "main_idea", value)} />
            <Field label="Explanation" value={plan[key].explanation} onChange={(value) => updateBody(key, "explanation", value)} />
            <Field label="Example" value={plan[key].example} onChange={(value) => updateBody(key, "example", value)} />
            <Field label="Link to position" value={plan[key].link_to_position} onChange={(value) => updateBody(key, "link_to_position", value)} />
          </div>
        </section>
      ))}
      <section className="rounded-xl border border-gray-200 bg-white p-4">
        <h2 className="mb-3 font-semibold text-gray-900">Conclusion</h2>
        <div className="space-y-3">
          <Field label="Restated position" value={plan.conclusion.restated_position} onChange={(value) => onChange({ ...plan, conclusion: { ...plan.conclusion, restated_position: value } })} />
          <Field label="Synthesis" value={plan.conclusion.synthesis} onChange={(value) => onChange({ ...plan, conclusion: { ...plan.conclusion, synthesis: value } })} />
        </div>
      </section>
    </div>
  );
}

export function PlanningPractice() {
  const { testId, taskNumber: taskNumberParam } = useParams<{ testId: string; taskNumber: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const taskNumber = taskNumberParam === "1" ? 1 : 2;
  const revisionOf = searchParams.get("revisionOf");
  const test = useMemo(
    () => Object.values(writingFiles).map((module) => module.default).find((item) => item.id === testId) ?? null,
    [testId],
  );
  const task = test?.tasks.find((item) => item.task_number === taskNumber) ?? null;
  const [draft, setDraft] = useState<PlanningDraft | null>(null);
  const [previous, setPrevious] = useState<PlanningSession | null>(null);
  const [now, setNow] = useState(() => Date.now());
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [guideOpen, setGuideOpen] = useState(false);

  useEffect(() => {
    if (!testId || !task) return;
    const currentTestId = testId;
    let cancelled = false;
    async function initialize() {
      let parent: PlanningSession | null = null;
      if (revisionOf) {
        parent = await getPlanningSessionById(revisionOf).catch(() => null);
      }
      if (cancelled) return;
      setPrevious(parent);
      const stored = getPlanningDraft(currentTestId, taskNumber, revisionOf);
      const sourcePlan = stored?.plan ?? parent?.plan ?? (taskNumber === 1 ? EMPTY_TASK1_PLAN : EMPTY_TASK2);
      const plan = normalizePlanningPlanForEdit(sourcePlan, taskNumber);
      setDraft(stored
        ? { ...stored, plan }
        : {
            testId: currentTestId,
            taskNumber,
            parentSessionId: revisionOf,
            startedAt: new Date().toISOString(),
            plan,
          });
    }
    void initialize();
    return () => { cancelled = true; };
  }, [revisionOf, task, taskNumber, testId]);

  useEffect(() => {
    if (!draft || submitting) return;
    savePlanningDraft(draft);
  }, [draft, submitting]);

  useEffect(() => {
    const interval = window.setInterval(() => setNow(Date.now()), 250);
    return () => window.clearInterval(interval);
  }, []);

  if (!test || !task || !draft) return <div className="p-8 text-gray-500">Loading planning prompt...</div>;
  const activeTest = test;
  const activeTask = task;
  const activeDraft = draft;
  const clock = getPlanningClock(new Date(activeDraft.startedAt).getTime(), now);
  const plan = activeDraft.plan;
  const task1Type = taskNumber === 1 ? getTask1QuestionType(activeTest.id) : null;

  async function submit() {
    if (submitting) return;
    setSubmitting(true);
    setError("");
    const completedAt = new Date().toISOString();
    const payload = {
      id: `${activeTest.id}-planning-${taskNumber}-${Date.now()}`,
      test_id: activeTest.id,
      task: task1Type ? { ...activeTask, question_type: task1Type } : activeTask,
      parent_session_id: activeDraft.parentSessionId,
      started_at: activeDraft.startedAt,
      completed_at: completedAt,
      total_time_ms: Math.max(0, Date.now() - new Date(activeDraft.startedAt).getTime()),
      plan,
    };
    try {
      const session = await submitPlanningSession(payload);
      clearPlanningDraft(activeDraft.testId, activeDraft.taskNumber, activeDraft.parentSessionId);
      navigate(`/planning-results/${session.id}`);
    } catch (submissionError) {
      setError(submissionError instanceof Error ? submissionError.message : "Could not submit planning session.");
      setSubmitting(false);
    }
  }

  function updatePlan(nextPlan: WritingPlan) {
    setDraft((current) => current ? { ...current, plan: nextPlan } : current);
  }

  return (
    <div className="flex min-h-screen flex-col bg-gray-50">
      <header className="flex items-center justify-between gap-4 border-b border-gray-700 bg-gray-900 px-4 py-3 text-white md:px-6">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold">Writing Test {test.id.match(/(\d+)$/)?.[1]} · Task {taskNumber} Planning</p>
          <p className="text-xs text-gray-300">{revisionOf ? "Revision attempt" : "Idea generation practice"}</p>
        </div>
        <div className="shrink-0 text-center" aria-label={`Elapsed time ${clock.display}`}>
          <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-gray-400">Elapsed</p>
          <p className="font-mono text-lg font-bold tabular-nums text-white">{clock.display}</p>
        </div>
        <button type="button" onClick={() => navigate("/planning")} className="shrink-0 text-sm text-gray-300 hover:text-white">Exit</button>
      </header>
      {previous && (
        <div className="border-b border-blue-100 bg-blue-50 px-4 py-3 text-sm text-blue-950 md:px-6">
          Previous focus: <span className="font-medium">{previous.feedback.next_attempt_focus}</span>
        </div>
      )}
      {error && <div className="border-b border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 md:px-6">{error}</div>}
      <main className="grid flex-1 gap-6 p-4 md:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)] md:p-6">
        <section className="h-fit rounded-xl border border-gray-200 bg-white p-5 md:sticky md:top-4">
          <p className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Prompt</p>
          <VisualPrompt task={task} />
        </section>
        <section className="min-w-0">
          {plan.kind === "task_1"
            ? <Task1Form plan={simplifyTask1Plan(plan)} onChange={updatePlan} />
            : <Task2Form plan={plan} onChange={updatePlan} />}
          <div className="mt-6 flex items-center justify-between gap-4 rounded-xl border border-gray-200 bg-white p-4">
            <p className="text-xs leading-5 text-gray-500">Your notes are graded for ideas and organization, not grammar or vocabulary.</p>
            <button type="button" onClick={() => void submit()} disabled={submitting} className="shrink-0 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60">
              {submitting ? "Grading..." : "Submit plan"}
            </button>
          </div>
        </section>
      </main>
      {task1Type && (
        <>
          <button
            type="button"
            onClick={() => setGuideOpen(true)}
            aria-haspopup="dialog"
            className="fixed bottom-5 right-5 z-40 rounded-full bg-violet-700 px-5 py-3 text-sm font-bold text-white shadow-lg shadow-violet-900/20 hover:bg-violet-800 focus:outline-none focus:ring-4 focus:ring-violet-200"
          >
            Question guide
          </button>
          <Task1GuideModal type={task1Type} open={guideOpen} onClose={() => setGuideOpen(false)} />
        </>
      )}
    </div>
  );
}
