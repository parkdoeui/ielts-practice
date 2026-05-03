import { useParams, useNavigate } from "react-router";
import type { TestSession } from "../types";

export function ResultsView() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const sessionStr = localStorage.getItem(`ielts_session_${id}`);
  if (!sessionStr) {
    return (
      <div className="max-w-2xl mx-auto py-16 px-4 text-center">
        <p className="text-gray-500">Session not found.</p>
        <button onClick={() => navigate("/")} className="mt-4 text-blue-600 text-sm">← Back to tests</button>
      </div>
    );
  }

  const session: TestSession = JSON.parse(sessionStr);
  const { score, answers } = session;
  const timeTakenMinutes = Math.round(session.total_time_ms / 60000);

  return (
    <div className="max-w-2xl mx-auto py-8 px-4">
      {/* Score summary */}
      <div className="bg-white border border-gray-200 rounded-xl p-6 mb-6">
        <h1 className="text-xl font-bold text-gray-900 mb-4">Test Results</h1>
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
      <div className="space-y-2">
        <h2 className="text-sm font-semibold text-gray-700 mb-3">Answer Review</h2>
        {answers.map((a) => (
          <div
            key={a.question_id}
            className={`flex items-start gap-3 p-3 rounded-lg border ${
              a.is_correct ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"
            }`}
          >
            <span className={`shrink-0 w-7 h-7 flex items-center justify-center rounded-full text-xs font-bold ${
              a.is_correct ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
            }`}>
              {a.question_id}
            </span>
            <div className="text-sm">
              <span className={a.is_correct ? "text-green-700" : "text-red-700"}>
                {a.is_correct ? "✓ Correct" : "✗ Incorrect"}
              </span>
              {!a.is_correct && (
                <span className="text-gray-500 ml-2">
                  Your answer: <span className="font-medium">{a.user_answer || "(blank)"}</span>
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-6 flex gap-3">
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
