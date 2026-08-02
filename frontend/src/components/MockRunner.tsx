import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { getMockSession, saveMockSession } from "../services/api";
import {
  IMPLEMENTED_SKILLS,
  isMockSectionComingSoon,
  type MockSession,
  type SkillName,
} from "../types";
import { ListeningTest, type ListeningSectionResult } from "./ListeningTest";
import { ReadingTest, type ReadingSectionResult } from "./ReadingTest";
import { WritingTest, type WritingSectionResult } from "./WritingTest";
import { ComingSoonSection } from "./ComingSoonSection";

type SectionResult = ListeningSectionResult | ReadingSectionResult | WritingSectionResult;

const skillLabel = (skill: SkillName) => skill.charAt(0).toUpperCase() + skill.slice(1);

// Where to resume: the first implemented section that isn't done. On a fresh mock,
// Listening is the first real section and therefore opens immediately.
function firstCursor(mock: MockSession): number {
  const firstUnfinished = mock.sections.findIndex(
    (section) => IMPLEMENTED_SKILLS.has(section.skill) && section.session_id === null,
  );
  if (firstUnfinished === -1) return mock.sections.length;
  const anyDone = mock.sections.some((section) => section.session_id !== null);
  return anyDone ? firstUnfinished : 0;
}

export function MockRunner() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [mock, setMock] = useState<MockSession | null>(() => (id ? getMockSession(id) : null));
  const [cursor, setCursor] = useState<number>(() => (mock ? firstCursor(mock) : 0));
  const [phase, setPhase] = useState<"running" | "handoff">("running");

  useEffect(() => {
    if (!mock) navigate("/mock", { replace: true });
  }, [mock, navigate]);

  useEffect(() => {
    if (mock && cursor >= mock.sections.length) {
      navigate(`/mock-results/${mock.id}`, { replace: true });
    }
  }, [cursor, mock, navigate]);

  if (!mock) return null;
  if (cursor >= mock.sections.length) {
    return <div className="p-8 text-gray-500">Finishing your test…</div>;
  }

  const section = mock.sections[cursor];

  const advance = () => {
    setPhase("running");
    setCursor((c) => c + 1);
  };

  const handleSectionComplete = (result: SectionResult) => {
    setMock((prev) => {
      if (!prev) return prev;
      const sections = prev.sections.map((s, i) =>
        i === cursor ? { ...s, session_id: result.sessionId, band: result.band } : s,
      );
      const updated = { ...prev, sections };
      saveMockSession(updated);
      return updated;
    });
    if (mock.mode === "strict") advance();
    else setPhase("handoff");
  };

  if (phase === "handoff") {
    return (
      <HandoffScreen
        justFinished={section.skill}
        next={mock.sections[cursor + 1]?.skill ?? null}
        onContinue={advance}
        onLeave={() => navigate("/")}
      />
    );
  }

  if (isMockSectionComingSoon(section)) {
    return <ComingSoonSection skill={section.skill} onSkip={advance} />;
  }

  if (section.skill === "listening" && section.test_id) {
    return (
      <ListeningTest
        key={`listening-${cursor}`}
        embeddedTestId={section.test_id}
        onComplete={handleSectionComplete}
      />
    );
  }

  if (section.skill === "reading" && section.test_id) {
    return (
      <ReadingTest
        key={`reading-${cursor}`}
        embeddedTestId={section.test_id}
        onComplete={handleSectionComplete}
      />
    );
  }

  if (section.skill === "writing" && section.test_id) {
    return (
      <WritingTest
        key={`writing-${cursor}`}
        embeddedTestId={section.test_id}
        onComplete={handleSectionComplete}
      />
    );
  }

  // Implemented skill with no test assigned — shouldn't happen; skip defensively.
  return <ComingSoonSection skill={section.skill} onSkip={advance} />;
}

function HandoffScreen({
  justFinished,
  next,
  onContinue,
  onLeave,
}: {
  justFinished: SkillName;
  next: SkillName | null;
  onContinue: () => void;
  onLeave: () => void;
}) {
  return (
    <div className="flex h-screen flex-col items-center justify-center bg-gray-50 p-8 text-center">
      <div className="max-w-md rounded-2xl border border-gray-200 bg-white p-8 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-gray-400">
          Section complete
        </p>
        <h1 className="mt-2 text-2xl font-bold text-gray-900">{skillLabel(justFinished)} done</h1>
        <p className="mt-3 text-sm leading-6 text-gray-600">
          {next ? `Next up: ${skillLabel(next)}.` : "That was the last section."} Take a short
          break if you need one — your progress is saved.
        </p>
        <div className="mt-6 flex flex-col gap-2">
          <button
            type="button"
            onClick={onContinue}
            className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-700"
          >
            {next ? "Continue" : "See results"}
          </button>
          <button
            type="button"
            onClick={onLeave}
            className="rounded-lg border border-gray-300 px-5 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Leave &amp; resume later
          </button>
        </div>
      </div>
    </div>
  );
}
