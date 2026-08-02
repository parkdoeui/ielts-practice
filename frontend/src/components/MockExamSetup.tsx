import { useMemo, useState } from "react";
import { useNavigate } from "react-router";
import { saveMockSession } from "../services/api";
import type { MockMode, MockSession, ReadingTest, WritingTest } from "../types";

const readingFiles = import.meta.glob<{ default: ReadingTest }>(
  "../data/reading-tests/*.json",
  { eager: true },
);
const writingFiles = import.meta.glob<{ default: WritingTest }>(
  "../data/writing-tests/*.json",
  { eager: true },
);

function isReadingTest(value: unknown): value is ReadingTest {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<ReadingTest>;
  return (
    typeof candidate.id === "string" &&
    Array.isArray(candidate.passages) &&
    Array.isArray(candidate.question_groups)
  );
}

function isWritingTest(value: unknown): value is WritingTest {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<WritingTest>;
  return typeof candidate.id === "string" && Array.isArray(candidate.tasks);
}

function testNumber(id: string): number {
  const match = id.match(/(\d+)/);
  return match ? Number(match[1]) : Number.MAX_SAFE_INTEGER;
}

const MODES: { value: MockMode; title: string; blurb: string }[] = [
  { value: "relaxed", title: "Relaxed", blurb: "Pause and resume between sections. Per-section timers." },
  { value: "strict", title: "Strict", blurb: "Continuous sitting in exam order — no leaving between sections." },
];

export function MockExamSetup() {
  const navigate = useNavigate();

  const readingTests = useMemo(
    () =>
      Object.values(readingFiles)
        .map((m) => m.default)
        .filter(isReadingTest)
        .sort((a, b) => testNumber(a.id) - testNumber(b.id)),
    [],
  );
  const writingTests = useMemo(
    () =>
      Object.values(writingFiles)
        .map((m) => m.default)
        .filter(isWritingTest)
        .sort((a, b) => testNumber(a.id) - testNumber(b.id)),
    [],
  );

  const [mode, setMode] = useState<MockMode>("relaxed");
  const [readingId, setReadingId] = useState(readingTests[0]?.id ?? "");
  const [writingId, setWritingId] = useState(writingTests[0]?.id ?? "");

  function startMock() {
    const mock: MockSession = {
      id: `mock-${Date.now()}`,
      mode,
      started_at: new Date().toISOString(),
      sections: [
        { skill: "listening", test_id: null, session_id: null, band: null },
        { skill: "reading", test_id: readingId || null, session_id: null, band: null },
        { skill: "writing", test_id: writingId || null, session_id: null, band: null },
        { skill: "speaking", test_id: null, session_id: null, band: null },
      ],
    };
    saveMockSession(mock);
    navigate(`/mock/${mock.id}`);
  }

  const canStart = Boolean(readingId && writingId);

  return (
    <div className="mx-auto max-w-2xl px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Full Test</h1>
        <p className="mt-1 text-sm text-gray-500">
          Sit a mock in exam order — Listening, Reading, Writing, Speaking — and get a combined band.
          Listening &amp; Speaking are coming soon and are skipped for now.
        </p>
      </div>

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

      <section className="mb-6 grid gap-4 sm:grid-cols-2">
        <label className="block">
          <span className="mb-1 block text-sm font-semibold text-gray-700">Reading test</span>
          <select
            value={readingId}
            onChange={(e) => setReadingId(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {readingTests.map((test) => (
              <option key={test.id} value={test.id}>
                {test.title}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="mb-1 block text-sm font-semibold text-gray-700">Writing test</span>
          <select
            value={writingId}
            onChange={(e) => setWritingId(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {writingTests.map((test) => (
              <option key={test.id} value={test.id}>
                {test.title}
              </option>
            ))}
          </select>
        </label>
      </section>

      <ol className="mb-6 space-y-1 text-sm text-gray-600">
        <li>1. Listening — <span className="text-amber-600">coming soon</span></li>
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
