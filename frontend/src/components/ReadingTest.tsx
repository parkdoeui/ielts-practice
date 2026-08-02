import { useState, useEffect, useCallback, useMemo, type CSSProperties } from "react";
import { useParams, useNavigate } from "react-router";
import type { ReadingTest as ReadingTestType, UserAnswer, TestSession } from "../types";
import { PassagePanel } from "./PassagePanel";
import { QuestionPanel } from "./QuestionPanel";
import { TimerBar } from "./TimerBar";
import { CbtStatusBar, FONT_SCALE_ZOOM, type FontScale } from "./CbtStatusBar";
import { QuestionNavigator, type NavigatorPart } from "./QuestionNavigator";
import { getLatestSessionForTest, saveSession } from "../services/api";
import { estimateBand, isAnswerCorrect } from "../lib/grading";

export interface ReadingSectionResult {
  skill: "reading";
  sessionId: string;
  band: number;
  correct: number;
  total: number;
}

interface ReadingTestProps {
  embeddedTestId?: string;
  onComplete?: (result: ReadingSectionResult) => void;
}

const testFiles = import.meta.glob<{ default: ReadingTestType }>(
  "../data/reading-tests/*.json",
  { eager: true }
);

function isReadingTest(value: unknown): value is ReadingTestType {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Partial<ReadingTestType>;
  return (
    typeof candidate.id === "string" &&
    typeof candidate.title === "string" &&
    Array.isArray(candidate.passages) &&
    Array.isArray(candidate.question_groups)
  );
}

export function ReadingTest({ embeddedTestId, onComplete }: ReadingTestProps = {}) {
  const params = useParams<{ id: string }>();
  const id = embeddedTestId ?? params.id;
  const embedded = Boolean(onComplete);
  const navigate = useNavigate();
  const [test, setTest] = useState<ReadingTestType | null>(null);
  const [currentPassageIndex, setCurrentPassageIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [startedAt] = useState(new Date().toISOString());
  const [startMs] = useState(Date.now());
  const [submitted, setSubmitted] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const [isCheckingCompletion, setIsCheckingCompletion] = useState(true);
  const [reviewSession, setReviewSession] = useState<TestSession | null>(null);
  // Mobile: "passage" | "questions"
  const [mobileView, setMobileView] = useState<"passage" | "questions">("passage");
  // CBT chrome (embedded/mock mode only)
  const [flagged, setFlagged] = useState<Set<number>>(new Set());
  const [currentQuestionId, setCurrentQuestionId] = useState<number | null>(null);
  const [fontScale, setFontScale] = useState<FontScale>("base");

  useEffect(() => {
    const found = Object.values(testFiles)
      .map((m) => m.default)
      .filter(isReadingTest)
      .find((testFile) => testFile.id === id);

    if (found) {
      setTest(found);
    }
  }, [id]);

  useEffect(() => {
    // Embedded (mock) attempts are always fresh — never enter review mode.
    if (embedded) {
      setReviewSession(null);
      setIsCheckingCompletion(false);
      return;
    }

    if (!id) {
      setReviewSession(null);
      setIsCheckingCompletion(false);
      return;
    }

    setIsCheckingCompletion(true);
    getLatestSessionForTest(id)
      .then((latest) => {
        setReviewSession(latest);
        if (latest) {
          setAnswers(
            Object.fromEntries(
              latest.answers.map((answer) => [answer.question_id, answer.user_answer])
            )
          );
        }
      })
      .catch(() => setReviewSession(null))
      .finally(() => setIsCheckingCompletion(false));
  }, [id, embedded]);

  const goToPassage = useCallback((nextIndex: number) => {
    setCurrentPassageIndex(nextIndex);
    setMobileView("questions");
  }, []);

  const handlePrev = useCallback(() => {
    if (!test) return;
    goToPassage(Math.max(currentPassageIndex - 1, 0));
  }, [currentPassageIndex, goToPassage, test]);

  const handleNext = useCallback(() => {
    if (!test) return;
    goToPassage(Math.min(currentPassageIndex + 1, test.passages.length - 1));
  }, [currentPassageIndex, goToPassage, test]);

  const handleSubmit = useCallback(async () => {
    if (!test || submitted || isSaving) return;
    setSubmitted(true);
    setIsSaving(true);
    setSubmitError("");

    const totalTimeMs = Date.now() - startMs;

    // For "choose N" multi-question MC groups, grading is set-based (order doesn't matter).
    // Build a map of question id → is_correct for those groups first.
    const multiMcCorrectById = new Map<number, boolean>();
    for (const group of test.question_groups) {
      const hasPerQuestionOptions = group.questions.some((question) => question.options);
      const isSharedMultiAnswerMc =
        group.type === "multiple-choice" &&
        group.questions.length > 1 &&
        !hasPerQuestionOptions &&
        /\b(choose|which)\s+(two|three|four|five|six|\d+)\b/i.test(
          `${group.instruction}\n${group.shared_text ?? ""}`
        );
      if (isSharedMultiAnswerMc) {
        // Build a frequency map of correct answers for this group
        const correctFreq = new Map<string, number>();
        for (const q of group.questions) {
          const a = q.answer.trim().toLowerCase();
          correctFreq.set(a, (correctFreq.get(a) ?? 0) + 1);
        }
        // Grade each question: correct if its user answer is still available in the correct set
        const usedFreq = new Map<string, number>();
        for (const q of group.questions) {
          const userAnswer = (answers[q.id] ?? "").trim().toLowerCase();
          const available = (correctFreq.get(userAnswer) ?? 0) - (usedFreq.get(userAnswer) ?? 0);
          if (userAnswer && available > 0) {
            multiMcCorrectById.set(q.id, true);
            usedFreq.set(userAnswer, (usedFreq.get(userAnswer) ?? 0) + 1);
          } else {
            multiMcCorrectById.set(q.id, false);
          }
        }
      }
    }

    const questionTypeById = new Map<number, ReadingTestType["question_groups"][number]["type"]>();
    for (const group of test.question_groups) {
      for (const question of group.questions) {
        questionTypeById.set(question.id, group.type);
      }
    }

    // Flatten all questions from all groups for grading
    const allQuestions = test.question_groups.flatMap((g) => g.questions);

    const gradedAnswers: UserAnswer[] = allQuestions.map((q) => {
      const userAnswer = answers[q.id] ?? "";
      const questionType = questionTypeById.get(q.id)!;
      const acceptedAnswers = [q.answer, ...(q.accepted_answers ?? [])];
      const isCorrect = multiMcCorrectById.has(q.id)
        ? multiMcCorrectById.get(q.id)!
        : isAnswerCorrect(questionType, userAnswer, acceptedAnswers);
      return {
        question_id: q.id,
        user_answer: userAnswer,
        is_correct: isCorrect,
        time_spent_ms: 0,
        question_type: questionType,
      };
    });

    const correct = gradedAnswers.filter((a) => a.is_correct).length;
    const total = allQuestions.length;
    const session: TestSession = {
      id: `${id}-${Date.now()}`,
      test_id: test.id,
      started_at: startedAt,
      completed_at: new Date().toISOString(),
      total_time_ms: totalTimeMs,
      answers: gradedAnswers,
      score: { correct, total, band_estimate: estimateBand(correct, total) },
      sync_status: "local-only",
    };

    localStorage.setItem(`ielts_session_${session.id}`, JSON.stringify(session));

    // Reading is graded locally, so the band is valid even if the backend save fails —
    // in embedded (mock) mode we hand control back to the runner either way.
    const sectionResult: ReadingSectionResult = {
      skill: "reading",
      sessionId: session.id,
      band: session.score.band_estimate,
      correct,
      total,
    };

    try {
      await saveSession(session);
      const syncedSession: TestSession = { ...session, sync_status: "synced", sync_error: undefined };
      localStorage.setItem(`ielts_session_${session.id}`, JSON.stringify(syncedSession));
      if (onComplete) {
        onComplete(sectionResult);
        return;
      }
      navigate(`/results/${session.id}`);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to save session to backend.";
      const localOnlySession: TestSession = { ...session, sync_status: "local-only", sync_error: message };
      localStorage.setItem(`ielts_session_${session.id}`, JSON.stringify(localOnlySession));
      if (onComplete) {
        onComplete(sectionResult);
        return;
      }
      setSubmitError("Saved on this device only. Backend sync failed.");
      navigate(`/results/${session.id}`);
    } finally {
      setIsSaving(false);
    }
  }, [test, submitted, isSaving, startMs, answers, id, startedAt, navigate, onComplete]);

  // --- CBT navigator model (embedded/mock mode) ---
  const questionModel = useMemo(() => {
    const orderedIds: number[] = [];
    const parts: NavigatorPart[] = [];
    const passageIndexById = new Map<number, number>();
    if (test) {
      test.passages.forEach((passage, pIdx) => {
        const ids = test.question_groups
          .filter((group) => group.passage_id === passage.id)
          .flatMap((group) => group.questions.map((q) => q.id));
        ids.forEach((qid) => {
          orderedIds.push(qid);
          passageIndexById.set(qid, pIdx);
        });
        parts.push({ label: `Part ${pIdx + 1}`, questionIds: ids });
      });
    }
    return { orderedIds, parts, passageIndexById };
  }, [test]);

  const answeredSet = useMemo(() => {
    const set = new Set<number>();
    for (const [key, value] of Object.entries(answers)) {
      if (value && value.trim()) set.add(Number(key));
    }
    return set;
  }, [answers]);

  // The navigator's "current" follows the visible passage unless the user jumped to a
  // specific question in it — avoids storing a cursor that can drift out of sync.
  const navCurrent = useMemo(() => {
    if (
      currentQuestionId != null &&
      questionModel.passageIndexById.get(currentQuestionId) === currentPassageIndex
    ) {
      return currentQuestionId;
    }
    return questionModel.parts[currentPassageIndex]?.questionIds[0] ?? null;
  }, [currentQuestionId, currentPassageIndex, questionModel]);

  const jumpToQuestion = useCallback(
    (qid: number) => {
      const pIdx = questionModel.passageIndexById.get(qid);
      if (pIdx == null) return;
      setCurrentPassageIndex(pIdx);
      setCurrentQuestionId(qid);
      setMobileView("questions");
    },
    [questionModel],
  );

  const stepQuestion = useCallback(
    (delta: number) => {
      const { orderedIds } = questionModel;
      if (orderedIds.length === 0) return;
      const ref = navCurrent ?? orderedIds[0];
      const idx = orderedIds.indexOf(ref);
      const nextIdx = Math.min(orderedIds.length - 1, Math.max(0, idx + delta));
      jumpToQuestion(orderedIds[nextIdx]);
    },
    [questionModel, navCurrent, jumpToQuestion],
  );

  const toggleFlag = useCallback((qid: number) => {
    setFlagged((prev) => {
      const next = new Set(prev);
      if (next.has(qid)) next.delete(qid);
      else next.add(qid);
      return next;
    });
  }, []);

  useEffect(() => {
    if (!embedded || navCurrent == null) return;
    document
      .getElementById(`question-${navCurrent}`)
      ?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [embedded, navCurrent]);

  if (!test || isCheckingCompletion) {
    return <div className="p-8 text-gray-500">Loading test...</div>;
  }

  const isReviewMode = reviewSession !== null;

  const currentPassageId = test.passages[currentPassageIndex]?.id;
  const groupsForPassage = test.question_groups.filter(
    (g) => g.passage_id === currentPassageId
  );
  const totalQuestions = test.question_groups.reduce((sum, g) => sum + g.questions.length, 0);
  const answeredCount = Object.keys(answers).length;

  return (
    <div className="flex flex-col h-screen">
      {/* Header — CBT status bar when embedded (mock), otherwise the standalone header */}
      {embedded ? (
        <CbtStatusBar
          sectionLabel={`Reading — Part ${currentPassageIndex + 1}`}
          totalSeconds={test.time_limit_minutes * 60}
          paused={submitted}
          fontScale={fontScale}
          onFontScaleChange={setFontScale}
        />
      ) : (
        <div className="border-b border-gray-200 bg-white shrink-0">
          <div className="flex items-center justify-between px-4 md:px-6 py-3">
            <h1 className="font-semibold text-gray-900 text-sm truncate max-w-[60%]">{test.title}</h1>
            <p className="text-xs text-gray-500">
              Passage {currentPassageIndex + 1} of {test.passages.length}
            </p>
          </div>
          {isReviewMode ? (
            <div className="px-4 md:px-6 pb-3">
              <div className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-xs text-blue-800">
                Completed test review. Answers are locked. Open the result page for right and wrong grading.
              </div>
            </div>
          ) : (
            <TimerBar
              totalSeconds={test.time_limit_minutes * 60}
              answeredCount={answeredCount}
              totalCount={totalQuestions}
              paused={submitted}
            />
          )}
        </div>
      )}
      {submitError && (
        <div className="px-4 md:px-6 py-2 text-xs text-amber-700 bg-white border-b border-gray-100 shrink-0">
          {submitError}
        </div>
      )}

      {/* Mobile toggle tabs */}
      <div className="md:hidden flex border-b border-gray-200 bg-white shrink-0">
        <button
          onClick={() => setMobileView("passage")}
          className={`flex-1 py-2 text-sm font-medium transition-colors ${
            mobileView === "passage"
              ? "text-blue-600 border-b-2 border-blue-600"
              : "text-gray-500"
          }`}
        >
          Passage
        </button>
        <button
          onClick={() => setMobileView("questions")}
          className={`flex-1 py-2 text-sm font-medium transition-colors ${
            mobileView === "questions"
              ? "text-blue-600 border-b-2 border-blue-600"
              : "text-gray-500"
          }`}
        >
          Questions ({answeredCount}/{totalQuestions})
        </button>
      </div>

      {/* Main layout */}
      <div
        className="flex flex-1 min-h-0"
        style={embedded ? ({ zoom: FONT_SCALE_ZOOM[fontScale] } as React.CSSProperties) : undefined}
      >
        {/* Passage panel */}
        <div
          className={`
            border-r border-gray-200 flex flex-col min-h-0
            ${mobileView === "passage" ? "flex" : "hidden"}
            md:flex md:w-1/2
            w-full
          `}
        >
          <PassagePanel
            passages={test.passages}
            currentPassageIndex={currentPassageIndex}
            onPassageChange={goToPassage}
          />
        </div>

        {/* Questions panel */}
        <div
          className={`
            flex flex-col min-h-0
            ${mobileView === "questions" ? "flex" : "hidden"}
            md:flex md:w-1/2
            w-full
          `}
        >
          <div className="px-4 md:px-6 py-3 border-b border-gray-100 bg-gray-50 shrink-0">
            <p className="text-xs text-gray-500">
              Passage {currentPassageIndex + 1} — {groupsForPassage.reduce((s, g) => s + g.questions.length, 0)} question{groupsForPassage.reduce((s, g) => s + g.questions.length, 0) !== 1 ? "s" : ""}
            </p>
          </div>
          <div className="flex-1 min-h-0">
            <QuestionPanel
              groups={groupsForPassage}
              answers={answers}
              onAnswer={(qId, answer) => setAnswers((prev) => ({ ...prev, [qId]: answer }))}
              readOnly={isReviewMode}
            />
          </div>
        </div>
      </div>

      {embedded ? (
        <>
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
          <div className="shrink-0 border-t border-gray-200 bg-white px-4 md:px-6 py-2 flex justify-end">
            <button
              onClick={handleSubmit}
              disabled={submitted || isSaving}
              className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {isSaving ? "Saving..." : "Submit section"}
            </button>
          </div>
        </>
      ) : (
        <div className="shrink-0 border-t border-gray-200 bg-white px-4 md:px-6 py-3">
          <div className="flex justify-end gap-2">
            <button
              onClick={handlePrev}
              disabled={currentPassageIndex === 0 || isSaving}
              className="px-3 md:px-4 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
            >
              Prev
            </button>
            <button
              onClick={handleNext}
              disabled={currentPassageIndex === test.passages.length - 1 || isSaving}
              className="px-3 md:px-4 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
            >
              Next
            </button>
            {isReviewMode ? (
              <button
                onClick={() => navigate(`/results/${reviewSession.id}`)}
                className="px-3 md:px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
              >
                View Results
              </button>
            ) : (
              <button
                onClick={handleSubmit}
                disabled={submitted || isSaving}
                className="px-3 md:px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                {isSaving ? "Saving..." : "Submit"}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
