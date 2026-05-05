import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router";
import { getSessionById } from "../services/api";
import type { ReadingTest, TestSession } from "../types";

const testFiles = import.meta.glob<{ default: ReadingTest }>(
  "../data/tests/*.json",
  { eager: true }
);

function getVisibleSharedText(sharedText?: string) {
  const normalized = sharedText?.trim();
  if (!normalized) {
    return null;
  }

  if (normalized.toLowerCase().startsWith("show answers")) {
    return null;
  }

  return normalized;
}

export function ResultsView() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [session, setSession] = useState<TestSession | null>(null);
  const [loading, setLoading] = useState(true);

  const test = useMemo(
    () => Object.values(testFiles).find((m) => m.default.id === session?.test_id)?.default ?? null,
    [session]
  );

  const reviewItems = useMemo(() => {
    if (!session || !test) {
      return [];
    }

    const answerByQuestionId = new Map(
      session.answers.map((answer) => [answer.question_id, answer])
    );

    return test.question_groups.flatMap((group) =>
      group.questions.map((question) => ({
        group,
        question,
        answer: answerByQuestionId.get(question.id) ?? null,
      }))
    );
  }, [session, test]);

  useEffect(() => {
    const passcode = localStorage.getItem("ielts_passcode") ?? "";
    if (!id || !passcode) {
      setLoading(false);
      return;
    }

    getSessionById(passcode, id)
      .then(setSession)
      .catch(() => setSession(null))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="max-w-2xl mx-auto py-16 px-4 text-center">
        <p className="text-gray-500">Loading result…</p>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="max-w-2xl mx-auto py-16 px-4 text-center">
        <p className="text-gray-500">Session not found on the backend.</p>
        <button onClick={() => navigate("/")} className="mt-4 text-blue-600 text-sm">← Back to tests</button>
      </div>
    );
  }

  const { score } = session;
  const timeTakenMinutes = Math.round(session.total_time_ms / 60000);

  return (
    <div className="max-w-2xl mx-auto py-8 px-4">
      {/* Score summary */}
      <div className="bg-white border border-gray-200 rounded-xl p-6 mb-6">
        <h1 className="text-xl font-bold text-gray-900 mb-4">Test Results</h1>
        {session.sync_status === "local-only" && (
          <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
            Result saved on this device only. Backend sync failed{session.sync_error ? `: ${session.sync_error}` : "."}
          </div>
        )}
        {session.sync_status === "synced" && (
          <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
            Result saved to the backend.
          </div>
        )}
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <div className="text-3xl font-bold text-blue-600">{score.correct}/{score.total}</div>
            <div className="text-xs text-gray-500 mt-1">Correct</div>
          </div>
          <div>
            <div className="text-3xl font-bold text-green-600">{score.band_estimate.toFixed(1)}</div>
            <div className="text-xs text-gray-500 mt-1">Band Estimate</div>
          </div>
          <div>
            <div className="text-3xl font-bold text-gray-700">{timeTakenMinutes}m</div>
            <div className="text-xs text-gray-500 mt-1">Time Taken</div>
          </div>
        </div>
      </div>

      {/* Answer review */}
      <div className="space-y-3">
        <h2 className="text-sm font-semibold text-gray-700 mb-3">Answer Review</h2>
        {reviewItems.map(({ group, question, answer }) => {
          const visibleSharedText = getVisibleSharedText(group.shared_text);
          const isCorrect = answer?.is_correct ?? false;
          const userAnswer = answer?.user_answer?.trim() || "(blank)";

          return (
          <div
            key={question.id}
            className={`flex items-start gap-3 p-3 rounded-lg border ${
              isCorrect ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"
            }`}
          >
            <span className={`shrink-0 w-7 h-7 flex items-center justify-center rounded-full text-xs font-bold ${
              isCorrect ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
            }`}>
              {question.id}
            </span>
            <div className="min-w-0 flex-1 space-y-2 text-sm">
              <div className="flex flex-wrap items-center gap-2">
                <span className={isCorrect ? "text-green-700 font-medium" : "text-red-700 font-medium"}>
                  {isCorrect ? "Correct" : "Incorrect"}
                </span>
                <span className="text-xs uppercase tracking-[0.16em] text-gray-400">
                  {group.type}
                </span>
              </div>

              <div className="space-y-1">
                <p className="text-xs font-medium uppercase tracking-[0.16em] text-gray-500">
                  Instruction
                </p>
                <p className="text-gray-700 whitespace-pre-line">{group.instruction}</p>
              </div>

              {visibleSharedText && (
                <div className="space-y-1">
                  <p className="text-xs font-medium uppercase tracking-[0.16em] text-gray-500">
                    Shared Context
                  </p>
                  <p className="text-gray-700 whitespace-pre-line">{visibleSharedText}</p>
                </div>
              )}

              <div className="space-y-1">
                <p className="text-xs font-medium uppercase tracking-[0.16em] text-gray-500">
                  Question
                </p>
                <p className="text-gray-900 whitespace-pre-line">
                  {question.statement || `Question ${question.id}`}
                </p>
              </div>

              <div className="grid gap-2 sm:grid-cols-2">
                <div className="rounded-lg bg-white/70 px-3 py-2">
                  <p className="text-xs font-medium uppercase tracking-[0.16em] text-gray-500">
                    Your Answer
                  </p>
                  <p className="mt-1 font-medium text-gray-900">{userAnswer}</p>
                </div>
                <div className="rounded-lg bg-white/70 px-3 py-2">
                  <p className="text-xs font-medium uppercase tracking-[0.16em] text-gray-500">
                    Correct Answer
                  </p>
                  <p className="mt-1 font-medium text-gray-900">{question.answer}</p>
                </div>
              </div>
            </div>
          </div>
          );
        })}
      </div>

      <div className="mt-6 flex gap-3">
        <button
          onClick={() => navigate(`/test/${session.test_id}`)}
          className="px-4 py-2 border border-gray-300 text-sm rounded-lg hover:bg-gray-50"
        >
          Review Test
        </button>
        <button onClick={() => navigate("/")} className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700">
          Take Another Test
        </button>
        <button onClick={() => navigate("/progress")} className="px-4 py-2 border border-gray-300 text-sm rounded-lg hover:bg-gray-50">
          View Progress
        </button>
      </div>
    </div>
  );
}
