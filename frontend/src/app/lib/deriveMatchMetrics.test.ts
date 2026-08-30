import { describe, expect, it } from "vitest";
import { formatClock, healthStatus, streamDelayS } from "./deriveMatchMetrics";

describe("live metric presentation helpers", () => {
  it("formats the backend-authoritative clock", () => {
    expect(formatClock(3780)).toBe("63:00");
    expect(formatClock(-1)).toBe("0:00");
  });

  it("reports transport delay from emitted Unix time", () => {
    expect(streamDelayS(100, 102_500)).toBe(2.5);
  });

  it("does not call stale or disconnected data live", () => {
    expect(healthStatus({ isConnected: true, hasData: true, delayS: 2, demoMode: false })).toBe("live");
    expect(healthStatus({ isConnected: true, hasData: true, delayS: 8, demoMode: false })).toBe("delayed");
    expect(healthStatus({ isConnected: false, hasData: true, delayS: 0, demoMode: false })).toBe("offline");
  });
});
