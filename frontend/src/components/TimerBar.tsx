import { useEffect, useState } from "react";

interface Props {
  totalSeconds: number;  // 60 * 60 = 3600
  answeredCount: number;
  totalCount: number;
  onExpire: () => void;
  paused?: boolean;
}

export function TimerBar({ totalSeconds, answeredCount, totalCount, onExpire, paused = false }: Props) {
  const [secondsLeft, setSecondsLeft] = useState(totalSeconds);

  useEffect(() => {
    if (paused) return;
    if (secondsLeft <= 0) {
      onExpire();
      return;
    }
    const id = setInterval(() => setSecondsLeft((s) => s - 1), 1000);
    return () => clearInterval(id);
  }, [secondsLeft, paused, onExpire]);

  const minutes = Math.floor(secondsLeft / 60);
  const seconds = secondsLeft % 60;
  const progress = answeredCount / totalCount;
  const isWarning = secondsLeft < 5 * 60;

  return (
    <div className="bg-white px-4 md:px-6 py-3">
      <div className="flex items-center gap-4">
        <span className={`font-mono text-lg font-bold tabular-nums ${isWarning ? "text-red-600 animate-pulse" : "text-gray-900"}`}>
          {String(minutes).padStart(2, "0")}:{String(seconds).padStart(2, "0")}
        </span>
        <div className="flex-1 bg-gray-200 rounded-full h-2">
          <div
            className="bg-blue-600 h-2 rounded-full transition-all duration-300"
            style={{ width: `${progress * 100}%` }}
          />
        </div>
        <span className="text-sm text-gray-500 tabular-nums shrink-0">
          {answeredCount}/{totalCount}
        </span>
      </div>
    </div>
  );
}
