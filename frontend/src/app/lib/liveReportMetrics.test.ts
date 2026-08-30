import { describe, expect, it } from "vitest";
import { buildLiveReportPlaceholders } from "./liveReportMetrics";

describe("buildLiveReportPlaceholders", () => {
  it("keeps every live report section visible without inventing values", () => {
    const sections = buildLiveReportPlaceholders();

    expect(sections.map((section) => section.id)).toEqual([
      "overview",
      "territory",
      "transitions",
      "shape",
      "pressing",
      "quality",
    ]);
    expect(sections.flatMap((section) => section.metrics).every((metric) => (
      metric.status === "unavailable"
      && metric.coverage === 0
      && metric.values.every((value) => value === null)
    ))).toBe(true);
    expect(sections[0].metrics.some((metric) => metric.id === "xg")).toBe(true);
  });
});
