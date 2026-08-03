import { useCallback, useMemo, useState, type CSSProperties } from "react";
import { useNavigate, useParams } from "react-router";
import type { ListeningTest as ListeningTestType, TestSession, UserAnswer } from "../types";
import { QuestionPanel } from "./QuestionPanel";
import { QuestionNavigator, type NavigatorPart } from "./QuestionNavigator";
import { CbtStatusBar } from "./CbtStatusBar";
import { FONT_SCALE_ZOOM, type FontScale } from "../lib/fontScale";
import { estimateBand, isAnswerCorrect } from "../lib/grading";
import { saveSession } from "../services/api";

export interface ListeningSectionResult {
  skill: "listening";
  sessionId: string;
  band: number;
  correct: number;
  total: number;
}

interface ListeningTestProps {
  embeddedTestId?: string;
  onComplete?: (result: ListeningSectionResult) => void;
  autoSubmitOnExpire?: boolean;
}

const testFiles = import.meta.glob<{ default: ListeningTestType }>(
  "../data/listening-tests/*.json",
  { eager: true },
);

function isListeningTest(value: unknown): value is ListeningTestType {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<ListeningTestType>;
  return (
    typeof candidate.id === "string" &&
    typeof candidate.title === "string" &&
    typeof candidate.audio_url === "string" &&
    Array.isArray(candidate.parts) &&
    Array.isArray(candidate.question_groups)
  );
}

export function ListeningTest({
  embeddedTestId,
  onComplete,
  autoSubmitOnExpire = false,
}: ListeningTestProps = {}) {
  const params = useParams<{ id: string }>();
  const id = embeddedTestId ?? params.id;
  const embedded = Boolean(onComplete);
  const navigate = useNavigate();
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [submitted, setSubmitted] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const [flagged, setFlagged] = useState<Set<number>>(new Set());
  const [currentQuestionId, setCurrentQuestionId] = useState<number | null>(null);
  const [fontScale, setFontScale] = useState<FontScale>("base");
  const [startedAt] = useState(() => new Date().toISOString());
  const [startMs] = useState(() => Date.now());

  const test = useMemo(() =>
    Object.values(testFiles)
      .map((module) => module.default)
      .filter(isListeningTest)
      .find((testFile) => testFile.id === id) ?? null,
  [id]);

  const partGroups = useMemo(
    () => test?.parts.map((part) => ({ part, groups: test.question_groups.filter((g) => g.passage_id === part.id) })) ?? [],
    [test],
  );

  const questionModel = useMemo(() => {
    const orderedIds: number[] = [];
    const parts: NavigatorPart[] = [];
    const partIndexByQuestion = new Map<number, number>();
    partGroups.forEach(({ part, groups }, index) => {
      const ids = groups.flatMap((group) => group.questions.map((question) => question.id));
      ids.forEach((questionId) => {
        orderedIds.push(questionId);
        partIndexByQuestion.set(questionId, index);
      });
      parts.push({ label: `Part ${part.number}`, questionIds: ids });
    });
    return { orderedIds, parts, partIndexByQuestion };
  }, [partGroups]);

  const navCurrent = currentQuestionId ?? questionModel.orderedIds[0] ?? null;
  const answeredSet = useMemo(
    () => new Set(Object.entries(answers).filter(([, value]) => value.trim()).map(([key]) => Number(key))),
    [answers],
  );

  const jumpToQuestion = useCallback((questionId: number) => {
    setCurrentQuestionId(questionId);
    if (embedded) {
      document.getElementById(`question-${questionId}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [embedded]);

  const stepQuestion = useCallback((delta: number) => {
    const { orderedIds } = questionModel;
    if (!orderedIds.length) return;
    const index = orderedIds.indexOf(navCurrent ?? orderedIds[0]);
    jumpToQuestion(orderedIds[Math.min(orderedIds.length - 1, Math.max(0, index + delta))]);
  }, [jumpToQuestion, navCurrent, questionModel]);

  const toggleFlag = useCallback((questionId: number) => {
    setFlagged((previous) => {
      const next = new Set(previous);
      if (next.has(questionId)) next.delete(questionId);
      else next.add(questionId);
      return next;
    });
  }, []);

  const handleSubmit = useCallback(async () => {
    if (!test || submitted || isSaving) return;
    setSubmitted(true);
    setIsSaving(true);
    setSubmitError("");

    const allQuestions = test.question_groups.flatMap((group) => group.questions);
    const multiMcCorrectById = new Map<number, boolean>();
    for (const group of test.question_groups) {
      const isSharedMultiAnswerMc =
        group.type === "multiple-choice" &&
        group.questions.length > 1 &&
        !group.questions.some((question) => question.options) &&
        /\b(choose|which)\s+(two|three|four|five|six|\d+)\b/i.test(`${group.instruction}\n${group.shared_text ?? ""}`);
      if (!isSharedMultiAnswerMc) continue;
      const correctFreq = new Map<string, number>();
      group.questions.forEach((question) => {
        const answer = question.answer.trim().toLowerCase();
        correctFreq.set(answer, (correctFreq.get(answer) ?? 0) + 1);
      });
      const usedFreq = new Map<string, number>();
      group.questions.forEach((question) => {
        const answer = (answers[question.id] ?? "").trim().toLowerCase();
        const available = (correctFreq.get(answer) ?? 0) - (usedFreq.get(answer) ?? 0);
        multiMcCorrectById.set(question.id, Boolean(answer) && available > 0);
        if (answer && available > 0) usedFreq.set(answer, (usedFreq.get(answer) ?? 0) + 1);
      });
    }

    const gradedAnswers: UserAnswer[] = allQuestions.map((question) => {
      const group = test.question_groups.find((candidate) => candidate.questions.some((item) => item.id === question.id));
      const questionType = group?.type ?? "note-completion";
      const userAnswer = answers[question.id] ?? "";
      const isCorrect = multiMcCorrectById.has(question.id)
        ? multiMcCorrectById.get(question.id)!
        : isAnswerCorrect(questionType, userAnswer, [question.answer, ...(question.accepted_answers ?? [])]);
      return { question_id: question.id, user_answer: userAnswer, is_correct: isCorrect, time_spent_ms: 0, question_type: questionType };
    });
    const correct = gradedAnswers.filter((answer) => answer.is_correct).length;
    const total = gradedAnswers.length;
    const session: TestSession = {
      id: `${test.id}-${Date.now()}`,
      test_id: test.id,
      started_at: startedAt,
      completed_at: new Date().toISOString(),
      total_time_ms: Date.now() - startMs,
      answers: gradedAnswers,
      score: { correct, total, band_estimate: estimateBand(correct, total) },
      sync_status: "local-only",
    };
    localStorage.setItem(`ielts_session_${session.id}`, JSON.stringify(session));
    const result: ListeningSectionResult = { skill: "listening", sessionId: session.id, band: session.score.band_estimate, correct, total };

    try {
      await saveSession(session);
      localStorage.setItem(`ielts_session_${session.id}`, JSON.stringify({ ...session, sync_status: "synced", sync_error: undefined }));
      if (onComplete) onComplete(result);
      else navigate(`/results/${session.id}`);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to save session to backend.";
      localStorage.setItem(`ielts_session_${session.id}`, JSON.stringify({ ...session, sync_error: message }));
      if (onComplete) onComplete(result);
      else {
        setSubmitError("Saved on this device only. Backend sync failed.");
        navigate(`/results/${session.id}`);
      }
    } finally {
      setIsSaving(false);
    }
  }, [answers, isSaving, navigate, onComplete, startMs, startedAt, submitted, test]);

  if (!test) return <div className="p-8 text-gray-500">Listening test unavailable.</div>;

  const totalQuestions = questionModel.orderedIds.length;
  return (
    <div className="flex h-screen flex-col">
      <CbtStatusBar
        sectionLabel="Listening"
        totalSeconds={test.time_limit_minutes * 60}
        paused={submitted}
        onExpire={autoSubmitOnExpire ? handleSubmit : undefined}
        fontScale={fontScale}
        onFontScaleChange={setFontScale}
      />
      {submitError && <div className="shrink-0 border-b border-gray-100 bg-white px-4 py-2 text-xs text-amber-700">{submitError}</div>}
      <div className="flex-1 min-h-0 overflow-y-auto bg-gray-50" style={{ zoom: FONT_SCALE_ZOOM[fontScale] } as CSSProperties}>
        <div className="mx-auto max-w-5xl space-y-5 p-4 md:p-6">
          <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
            <div className="mb-3 flex items-start justify-between gap-3">
              <div>
                <h1 className="text-lg font-semibold text-gray-900">{test.title}</h1>
                <p className="mt-1 text-sm text-gray-600">Listen to the recording, then answer Questions 1–{totalQuestions}.</p>
              </div>
              <span className="shrink-0 rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700">{answeredSet.size}/{totalQuestions} answered</span>
            </div>
            <audio controls preload="metadata" src={test.audio_url} className="w-full" aria-label="Listening test audio" />
          </div>
          {partGroups.map(({ part, groups }) => (
            <section key={part.id} className="rounded-xl border border-gray-200 bg-white shadow-sm">
              <div className="border-b border-gray-100 px-4 py-3">
                <h2 className="font-semibold text-gray-900">Part {part.number}{part.title ? ` — ${part.title}` : ""}</h2>
              </div>
              <QuestionPanel
                groups={groups}
                answers={answers}
                onAnswer={(questionId, answer) => setAnswers((previous) => ({ ...previous, [questionId]: answer }))}
                readOnly={submitted}
              />
            </section>
          ))}
        </div>
      </div>
      <QuestionNavigator
        parts={questionModel.parts}
        answered={answeredSet}
        flagged={flagged}
        current={navCurrent}
        onJump={jumpToQuestion}
        onToggleFlag={toggleFlag}
        onPrev={() => stepQuestion(-1)}
        onNext={() => stepQuestion(1)}
      />
      <div className="flex shrink-0 justify-end border-t border-gray-200 bg-white px-4 py-2 md:px-6">
        <button onClick={handleSubmit} disabled={submitted || isSaving} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:opacity-50">
          {isSaving ? "Saving..." : "Submit section"}
        </button>
      </div>
    </div>
  );
}
