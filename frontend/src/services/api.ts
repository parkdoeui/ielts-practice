import type { MockSession, TestSession, WritingSession, WritingTest } from "../types";

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const FETCH_OPTS: RequestInit = { credentials: "include" };
const PASSCODE_STORAGE_KEY = "ielts_passcode";

export interface AuthSession {
  authenticated: boolean;
}

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

export interface WritingScoreHistory {
  date: string;
  test_id: string;
  band: number;
}

export interface WritingProgressData {
  total_tests: number;
  average_band: number;
  best_band: number;
  score_history: WritingScoreHistory[];
}

export interface SaveSessionResult {
  saved: boolean;
  conflict: boolean;
}

export interface WritingSubmitPayload {
  id: string;
  test: WritingTest;
  started_at: string;
  completed_at: string;
  total_time_ms: number;
  answers: Record<string, string>;
}

export function getStoredSessionById(sessionId: string): TestSession | null {
  const raw = localStorage.getItem(`ielts_session_${sessionId}`);
  if (!raw) {
    return null;
  }

  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object") return null;

    // Back-compat: older cached sessions included `passcode`; we intentionally ignore it.
    const candidate = parsed as Record<string, unknown>;
    if ("passcode" in candidate) {
      const { passcode: _ignored, ...rest } = candidate;
      return rest as unknown as TestSession;
    }
    return parsed as TestSession;
  } catch {
    return null;
  }
}

function storePasscode(passcode: string): void {
  localStorage.setItem(PASSCODE_STORAGE_KEY, passcode);
}

function getStoredPasscode(): string | null {
  return localStorage.getItem(PASSCODE_STORAGE_KEY);
}

function authHeaders(extra?: HeadersInit): HeadersInit {
  const headers = new Headers(extra);
  const passcode = getStoredPasscode();
  if (passcode) {
    headers.set("X-IELTS-Passcode", passcode);
  }
  return headers;
}

export async function login(passcode: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    ...FETCH_OPTS,
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ passcode }),
  });
  if (!res.ok) {
    throw new Error(`POST /api/auth/login failed: ${res.status}`);
  }
  storePasscode(passcode);
}

export async function getAuthSession(): Promise<AuthSession> {
  const res = await fetch(`${API_BASE}/api/auth/session`, {
    ...FETCH_OPTS,
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`GET /api/auth/session failed: ${res.status}`);
  return res.json();
}

/**
 * POST /api/sessions — persist a completed test session to the backend.
 */
export async function saveSession(session: TestSession): Promise<SaveSessionResult> {
  const res = await fetch(`${API_BASE}/api/sessions`, {
    ...FETCH_OPTS,
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
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

export async function updateSession(session: TestSession): Promise<TestSession> {
  const res = await fetch(`${API_BASE}/api/sessions/${encodeURIComponent(session.id)}`, {
    ...FETCH_OPTS,
    method: "PUT",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(session),
  });

  if (!res.ok) {
    throw new Error(`PUT /api/sessions/${session.id} failed: ${res.status}`);
  }

  return res.json();
}

/**
 * GET /api/sessions — fetch all sessions for the authenticated user (cookie auth).
 */
export async function getSessions(): Promise<TestSession[]> {
  const res = await fetch(`${API_BASE}/api/sessions`, {
    ...FETCH_OPTS,
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`GET /api/sessions failed: ${res.status}`);
  return res.json();
}

export async function getSessionById(sessionId: string): Promise<TestSession | null> {
  const stored = getStoredSessionById(sessionId);
  if (stored) {
    return stored;
  }

  const sessions = await getSessions();
  return sessions.find((session) => session.id === sessionId) ?? null;
}

export async function getLatestSessionForTest(
  testId: string
): Promise<TestSession | null> {
  const sessions = await getSessions();

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
 * GET /api/progress — fetch aggregated progress stats for the authenticated user (cookie auth).
 */
export async function getProgress(): Promise<ProgressData> {
  const res = await fetch(`${API_BASE}/api/progress`, {
    ...FETCH_OPTS,
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`GET /api/progress failed: ${res.status}`);
  return res.json();
}

// ---- Full Test (Mock Exam) wrapper — localStorage only this iteration ----
// The child reading/writing sessions still persist to the backend; only the grouping
// wrapper lives locally. Mirrors the localStorage-first pattern of getStoredSessionById.

const mockSessionKey = (mockId: string) => `ielts_mock_session_${mockId}`;

export function saveMockSession(mock: MockSession): void {
  localStorage.setItem(mockSessionKey(mock.id), JSON.stringify(mock));
}

export function getMockSession(mockId: string): MockSession | null {
  const raw = localStorage.getItem(mockSessionKey(mockId));
  if (!raw) return null;
  try {
    return JSON.parse(raw) as MockSession;
  } catch {
    return null;
  }
}

export function getStoredWritingSessionById(sessionId: string): WritingSession | null {
  const raw = localStorage.getItem(`ielts_writing_session_${sessionId}`);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as WritingSession;
  } catch {
    return null;
  }
}

export async function submitWritingSession(payload: WritingSubmitPayload): Promise<WritingSession> {
  const res = await fetch(`${API_BASE}/api/writing-sessions`, {
    ...FETCH_OPTS,
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error(`POST /api/writing-sessions failed: ${res.status}`);
  }
  return res.json();
}

export async function getWritingSessions(): Promise<WritingSession[]> {
  const res = await fetch(`${API_BASE}/api/writing-sessions`, {
    ...FETCH_OPTS,
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`GET /api/writing-sessions failed: ${res.status}`);
  return res.json();
}

export async function getWritingSessionById(sessionId: string): Promise<WritingSession | null> {
  const stored = getStoredWritingSessionById(sessionId);
  if (stored) return stored;
  const res = await fetch(`${API_BASE}/api/writing-sessions/${encodeURIComponent(sessionId)}`, {
    ...FETCH_OPTS,
    headers: authHeaders(),
  });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`GET /api/writing-sessions/${sessionId} failed: ${res.status}`);
  return res.json();
}
