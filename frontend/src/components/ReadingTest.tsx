import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router";
import type { ReadingTest as ReadingTestType, UserAnswer, TestSession } from "../types";
import { PassagePanel } from "./PassagePanel";
import { QuestionPanel } from "./QuestionPanel";
import { TimerBar } from "./TimerBar";
import { saveSession } from "../services/api";

const testFiles = import.meta.glob<{ default: ReadingTestType }>(
  "../data/tests/*.json",
  { eager: true }
);

function estimateBand(correct: number, total: number): number {
  const score = Math.round((correct / total) * 40);
  if (score >= 39) return 9.0;
  if (score >= 37) return 8.5;
  if (score >= 35) return 8.0;
  if (score >= 33) return 7.5;
  if (score >= 30) return 7.0;
  if (score >= 27) return 6.5;
  if (score >= 23) return 6.0;
  if (score >= 19) return 5.5;
  if (score >= 15) return 5.0;
  if (score >= 13) return 4.5;
  return 4.0;
}

export function ReadingTest() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [test, setTest] = useState<ReadingTestType | null>(null);
  const [currentPassageIndex, setCurrentPassageIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [startedAt] = useState(new Date().toISOString());
  const [startMs] = useState(Date.now());
  const [submitted, setSubmitted] = useState(false);
  // Mobile: "passage" | "questions"
  const [mobileView, setMobileView] = useState<"passage" | "questions">("passage");

  useEffect(() => {
    const found = Object.values(testFiles).find((m) => m.default.id === id);
    if (found) setTest(found.default);
  }, [id]);

  const handleSubmit = useCallback(() => {
    if (!test || submitted) return;
    setSubmitted(true);

    const totalTimeMs = Date.now() - startMs;
    const passcode = localStorage.getItem("ielts_passcode") ?? "unknown";

    // Flatten all questions from all groups for grading
    const allQuestions = test.question_groups.flatMap((g) => g.questions);

    const gradedAnswers: UserAnswer[] = allQuestions.map((q) => {
      const userAnswer = answers[q.id] ?? "";
      const isCorrect = userAnswer.trim().toLowerCase() === q.answer.trim().toLowerCase();
      return { question_id: q.id, user_answer: userAnswer, is_correct: isCorrect, time_spent_ms: 0 };
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
      passcode,
    };

    localStorage.setItem(`ielts_session_${session.id}`, JSON.stringify(session));
    saveSession(session);
    navigate(`/results/${session.id}`);
  }, [test, submitted, answers, startedAt, startMs, id, navigate]);

  if (!test) return <div className="p-8 text-gray-500">Loading test...</div>;

  const currentPassageId = test.passages[currentPassageIndex]?.id;
  const groupsForPassage = test.question_groups.filter(
    (g) => g.passage_id === currentPassageId
  );
  const totalQuestions = test.question_groups.reduce((sum, g) => sum + g.questions.length, 0);
  const answeredCount = Object.keys(answers).length;

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <div className="flex items-center justify-between px-4 md:px-6 py-3 border-b border-gray-200 bg-white shrink-0">
        <h1 className="font-semibold text-gray-900 text-sm truncate max-w-[60%]">{test.title}</h1>
        <button
          onClick={handleSubmit}
          disabled={submitted}
          className="px-3 md:px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors shrink-0"
        >
          Submit
        </button>
      </div>

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
      <div className="flex flex-1 min-h-0">
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
            onPassageChange={(i) => {
              setCurrentPassageIndex(i);
              setMobileView("questions");
            }}
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
            />
          </div>
        </div>
      </div>

      {/* Timer bar */}
      <div className="shrink-0">
        <TimerBar
          totalSeconds={test.time_limit_minutes * 60}
          answeredCount={answeredCount}
          totalCount={totalQuestions}
          onExpire={handleSubmit}
          paused={submitted}
        />
      </div>
    </div>
  );
}
