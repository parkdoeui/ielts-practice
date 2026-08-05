export interface PlanningClock {
  phase: "countdown" | "overtime";
  display: string;
  elapsedMs: number;
  remainingMs: number;
}

const TARGET_MS = 5 * 60 * 1000;

function format(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

export function getPlanningClock(startedAtMs: number, nowMs: number): PlanningClock {
  const elapsedMs = Math.max(0, nowMs - startedAtMs);
  if (elapsedMs <= TARGET_MS) {
    return {
      phase: "countdown",
      display: format(TARGET_MS - elapsedMs),
      elapsedMs,
      remainingMs: TARGET_MS - elapsedMs,
    };
  }
  return {
    phase: "overtime",
    display: `+${format(elapsedMs - TARGET_MS)}`,
    elapsedMs,
    remainingMs: 0,
  };
}
