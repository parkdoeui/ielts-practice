import { describe, expect, it } from "vitest";
import { getPlanningClock } from "./planningTimer";

describe("getPlanningClock", () => {
  it("starts at zero and counts elapsed seconds upward", () => {
    expect(getPlanningClock(1000, 0)).toEqual({ display: "0:00", elapsedMs: 0 });
    expect(getPlanningClock(0, 999).display).toBe("0:00");
    expect(getPlanningClock(0, 1000).display).toBe("0:01");
  });

  it("continues without a deadline or overtime state", () => {
    expect(getPlanningClock(0, 300000)).toEqual({ display: "5:00", elapsedMs: 300000 });
    expect(getPlanningClock(0, 3661000).display).toBe("61:01");
  });
});
