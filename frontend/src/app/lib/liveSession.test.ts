import { describe, expect, it } from "vitest";
import { isSessionActive, sessionLabel, validExclusion } from "./liveSession";

describe("managed broadcast sessions", () => {
  it("keeps stopping sessions active until cleanup is complete", () => {
    expect(isSessionActive({ id: "one", event_url: "", state: "stopping", error: null, deadline: 1, artifacts_ready: false, worker_started: true })).toBe(true);
    expect(isSessionActive(null)).toBe(false);
    expect(sessionLabel("interrupted")).toBe("Analysis interrupted");
  });
  it("accepts only intervals already observed on the broadcast timeline", () => {
    expect(validExclusion(10, 20, 30)).toBe(true);
    expect(validExclusion(20, 10, 30)).toBe(false);
    expect(validExclusion(10, 40, 30)).toBe(false);
    expect(validExclusion(Number.NaN, 20, 30)).toBe(false);
  });
});
