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

export interface SaveSessionResult {
  saved: boolean;
  conflict: boolean;
}

export function getStoredSessionById(sessionId: string): TestSession | null {
  const raw = localStorage.getItem(`ielts_session_${sessionId}`);
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as TestSession;
  } catch {
    return null;
  }
}

/**
 * POST /api/sessions — persist a completed test session to the backend.
 */
export async function saveSession(session: TestSession): Promise<SaveSessionResult> {
  const res = await fetch(`${API_BASE}/api/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(session),
  });

  if (res.status === 409) {
    return { saved: true, conflict: true };
  }

  if (!res.ok) {
    throw new Error(`POST /api/sessions failed: ${res.status}`);
  }

  return { saved: true, conflict: false };
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

export async function getSessionById(
  passcode: string,
  sessionId: string
): Promise<TestSession | null> {
  const stored = getStoredSessionById(sessionId);
  if (stored && stored.passcode === passcode) {
    return stored;
  }

  const sessions = await getSessions(passcode);
  return sessions.find((session) => session.id === sessionId) ?? null;
}

export async function getLatestSessionForTest(
  passcode: string,
  testId: string
): Promise<TestSession | null> {
  const sessions = await getSessions(passcode);

  return (
    sessions
      .filter((session) => session.test_id === testId)
      .sort(
        (a, b) =>
          new Date(b.completed_at).getTime() - new Date(a.completed_at).getTime()
      )[0] ?? null
  );
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
