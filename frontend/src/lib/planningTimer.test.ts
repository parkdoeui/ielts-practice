import { describe, expect, it } from "vitest";
import { getPlanningClock } from "./planningTimer";

describe("getPlanningClock", () => {
  it("counts down to zero", () => {
    expect(getPlanningClock(0, 299999).display).toBe("00:00");
    expect(getPlanningClock(0, 300000).phase).toBe("countdown");
  });

  it("continues as overtime after five minutes", () => {
    expect(getPlanningClock(0, 300001)).toEqual({
      phase: "overtime",
      display: "+00:00",
      elapsedMs: 300001,
      remainingMs: 0,
    });
    expect(getPlanningClock(0, 301000).display).toBe("+00:01");
  });
});
