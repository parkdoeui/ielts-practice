export interface PlanningClock {
  display: string;
  elapsedMs: number;
}

function formatElapsed(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

export function getPlanningClock(startedAtMs: number, nowMs: number): PlanningClock {
  const elapsedMs = Math.max(0, nowMs - startedAtMs);
  return {
    display: formatElapsed(elapsedMs),
    elapsedMs,
  };
}
