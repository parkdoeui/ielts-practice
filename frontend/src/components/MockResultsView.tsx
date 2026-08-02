import { useMemo } from "react";
import { Link, useParams } from "react-router";
import { getMockSession } from "../services/api";
import { roundToOverallBand } from "../lib/grading";
import { isMockSectionComingSoon, type MockSection, type SkillName } from "../types";

const skillLabel = (skill: SkillName) => skill.charAt(0).toUpperCase() + skill.slice(1);

function sectionResultLink(section: MockSection): string | null {
  if (!section.session_id) return null;
  if (section.skill === "reading") return `/results/${section.session_id}`;
  if (section.skill === "writing") return `/writing-results/${section.session_id}`;
  return null;
}

function statusFor(section: MockSection): { text: string; tone: "band" | "muted" | "warn" } {
  if (isMockSectionComingSoon(section)) return { text: "Coming soon", tone: "muted" };
  if (section.session_id === null) return { text: "Not taken", tone: "muted" };
  if (section.band === null || section.band <= 0) return { text: "Grading unavailable", tone: "warn" };
  return { text: `Band ${section.band.toFixed(1)}`, tone: "band" };
}

export function MockResultsView() {
  const { id } = useParams<{ id: string }>();
  const mock = useMemo(() => (id ? getMockSession(id) : null), [id]);

  const overall = useMemo(() => {
    if (!mock) return null;
    const bands = mock.sections
      .filter((s) => !isMockSectionComingSoon(s) && s.band !== null && s.band > 0)
      .map((s) => s.band as number);
    return roundToOverallBand(bands);
  }, [mock]);

  const hasComingSoon = useMemo(
    () => (mock ? mock.sections.some(isMockSectionComingSoon) : false),
    [mock],
  );

  if (!mock) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-10 text-center">
        <p className="text-gray-500">This full-test result was not found on this device.</p>
        <Link to="/mock" className="mt-4 inline-block text-sm font-medium text-blue-600">
          Start a new Full Test
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-8">
      <div className="rounded-2xl border border-gray-200 bg-white p-6 text-center shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-gray-400">Full Test</p>
        <p className="mt-3 text-sm text-gray-500">Overall band</p>
        <p className="text-5xl font-bold text-gray-900">{overall !== null ? overall.toFixed(1) : "—"}</p>
        {hasComingSoon && (
          <p className="mt-3 text-xs text-amber-600">
            Provisional — Listening &amp; Speaking aren't available yet, so they don't count toward
            this band.
          </p>
        )}
      </div>

      <div className="mt-6 divide-y divide-gray-100 overflow-hidden rounded-xl border border-gray-200 bg-white">
        {mock.sections.map((section) => {
          const status = statusFor(section);
          const link = sectionResultLink(section);
          return (
            <div key={section.skill} className="flex items-center justify-between gap-4 px-5 py-4">
              <div>
                <p className="font-semibold text-gray-900">{skillLabel(section.skill)}</p>
                {link && (
                  <Link to={link} className="text-xs font-medium text-blue-600 hover:underline">
                    View details
                  </Link>
                )}
              </div>
              <span
                className={`rounded-full px-3 py-1 text-sm font-medium ${
                  status.tone === "band"
                    ? "bg-emerald-50 text-emerald-700"
                    : status.tone === "warn"
                      ? "bg-amber-50 text-amber-700"
                      : "bg-gray-100 text-gray-500"
                }`}
              >
                {status.text}
              </span>
            </div>
          );
        })}
      </div>

      <div className="mt-6 flex gap-3">
        <Link
          to="/mock"
          className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-700"
        >
          New Full Test
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
