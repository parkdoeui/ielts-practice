import { useEffect, useState } from "react";
import { SCALE_ORDER, type FontScale } from "../lib/fontScale";

interface Props {
  sectionLabel: string;
  totalSeconds: number;
  paused?: boolean;
  fontScale: FontScale;
  onFontScaleChange: (scale: FontScale) => void;
}

/**
 * Top chrome for the mock (CBT) experience — mirrors the composition of the official
 * computer-delivered IELTS status bar: section/part label on the left, a countdown that
 * shows minutes remaining (no seconds, like the real exam) in the middle, and a font-size
 * control on the right. The countdown reuses TimerBar's setInterval/paused pattern.
 */
export function CbtStatusBar({ sectionLabel, totalSeconds, paused = false, fontScale, onFontScaleChange }: Props) {
  const [secondsLeft, setSecondsLeft] = useState(totalSeconds);

  useEffect(() => {
    if (paused || secondsLeft <= 0) return;
    const id = setInterval(() => setSecondsLeft((s) => Math.max(0, s - 1)), 1000);
    return () => clearInterval(id);
  }, [secondsLeft, paused]);

  const minutesLeft = Math.ceil(secondsLeft / 60);
  const isWarning = secondsLeft <= 5 * 60;
  const timeLabel =
    secondsLeft <= 60 ? "less than 1 minute left" : `${minutesLeft} minutes left`;

  const scaleIndex = SCALE_ORDER.indexOf(fontScale);
  const step = (delta: number) => {
    const next = SCALE_ORDER[Math.min(SCALE_ORDER.length - 1, Math.max(0, scaleIndex + delta))];
    if (next !== fontScale) onFontScaleChange(next);
  };

  return (
    <div className="flex items-center justify-between gap-4 border-b border-gray-700 bg-gray-900 px-4 md:px-6 py-2 text-white shrink-0">
      <span className="text-sm font-semibold tracking-wide truncate">{sectionLabel}</span>

      <span
        className={`text-sm font-mono font-semibold tabular-nums ${
          isWarning ? "text-red-300" : "text-gray-100"
        }`}
      >
        {timeLabel}
      </span>

      <div className="flex items-center gap-1" aria-label="Font size">
        <button
          type="button"
          onClick={() => step(-1)}
          disabled={scaleIndex === 0}
          className="h-7 w-7 rounded border border-gray-600 text-xs font-semibold disabled:opacity-40 hover:bg-gray-800"
          aria-label="Decrease font size"
        >
          A−
        </button>
        <button
          type="button"
          onClick={() => step(1)}
          disabled={scaleIndex === SCALE_ORDER.length - 1}
          className="h-7 w-7 rounded border border-gray-600 text-sm font-semibold disabled:opacity-40 hover:bg-gray-800"
          aria-label="Increase font size"
        >
          A+
        </button>
      </div>
    </div>
  );
}
