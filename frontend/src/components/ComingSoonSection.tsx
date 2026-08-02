import type { SkillName } from "../types";

interface Props {
  skill: SkillName;
  onSkip: () => void;
}

/**
 * Placeholder step shown for skills that aren't playable yet (Listening, Speaking).
 * Keeps the four-section structure visible during a mock; skipping advances the runner
 * and the section contributes nothing to the overall band.
 */
export function ComingSoonSection({ skill, onSkip }: Props) {
  const label = skill.charAt(0).toUpperCase() + skill.slice(1);

  return (
    <div className="flex h-screen flex-col items-center justify-center bg-gray-50 p-8 text-center">
      <div className="max-w-md rounded-2xl border border-gray-200 bg-white p-8 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-gray-400">Section</p>
        <h1 className="mt-2 text-2xl font-bold text-gray-900">{label}</h1>
        <span className="mt-3 inline-block rounded-full bg-amber-50 px-3 py-1 text-xs font-medium text-amber-700">
          Coming soon
        </span>
        <p className="mt-4 text-sm leading-6 text-gray-600">
          The {label} section isn't available yet. It will join the full test soon — for now it's
          skipped and won't count toward your overall band.
        </p>
        <button
          type="button"
          onClick={onSkip}
          className="mt-6 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-700"
        >
          Skip for now
        </button>
      </div>
    </div>
  );
}
