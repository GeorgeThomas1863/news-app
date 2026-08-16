import { describe, test, expect, beforeEach, afterEach, vi } from "vitest";
import { formatTimeAgo } from "./time.js";

const NOW = new Date("2026-08-15T12:00:00Z");

function isoMinutesAgo(minutes) {
  return new Date(NOW.getTime() - minutes * 60000).toISOString();
}

describe("formatTimeAgo", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(NOW);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  test("returns empty string for unparseable input", () => {
    expect(formatTimeAgo("not-a-date")).toBe("");
    expect(formatTimeAgo(undefined)).toBe("");
  });

  test("returns 'just now' under one minute", () => {
    expect(formatTimeAgo(isoMinutesAgo(0))).toBe("just now");
  });

  test("formats minutes under an hour", () => {
    expect(formatTimeAgo(isoMinutesAgo(1))).toBe("1m ago");
    expect(formatTimeAgo(isoMinutesAgo(59))).toBe("59m ago");
  });

  test("formats hours up to 48h, then days", () => {
    expect(formatTimeAgo(isoMinutesAgo(60))).toBe("1h ago");
    expect(formatTimeAgo(isoMinutesAgo(47 * 60))).toBe("47h ago");
    expect(formatTimeAgo(isoMinutesAgo(48 * 60))).toBe("2d ago");
    expect(formatTimeAgo(isoMinutesAgo(10 * 24 * 60))).toBe("10d ago");
  });
});
