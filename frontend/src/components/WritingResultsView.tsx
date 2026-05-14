import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { getStoredWritingSessionById, getWritingSessionById } from "../services/api";
import type {
  WritingSession,
  WritingTask,
  WritingTaskFeedback,
  WritingTest,
} from "../types";

const writingFiles = import.meta.glob<{ default: WritingTest }>(
  "../data/writing-tests/*.json",
  { eager: true },
);

const CHECKLISTS = {
  task_response: {
    label: "Task Achievement / Task Response",
    items: [
      {
        band: 9,
        text: "Requirements fully satisfied; message followed effortlessly; rare lapses in content.",
      },
      {
        band: 8,
        text: "Requirements sufficiently covered; key features skillfully selected and illustrated.",
      },
      {
        band: 7,
        text: "Clear overview/purpose; relevant and accurate; format is appropriate.",
      },
      {
        band: 6,
        text: "Focuses on task; relevant overview attempted; may have some irrelevant or missing detail.",
      },
      {
        band: 5,
        text: "Addresses task but format may be inappropriate; detail is mechanical; lacks a \"big picture\" overview; includes irrelevant or inaccurate material.",
      },
    ],
  },
  coherence_cohesion: {
    label: "Coherence & Cohesion",
    items: [
      {
        band: 9,
        text: "Seamless cohesion; skillful paragraphing; message followed without effort.",
      },
      {
        band: 8,
        text: "Logically sequenced; well-managed cohesion; occasional minor lapses.",
      },
      {
        band: 7,
        text: "Clear progression throughout; variety of cohesive devices used (though some inaccuracies).",
      },
      {
        band: 6,
        text: "Generally coherent with clear progression; cohesive devices may be mechanical or faulty.",
      },
      {
        band: 5,
        text: "Organisation is evident but not wholly logical; sentences are not fluently linked; repetitive due to inadequate use of reference/substitution.",
      },
    ],
  },
  lexical_resource: {
    label: "Lexical Resource",
    items: [
      {
        band: 9,
        text: "Sophisticated and natural use of lexical features; errors are extremely rare.",
      },
      {
        band: 8,
        text: "Fluently used to convey precise meanings; skillful use of uncommon/idiomatic items.",
      },
      {
        band: 7,
        text: "Sufficient flexibility and precision; awareness of style and collocation is evident.",
      },
      {
        band: 6,
        text: "Meaning is clear; restricted range or lack of precision; errors do not impede communication.",
      },
      {
        band: 5,
        text: "Limited/simple vocabulary; frequent lapses in word choice; spelling/formation errors may cause difficulty for the reader.",
      },
    ],
  },
  grammar_accuracy: {
    label: "Grammatical Range & Accuracy",
    items: [
      {
        band: 9,
        text: "Full flexibility and control; punctuation and grammar are used appropriately throughout.",
      },
      {
        band: 8,
        text: "Wide range of structures used accurately; majority of sentences are error-free.",
      },
      {
        band: 7,
        text: "Variety of complex structures; frequent error-free sentences; grammar well-controlled.",
      },
      {
        band: 6,
        text: "Mix of simple and complex forms; limited flexibility; errors rarely impede communication.",
      },
      {
        band: 5,
        text: "Range is limited and repetitive; complex sentences are attempted but tend to be faulty; errors cause difficulty for the reader.",
      },
    ],
  },
} as const;

function isWritingTest(value: unknown): value is WritingTest {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<WritingTest>;
  return typeof candidate.id === "string" && Array.isArray(candidate.tasks);
}

function countWords(value: string): number {
  const words = value.trim().match(/\b[\w'-]+\b/g);
  return words ? words.length : 0;
}

function summarizePrompt(prompt: string): string {
  const normalized = prompt.replace(/\s+/g, " ").trim();
  if (normalized.length <= 180) {
    return normalized;
  }
  return `${normalized.slice(0, 177).trimEnd()}...`;
}

function bandBucket(score: number): number {
  return Math.max(5, Math.min(9, Math.floor(score || 0)));
}

function getLegacyTaskFields(task: WritingTaskFeedback): {
  strengths: string[];
  improvements: string[];
} {
  const candidate = task as WritingTaskFeedback & {
    strengths?: string[];
    improvements?: string[];
  };
  return {
    strengths: candidate.strengths ?? [],
    improvements: candidate.improvements ?? [],
  };
}

function getCriterionEvidence(
  task: WritingTaskFeedback,
  key: keyof WritingTaskFeedback["criterion_evidence"],
): string {
  const direct = task.criterion_evidence?.[key]?.trim();
  if (direct) {
    return direct;
  }

  const legacy = getLegacyTaskFields(task);
  if (key === "task_response") {
    return legacy.strengths[0] ?? "No criterion evidence provided.";
  }
  if (key === "grammar_accuracy") {
    return legacy.improvements[0] ?? "No criterion evidence provided.";
  }
  return "No criterion evidence provided.";
}

function getCurrentState(task: WritingTaskFeedback): string {
  return (
    task.current_state?.trim() ||
    getLegacyTaskFields(task).strengths[0] ||
    "No current-state summary provided."
  );
}

function getPrimaryGoal(task: WritingTaskFeedback, fallbackAction: string): string {
  return (
    task.primary_goal?.trim() ||
    getLegacyTaskFields(task).improvements[0] ||
    fallbackAction ||
    "No primary goal provided."
  );
}

function getDetailedImprovementPoints(
  task: WritingTaskFeedback,
  key: keyof WritingTaskFeedback["detailed_improvement_points"],
): string[] {
  return task.detailed_improvement_points?.[key]?.filter((point) => point.trim()) ?? [];
}

function ChecklistSection({
  label,
  score,
  items,
}: {
  label: string;
  score: number;
  items: ReadonlyArray<{ band: number; text: string }>;
}) {
  const selectedBand = bandBucket(score);

  return (
    <div className="space-y-2 rounded-xl border border-gray-200 bg-gray-50 p-4">
      <h4 className="text-sm font-semibold text-gray-900">{label}</h4>
      <div className="space-y-2 text-sm text-gray-700">
        {items.map((item) => (
          <label key={item.band} className="flex items-start gap-3">
            <input
              type="checkbox"
              checked={item.band === selectedBand}
              readOnly
              className="mt-1 h-4 w-4 rounded border-gray-300 text-blue-600"
            />
            <span>
              <span className="font-medium">Band {item.band}:</span> {item.text}
            </span>
          </label>
        ))}
      </div>
    </div>
  );
}

export function WritingResultsView() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [session, setSession] = useState<WritingSession | null>(null);
  const [loading, setLoading] = useState(true);

  const test = useMemo(
    () =>
      Object.values(writingFiles)
        .map((m) => m.default)
        .filter(isWritingTest)
        .find((file) => file.id === session?.test_id) ?? null,
    [session],
  );

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

  if (loading) {
    return <div className="max-w-5xl mx-auto py-16 px-4 text-gray-500">Loading writing result...</div>;
  }

  if (!session) {
    return (
      <div className="max-w-3xl mx-auto py-16 px-4 text-center">
        <p className="text-gray-500">Writing session not found.</p>
        <button onClick={() => navigate("/writing")} className="mt-4 text-blue-600 text-sm">
          Back to writing tests
        </button>
      </div>
    );
  }

  const taskSections: Array<{
    label: "Task 1" | "Task 2";
    task: WritingTaskFeedback;
    answerKey: "1" | "2";
    taskDef: WritingTask | null;
  }> = [
    {
      label: "Task 1",
      task: session.grading.task_1,
      answerKey: "1",
      taskDef: test?.tasks.find((item) => item.task_number === 1) ?? null,
    },
    {
      label: "Task 2",
      task: session.grading.task_2,
      answerKey: "2",
      taskDef: test?.tasks.find((item) => item.task_number === 2) ?? null,
    },
  ];

  return (
    <div className="max-w-5xl mx-auto py-8 px-4 space-y-6">
      <section className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-500">
          IELTS Writing Evaluation Scorecard
        </p>
        <h1 className="mt-2 text-2xl font-bold text-gray-900">Writing Result</h1>
        <div className="mt-5 grid gap-4 sm:grid-cols-3">
          <div className="rounded-xl bg-blue-50 px-4 py-3">
            <p className="text-xs font-medium uppercase tracking-[0.16em] text-blue-700">Overall Band Score</p>
            <p className="mt-1 text-3xl font-bold text-blue-700">
              {session.grading.overall_band.toFixed(1)}
            </p>
          </div>
          <div className="rounded-xl bg-gray-50 px-4 py-3">
            <p className="text-xs font-medium uppercase tracking-[0.16em] text-gray-500">Task 1 Band</p>
            <p className="mt-1 text-2xl font-bold text-gray-900">
              {session.grading.task_1.band.toFixed(1)}
            </p>
          </div>
          <div className="rounded-xl bg-gray-50 px-4 py-3">
            <p className="text-xs font-medium uppercase tracking-[0.16em] text-gray-500">Task 2 Band</p>
            <p className="mt-1 text-2xl font-bold text-gray-900">
              {session.grading.task_2.band.toFixed(1)}
            </p>
          </div>
        </div>
      </section>

      {taskSections.map(({ label, task, answerKey, taskDef }) => {
        const answer = session.answers[answerKey] ?? "";
        const wordCount = countWords(answer);
        const fallbackAction = session.grading.action_points[0] ?? "";
        const criteriaRows = [
          {
            key: "task_response" as const,
            label: label === "Task 1" ? "Task Achievement" : "Task Response",
            value: task.criteria.task_response,
          },
          {
            key: "coherence_cohesion" as const,
            label: "Coherence & Cohesion",
            value: task.criteria.coherence_cohesion,
          },
          {
            key: "lexical_resource" as const,
            label: "Lexical Resource",
            value: task.criteria.lexical_resource,
          },
          {
            key: "grammar_accuracy" as const,
            label: "Grammatical Range & Accuracy",
            value: task.criteria.grammar_accuracy,
          },
        ];

        return (
          <section key={label} className="space-y-6 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <h2 className="text-xl font-semibold text-gray-900">{label}</h2>
                <p className="text-sm text-gray-600">Band {task.band.toFixed(1)}</p>
              </div>
            </div>

            <div className="grid gap-4 lg:grid-cols-3">
              <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
                <p className="text-xs font-medium uppercase tracking-[0.16em] text-gray-500">
                  Task Type
                </p>
                <p className="mt-1 text-sm font-medium text-gray-900">{label}</p>
              </div>
              <div className="rounded-xl border border-gray-200 bg-gray-50 p-4 lg:col-span-2">
                <p className="text-xs font-medium uppercase tracking-[0.16em] text-gray-500">
                  Prompt Summary
                </p>
                <p className="mt-1 text-sm text-gray-900">
                  {taskDef ? summarizePrompt(taskDef.prompt) : "Prompt summary unavailable."}
                </p>
              </div>
              <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
                <p className="text-xs font-medium uppercase tracking-[0.16em] text-gray-500">
                  Word Count
                </p>
                <p className="mt-1 text-sm font-medium text-gray-900">{wordCount}</p>
              </div>
              <div className="rounded-xl border border-gray-200 bg-gray-50 p-4 lg:col-span-2">
                <p className="text-xs font-medium uppercase tracking-[0.16em] text-gray-500">
                  Your Response
                </p>
                <p className="mt-1 whitespace-pre-wrap text-sm text-gray-800">
                  {answer.trim() || "(blank)"}
                </p>
              </div>
            </div>

            <div className="overflow-x-auto rounded-xl border border-gray-200">
              <table className="min-w-full divide-y divide-gray-200 text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left font-semibold text-gray-700">Criterion</th>
                    <th className="px-4 py-3 text-center font-semibold text-gray-700">Band Score (5-9)</th>
                    <th className="px-4 py-3 text-left font-semibold text-gray-700">
                      Primary Evidence / Key Lapses
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 bg-white">
                  {criteriaRows.map((row) => (
                    <tr key={row.key}>
                      <td className="px-4 py-3 font-medium text-gray-900">{row.label}</td>
                      <td className="px-4 py-3 text-center font-semibold text-gray-900">
                        {row.value.toFixed(1)}
                      </td>
                      <td className="px-4 py-3 text-gray-700">
                        {getCriterionEvidence(task, row.key)}
                      </td>
                    </tr>
                  ))}
                  <tr className="bg-blue-50">
                    <td className="px-4 py-3 font-semibold text-gray-900">OVERALL BAND SCORE</td>
                    <td className="px-4 py-3 text-center font-bold text-blue-700">
                      {task.band.toFixed(1)}
                    </td>
                    <td className="px-4 py-3 text-gray-700">
                      Average of the four component scores as judged for this task.
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-gray-900">Evaluation Checklist (Bands 5-9)</h3>
              <div className="grid gap-4 xl:grid-cols-2">
                <ChecklistSection
                  label={CHECKLISTS.task_response.label}
                  score={task.criteria.task_response}
                  items={CHECKLISTS.task_response.items}
                />
                <ChecklistSection
                  label={CHECKLISTS.coherence_cohesion.label}
                  score={task.criteria.coherence_cohesion}
                  items={CHECKLISTS.coherence_cohesion.items}
                />
                <ChecklistSection
                  label={CHECKLISTS.lexical_resource.label}
                  score={task.criteria.lexical_resource}
                  items={CHECKLISTS.lexical_resource.items}
                />
                <ChecklistSection
                  label={CHECKLISTS.grammar_accuracy.label}
                  score={task.criteria.grammar_accuracy}
                  items={CHECKLISTS.grammar_accuracy.items}
                />
              </div>
            </div>

            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-gray-900">Detailed Improvement Points</h3>
              <div className="grid gap-4 xl:grid-cols-2">
                {criteriaRows.map((row) => {
                  const points = getDetailedImprovementPoints(task, row.key);

                  return (
                    <div key={row.key} className="rounded-xl border border-gray-200 bg-gray-50 p-4">
                      <h4 className="text-sm font-semibold text-gray-900">
                        {CHECKLISTS[row.key].label}
                      </h4>
                      {points.length > 0 ? (
                        <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-gray-700">
                          {points.map((point) => (
                            <li key={point}>{point}</li>
                          ))}
                        </ul>
                      ) : (
                        <p className="mt-3 text-sm text-gray-500">
                          No generated improvement points were saved for this criterion.
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="grid gap-4 lg:grid-cols-2">
              <div className="rounded-xl border border-gray-200 bg-white p-4">
                <p className="text-xs font-medium uppercase tracking-[0.16em] text-gray-500">
                  Current State
                </p>
                <p className="mt-2 text-sm text-gray-800">{getCurrentState(task)}</p>
              </div>
              <div className="rounded-xl border border-blue-200 bg-blue-50 p-4">
                <p className="text-xs font-medium uppercase tracking-[0.16em] text-blue-700">
                  Primary Goal For Next Writing
                </p>
                <p className="mt-2 text-sm text-blue-900">
                  {getPrimaryGoal(task, fallbackAction)}
                </p>
              </div>
            </div>
          </section>
        );
      })}

      {session.grading.action_points.length > 0 && (
        <section className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
          <h3 className="text-sm font-semibold uppercase tracking-[0.16em] text-gray-600">
            Global Next Steps
          </h3>
          <ol className="mt-3 list-decimal space-y-1 pl-5 text-sm text-gray-700">
            {session.grading.action_points.slice(0, 4).map((item, idx) => (
              <li key={`${idx}-${item}`}>{item}</li>
            ))}
          </ol>
        </section>
      )}
    </div>
  );
}
