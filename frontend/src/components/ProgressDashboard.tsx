import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import type {
  ProgressData,
  ScoreHistory,
  WritingProgressData,
  WritingScoreHistory,
} from "../services/api";
import { getProgress, getWritingSessions } from "../services/api";
import type { WritingSession } from "../types";

type ProgressTab = "reading" | "writing";

const EMPTY_READING_PROGRESS: ProgressData = {
  total_tests: 0,
  average_band: 0,
  best_band: 0,
  score_history: [],
  per_type_accuracy: [],
};

const EMPTY_WRITING_PROGRESS: WritingProgressData = {
  total_tests: 0,
  average_band: 0,
  best_band: 0,
  score_history: [],
};

function bandColor(band: number): string {
  if (band >= 8) return "#10b981"; // green
  if (band >= 6.5) return "#3b82f6"; // blue
  if (band >= 5) return "#f59e0b"; // amber
  return "#ef4444"; // red
}

function bandLabel(band: number): string {
  if (band >= 8.5) return "Expert";
  if (band >= 7) return "Good";
  if (band >= 5.5) return "Competent";
  return "Developing";
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatQType(type: string): string {
  const labels: Record<string, string> = {
    "true-false-ng": "True / False / NG",
    "multiple-choice": "Multiple Choice",
    "multiple-choice-multi": "Multi-Answer MC",
    "matching-headings": "Matching Headings",
    "matching-information": "Matching Info",
    "sentence-completion": "Sentence Completion",
    "summary-completion": "Summary Completion",
    "note-completion": "Note Completion",
    "diagram-labeling": "Diagram Labeling",
    unknown: "Other",
  };
  return labels[type] ?? type;
}

function buildWritingProgress(sessions: WritingSession[]): WritingProgressData {
  if (sessions.length === 0) {
    return EMPTY_WRITING_PROGRESS;
  }

  const sorted = [...sessions].sort(
    (a, b) => new Date(a.completed_at).getTime() - new Date(b.completed_at).getTime(),
  );
  const bands = sorted.map((session) => session.grading.overall_band);
  const totalBand = bands.reduce((sum, band) => sum + band, 0);

  return {
    total_tests: sorted.length,
    average_band: roundBand(totalBand / sorted.length),
    best_band: Math.max(...bands),
    score_history: sorted.map((session) => ({
      date: session.completed_at,
      test_id: session.test_id,
      band: session.grading.overall_band,
    })),
  };
}

function roundBand(value: number): number {
  return Math.round(value * 100) / 100;
}

function isReadingScoreHistory(
  entry: ScoreHistory | WritingScoreHistory,
): entry is ScoreHistory {
  return "correct" in entry && "total" in entry;
}

export function ProgressDashboard() {
  const navigate = useNavigate();
  const [tab, setTab] = useState<ProgressTab>("reading");
  const [readingProgress, setReadingProgress] = useState<ProgressData>(EMPTY_READING_PROGRESS);
  const [writingProgress, setWritingProgress] = useState<WritingProgressData>(EMPTY_WRITING_PROGRESS);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadProgress() {
      const [readingResult, writingResult] = await Promise.allSettled([
        getProgress(),
        getWritingSessions(),
      ]);

      setReadingProgress(
        readingResult.status === "fulfilled"
          ? readingResult.value
          : EMPTY_READING_PROGRESS,
      );
      setWritingProgress(
        writingResult.status === "fulfilled"
          ? buildWritingProgress(writingResult.value)
          : EMPTY_WRITING_PROGRESS,
      );
      setLoading(false);
    }

    loadProgress();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="text-gray-400 text-sm animate-pulse">
          Loading progress…
        </div>
      </div>
    );
  }

  const totalTaken = readingProgress.total_tests + writingProgress.total_tests;
  const activeProgress = tab === "reading" ? readingProgress : writingProgress;

  if (totalTaken === 0) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-gray-50 px-4">
        <div className="text-5xl mb-4">📊</div>
        <h1 className="text-xl font-semibold text-gray-800 mb-2">
          No tests yet
        </h1>
        <p className="text-gray-500 text-sm mb-6">
          Take your first reading or writing test to see your progress here.
        </p>
        <div className="flex gap-3">
          <button
            onClick={() => navigate("/")}
            className="px-5 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
          >
            Reading tests
          </button>
          <button
            onClick={() => navigate("/writing")}
            className="px-5 py-2 border border-gray-200 bg-white text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition-colors"
          >
            Writing tests
          </button>
        </div>
      </div>
    );
  }

  const maxBand = 9;

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-10">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              Progress Dashboard
            </h1>
            <p className="text-sm text-gray-400 mt-0.5">
              Synced from backend · {totalTaken} total test
              {totalTaken !== 1 ? "s" : ""} taken
            </p>
          </div>
          <button
            onClick={() => navigate("/")}
            className="px-4 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-white transition-colors"
          >
            ← Tests
          </button>
        </div>

        <div className="flex gap-2 mb-6 rounded-xl bg-gray-100 p-1 w-full sm:w-fit">
          <button
            onClick={() => setTab("reading")}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
              tab === "reading"
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            Reading ({readingProgress.total_tests})
          </button>
          <button
            onClick={() => setTab("writing")}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
              tab === "writing"
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            Writing ({writingProgress.total_tests})
          </button>
        </div>

        {activeProgress.total_tests === 0 ? (
          <div className="bg-white border border-gray-100 rounded-xl p-6 text-sm text-gray-500 shadow-sm">
            {tab === "reading"
              ? "No reading tests completed yet."
              : "No writing tests completed yet."}
          </div>
        ) : (
          <>
        {/* Stat cards */}
        <div className="grid grid-cols-3 gap-4 mb-8">
          <div className="bg-white rounded-xl border border-gray-100 p-5 text-center shadow-sm">
            <div className="text-3xl font-bold text-gray-900">
              {activeProgress.total_tests}
            </div>
            <div className="text-xs text-gray-400 mt-1 uppercase tracking-wide">
              Tests Taken
            </div>
          </div>
          <div
            className="bg-white rounded-xl border border-gray-100 p-5 text-center shadow-sm"
          >
            <div
              className="text-3xl font-bold"
              style={{ color: bandColor(activeProgress.average_band) }}
            >
              {activeProgress.average_band.toFixed(1)}
            </div>
            <div className="text-xs text-gray-400 mt-1 uppercase tracking-wide">
              Avg Band
            </div>
          </div>
          <div
            className="bg-white rounded-xl border border-gray-100 p-5 text-center shadow-sm"
          >
            <div
              className="text-3xl font-bold"
              style={{ color: bandColor(activeProgress.best_band) }}
            >
              {activeProgress.best_band.toFixed(1)}
            </div>
            <div className="text-xs text-gray-400 mt-1 uppercase tracking-wide">
              Best Band · {bandLabel(activeProgress.best_band)}
            </div>
          </div>
        </div>

        {/* Score history */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm mb-6">
          <div className="px-6 py-4 border-b border-gray-50">
            <h2 className="font-semibold text-gray-800 text-sm">
              {tab === "reading" ? "Reading Score History" : "Writing Band History"}
            </h2>
          </div>
          <div className="divide-y divide-gray-50">
            {activeProgress.score_history.map((entry, i) => (
              <div
                key={i}
                className="flex items-center justify-between px-6 py-3 hover:bg-gray-50 transition-colors"
              >
                <div>
                  <div className="text-sm font-medium text-gray-800">
                    {entry.test_id}
                  </div>
                  <div className="text-xs text-gray-400">
                    {formatDate(entry.date)}
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  {isReadingScoreHistory(entry) && (
                    <>
                      <div className="w-24 h-2 bg-gray-100 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all"
                          style={{
                            width: `${(entry.correct / entry.total) * 100}%`,
                            backgroundColor: bandColor(entry.band),
                          }}
                        />
                      </div>
                      <div className="text-xs text-gray-500 w-16 text-right">
                        {entry.correct}/{entry.total}
                      </div>
                    </>
                  )}
                  <div
                    className="text-sm font-bold w-10 text-right"
                    style={{ color: bandColor(entry.band) }}
                  >
                    {entry.band.toFixed(1)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Band gauge */}
        {activeProgress.score_history.length > 0 && (
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm mb-6 px-6 py-5">
            <h2 className="font-semibold text-gray-800 text-sm mb-4">
              Band Trend
            </h2>
            <div className="flex items-end gap-2 h-20">
              {activeProgress.score_history.map((entry, i) => (
                <div
                  key={i}
                  className="flex-1 flex flex-col items-center gap-1"
                  title={`${entry.test_id}: Band ${entry.band}`}
                >
                  <div
                    className="w-full rounded-t-md transition-all"
                    style={{
                      height: `${(entry.band / maxBand) * 80}px`,
                      backgroundColor: bandColor(entry.band),
                      opacity: 0.85,
                    }}
                  />
                  <span className="text-[10px] text-gray-400">
                    {entry.band.toFixed(1)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Per-type accuracy (only if backend data has it) */}
        {tab === "reading" && readingProgress.per_type_accuracy.length > 0 && (
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm">
            <div className="px-6 py-4 border-b border-gray-50">
              <h2 className="font-semibold text-gray-800 text-sm">
                Accuracy by Question Type
              </h2>
            </div>
            <div className="divide-y divide-gray-50">
              {readingProgress.per_type_accuracy.map((item, i) => (
                <div
                  key={i}
                  className="flex items-center gap-4 px-6 py-3"
                >
                  <div className="flex-1 text-sm text-gray-700">
                    {formatQType(item.question_type)}
                  </div>
                  <div className="w-32 h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${item.accuracy}%`,
                        backgroundColor: bandColor(
                          (item.accuracy / 100) * 9
                        ),
                      }}
                    />
                  </div>
                  <div className="text-xs text-gray-500 w-20 text-right">
                    {item.correct}/{item.total} · {item.accuracy}%
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
          </>
        )}
      </div>
    </div>
  );
}
