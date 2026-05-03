import type { TestSession } from "../types";

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface ScoreHistory {
  date: string;
  test_id: string;
  band: number;
  correct: number;
  total: number;
}

export interface QuestionTypeBreakdown {
  question_type: string;
  correct: number;
  total: number;
  accuracy: number;
}

export interface ProgressData {
  total_tests: number;
  average_band: number;
  best_band: number;
  score_history: ScoreHistory[];
  per_type_accuracy: QuestionTypeBreakdown[];
}

/**
 * POST /api/sessions — persist a completed test session to the backend.
 * Fails silently if the backend is unreachable (results are already in localStorage).
 */
export async function saveSession(session: TestSession): Promise<void> {
  try {
    const res = await fetch(`${API_BASE}/api/sessions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(session),
    });
    if (!res.ok && res.status !== 409) {
      console.warn("Failed to save session to backend:", res.status);
    }
  } catch (err) {
    console.warn("Backend unreachable — session saved to localStorage only:", err);
  }
}

/**
 * GET /api/sessions — fetch all sessions for a given passcode.
 */
export async function getSessions(passcode: string): Promise<TestSession[]> {
  const res = await fetch(
    `${API_BASE}/api/sessions?passcode=${encodeURIComponent(passcode)}`
  );
  if (!res.ok) throw new Error(`GET /api/sessions failed: ${res.status}`);
  return res.json();
}

/**
 * GET /api/progress — fetch aggregated progress stats for a passcode.
 */
export async function getProgress(passcode: string): Promise<ProgressData> {
  const res = await fetch(
    `${API_BASE}/api/progress?passcode=${encodeURIComponent(passcode)}`
  );
  if (!res.ok) throw new Error(`GET /api/progress failed: ${res.status}`);
  return res.json();
}
