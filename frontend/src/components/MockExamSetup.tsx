import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router";
import { listMockSessions, saveMockSession } from "../services/api";
import {
  IMPLEMENTED_SKILLS,
  type FullTestSet,
  type MockMode,
  type MockSession,
} from "../types";

const fullTestFiles = import.meta.glob<{ default: FullTestSet }>(
  "../data/full-tests/*.json",
  { eager: true },
);

function isFullTestSet(value: unknown): value is FullTestSet {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<FullTestSet>;
  return (
    typeof candidate.id === "string" &&
    typeof candidate.title === "string" &&
    typeof candidate.listening_test_id === "string" &&
    typeof candidate.reading_test_id === "string" &&
    typeof candidate.writing_test_id === "string" &&
    (typeof candidate.speaking_test_id === "string" || candidate.speaking_test_id === null)
  );
}

const MODES: { value: MockMode; title: string; blurb: string }[] = [
  { value: "relaxed", title: "Relaxed", blurb: "Pause and resume between sections. Per-section timers." },
  { value: "strict", title: "Strict", blurb: "Continuous sitting in exam order — no leaving between sections." },
];

export function MockExamSetup() {
  const navigate = useNavigate();

  const fullTests = useMemo(
    () =>
      Object.values(fullTestFiles)
        .map((m) => m.default)
        .filter(isFullTestSet)
        .sort((a, b) => a.title.localeCompare(b.title)),
    [],
  );

  const [mode, setMode] = useState<MockMode>("relaxed");
  const [fullTestId, setFullTestId] = useState(fullTests[0]?.id ?? "");
  const selectedFullTest = fullTests.find((test) => test.id === fullTestId) ?? null;

  const inProgress = useMemo(
    () =>
      listMockSessions().filter((session) =>
        session.sections.some(
          (s) => IMPLEMENTED_SKILLS.has(s.skill) && s.session_id === null,
        ),
      ).slice(0, 1),
    [],
  );

  function startMock() {
    if (!selectedFullTest) return;
    const mock: MockSession = {
      id: `mock-${Date.now()}`,
      mode,
      started_at: new Date().toISOString(),
      sections: [
        { skill: "listening", test_id: selectedFullTest.listening_test_id, session_id: null, band: null },
        { skill: "reading", test_id: selectedFullTest.reading_test_id, session_id: null, band: null },
        { skill: "writing", test_id: selectedFullTest.writing_test_id, session_id: null, band: null },
        { skill: "speaking", test_id: selectedFullTest.speaking_test_id, session_id: null, band: null },
      ],
    };
    saveMockSession(mock);
    navigate(`/mock/${mock.id}`);
  }

  const canStart = selectedFullTest !== null;

  return (
    <div className="mx-auto max-w-2xl px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Full Test</h1>
        <p className="mt-1 text-sm text-gray-500">
          Sit a mock in exam order — Listening, Reading, Writing, Speaking — and get a combined band.
          Speaking is coming soon and is skipped for now.
        </p>
      </div>

      {inProgress.length > 0 && (
        <section className="mb-6">
          <h2 className="mb-2 text-sm font-semibold text-gray-700">Resume</h2>
          <div className="space-y-2">
            {inProgress.map((session) => {
              const done = session.sections.filter(
                (s) => IMPLEMENTED_SKILLS.has(s.skill) && s.session_id !== null,
              ).length;
              const total = session.sections.filter((s) => IMPLEMENTED_SKILLS.has(s.skill)).length;
              return (
                <Link
                  key={session.id}
                  to={`/mock/${session.id}`}
                  className="flex items-center justify-between rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 hover:border-amber-300"
                >
                  <span className="text-sm text-gray-700">
                    In progress · {session.mode} · {done}/{total} sections done
                  </span>
                  <span className="text-sm font-medium text-amber-700">Resume →</span>
                </Link>
              );
            })}
          </div>
        </section>
      )}

      <section className="mb-6">
        <h2 className="mb-2 text-sm font-semibold text-gray-700">Mode</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          {MODES.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => setMode(option.value)}
              className={`rounded-xl border p-4 text-left transition-colors ${
                mode === option.value
                  ? "border-blue-500 bg-blue-50"
                  : "border-gray-200 bg-white hover:border-gray-300"
              }`}
            >
              <p className="font-semibold text-gray-900">{option.title}</p>
              <p className="mt-1 text-xs leading-5 text-gray-500">{option.blurb}</p>
            </button>
          ))}
        </div>
      </section>

      <section className="mb-6 space-y-3">
        <label className="block">
          <span className="mb-1 block text-sm font-semibold text-gray-700">Full Test set</span>
          <select
            value={fullTestId}
            onChange={(e) => setFullTestId(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {fullTests.map((test) => (
              <option key={test.id} value={test.id}>
                {test.title}
              </option>
            ))}
          </select>
        </label>
        {selectedFullTest && (
          <div className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-600">
            <p>Listening: {selectedFullTest.listening_test_id}</p>
            <p>Reading: {selectedFullTest.reading_test_id}</p>
            <p>Writing: {selectedFullTest.writing_test_id}</p>
            <p>Speaking: {selectedFullTest.speaking_test_id ?? "coming soon"}</p>
          </div>
        )}
      </section>

      <ol className="mb-6 space-y-1 text-sm text-gray-600">
        <li>1. Listening</li>
        <li>2. Reading</li>
        <li>3. Writing</li>
        <li>4. Speaking — <span className="text-amber-600">coming soon</span></li>
      </ol>

      <button
        type="button"
        onClick={startMock}
        disabled={!canStart}
        className="rounded-lg bg-blue-600 px-6 py-3 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
      >
        Start Full Test
      </button>
    </div>
  );
}
