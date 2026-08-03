import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router";
import {
  getFullTestSessionById,
  getMockSession,
  getSessionById,
  getWritingSessionById,
} from "../services/api";
import { FULL_TESTS } from "../lib/fullTests";
import { buildFullTestResult } from "../lib/fullTestResults";
import { getSessionFullTest } from "../lib/mockProgress";
import type {
  FullTestSectionResult,
} from "../lib/fullTestResults";
import type { MockSession, SkillName, TestSession, WritingSession } from "../types";

const SKILL_LABELS: Record<SkillName, string> = {
  listening: "Listening",
  reading: "Reading",
  writing: "Writing",
  speaking: "Speaking",
};

function statusText(section: FullTestSectionResult): string {
  if (section.status === "coming-soon") return "Coming soon";
  if (section.status === "not-taken") return "Not taken";
  if (section.status === "grading-unavailable") return "Grading unavailable";
  return "Completed";
}

function SectionResultCard({ section }: { section: FullTestSectionResult }) {
  const unavailable = section.status !== "completed";

  return (
    <article className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">
            {SKILL_LABELS[section.skill]}
          </p>
          {section.band !== null && section.band > 0 ? (
            <p className="mt-1 text-3xl font-bold text-gray-900">
              {section.band.toFixed(1)}
              <span className="ml-1 text-sm font-medium text-gray-500">band</span>
            </p>
          ) : (
            <p className="mt-2 text-sm font-medium text-gray-500">{statusText(section)}</p>
          )}
        </div>
        <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
          unavailable
            ? "bg-gray-100 text-gray-500"
            : "bg-emerald-50 text-emerald-700"
        }`}>
          {statusText(section)}
        </span>
      </div>

      {section.scoreText && (
        <p className="mt-3 text-sm font-medium text-gray-700">{section.scoreText}</p>
      )}

      {section.skill === "writing" && section.task1Band !== null && section.task2Band !== null && (
        <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
          <div className="rounded-lg bg-gray-50 px-3 py-2">
            <p className="text-xs text-gray-500">Task 1</p>
            <p className="font-semibold text-gray-900">Band {section.task1Band.toFixed(1)}</p>
          </div>
          <div className="rounded-lg bg-gray-50 px-3 py-2">
            <p className="text-xs text-gray-500">Task 2</p>
            <p className="font-semibold text-gray-900">Band {section.task2Band.toFixed(1)}</p>
          </div>
        </div>
      )}

      {section.detailPath && (
        <Link
          to={section.detailPath}
          className="mt-4 inline-block text-sm font-semibold text-blue-600 hover:underline"
        >
          {section.skill === "writing" ? "View Writing feedback" : "Review Reading answers"} →
        </Link>
      )}
    </article>
  );
}

export function MockResultsView() {
  const { id } = useParams<{ id: string }>();
  const localMock = useMemo(() => (id ? getMockSession(id) : null), [id]);
  const [restored, setRestored] = useState<{ id: string; session: MockSession | null } | null>(null);
  const [objectiveSessions, setObjectiveSessions] = useState<Record<string, TestSession | null>>({});
  const [writingSession, setWritingSession] = useState<WritingSession | null>(null);
  const [isLoadingMock, setIsLoadingMock] = useState(true);
  const [isLoadingDetails, setIsLoadingDetails] = useState(true);
  const mock = restored && restored.id === id ? restored.session ?? localMock : localMock;

  useEffect(() => {
    if (!id) return;
    let active = true;
    getFullTestSessionById(id)
      .then((session) => {
        if (active) setRestored({ id, session });
      })
      .catch(() => {
        // The local wrapper, when available, remains the offline fallback.
      })
      .finally(() => {
        if (active) setIsLoadingMock(false);
      });
    return () => {
      active = false;
    };
  }, [id]);

  useEffect(() => {
    if (!mock) return;
    let active = true;
    const objectiveSections = mock.sections.filter(
      (section) =>
        (section.skill === "listening" || section.skill === "reading") &&
        section.session_id,
    );
    const writingSection = mock.sections.find((section) => section.skill === "writing");

    Promise.all([
      Promise.all(
        objectiveSections.map(async (section) => [
          section.session_id as string,
          await getSessionById(section.session_id as string).catch(() => null),
        ] as const),
      ),
      writingSection?.session_id
        ? getWritingSessionById(writingSection.session_id).catch(() => null)
        : Promise.resolve(null),
    ])
      .then(([objectiveEntries, writing]) => {
        if (!active) return;
        setObjectiveSessions(Object.fromEntries(objectiveEntries));
        setWritingSession(writing);
      })
      .catch(() => {
        // Wrapper bands still provide a useful combined result without child details.
      })
      .finally(() => {
        if (active) setIsLoadingDetails(false);
      });
    return () => {
      active = false;
    };
  }, [mock]);

  const fullTest = useMemo(
    () => (mock ? getSessionFullTest(mock, FULL_TESTS) : null),
    [mock],
  );
  const result = useMemo(
    () => (mock ? buildFullTestResult(mock, objectiveSessions, writingSession) : null),
    [mock, objectiveSessions, writingSession],
  );

  if (!mock && isLoadingMock) {
    return <div className="mx-auto max-w-3xl px-4 py-12 text-gray-500">Loading Full Test result…</div>;
  }

  if (!mock || !result) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-10 text-center">
        <p className="text-gray-500">This Full Test result could not be found.</p>
        <Link to="/mock" className="mt-4 inline-block text-sm font-medium text-blue-600">
          Back to Full Tests
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <header className="rounded-2xl border border-gray-200 bg-white p-6 text-center shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-gray-400">
          Full Test result
        </p>
        <h1 className="mt-2 text-2xl font-bold text-gray-900">
          {fullTest?.title ?? "Full Test"}
        </h1>
        <p className="mt-1 text-xs capitalize text-gray-500">
          {mock.mode} mode · Started {new Date(mock.started_at).toLocaleDateString()}
        </p>
        <p className="mt-5 text-sm text-gray-500">Overall band</p>
        <p className="text-5xl font-bold text-gray-900">
          {result.overallBand !== null ? result.overallBand.toFixed(1) : "—"}
        </p>
        <span className={`mt-4 inline-flex rounded-full px-3 py-1 text-xs font-semibold ${
          result.completed
            ? "bg-emerald-50 text-emerald-700"
            : "bg-amber-50 text-amber-700"
        }`}>
          {result.completed ? "Full Test completed" : "Full Test in progress"}
        </span>
        <p className="mt-3 text-xs text-amber-600">
          Provisional — Speaking is not available yet and is not included in the overall band.
        </p>
      </header>

      <section className="mt-6" aria-labelledby="section-results-heading">
        <div className="mb-3 flex items-center justify-between gap-4">
          <h2 id="section-results-heading" className="text-lg font-bold text-gray-900">
            Section results
          </h2>
          {isLoadingDetails && <span className="text-xs text-gray-500">Loading score details…</span>}
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          {result.sections.map((section) => (
            <SectionResultCard key={section.skill} section={section} />
          ))}
        </div>
      </section>

      <div className="mt-6 flex flex-wrap gap-3">
        <Link
          to="/mock"
          className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-700"
        >
          Back to Full Tests
        </Link>
        <Link
          to="/"
          className="rounded-lg border border-gray-300 px-5 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          Back home
        </Link>
      </div>
    </div>
  );
}
