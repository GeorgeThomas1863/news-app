import { describe, test, expect, beforeEach, afterEach, vi } from "vitest";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import PipelineStatsPanel from "./PipelineStatsPanel.jsx";
import { getPipelineStats } from "../api.js";

vi.mock("../api.js", () => ({
  getPipelineStats: vi.fn(),
}));

const minutesAgo = (minutes) => new Date(Date.now() - minutes * 60000).toISOString();

function buildStats(overrides = {}) {
  return {
    running: true,
    paused: false,
    live: {
      run: {
        trigger: "manual",
        started_at: minutesAgo(2),
        finished_at: null,
        status: null,
        stage: "group",
      },
      stages: {
        ingest: {
          status: "done",
          started_at: minutesAgo(2),
          finished_at: minutesAgo(1),
          current: 12,
          total: 12,
          detail: null,
          duration_seconds: 5,
        },
        embed: {
          status: "idle",
          started_at: null,
          finished_at: null,
          current: 0,
          total: null,
          detail: null,
          duration_seconds: null,
        },
        reap: {
          status: "idle",
          started_at: null,
          finished_at: null,
          current: 0,
          total: null,
          detail: null,
          duration_seconds: null,
        },
        group: {
          status: "running",
          started_at: minutesAgo(1),
          finished_at: null,
          current: 4,
          total: 10,
          detail: "Ceasefire talks collapse in eastern border region",
          duration_seconds: null,
        },
        score: {
          status: "idle",
          started_at: null,
          finished_at: null,
          current: 0,
          total: null,
          detail: null,
          duration_seconds: null,
        },
      },
      counts: {
        ingested: 42,
        deduped: 5,
        embedded: 37,
        stories_created: 3,
        stories_updated: 8,
        filtered_out: 2,
        scored: 6,
        orphans_reaped: 1,
      },
      llm: {
        run: {
          filter: { calls: 9, failures: 1 },
          verdict: { calls: 4, failures: 0 },
          score: { calls: 6, failures: 2 },
        },
        total: {
          filter: { calls: 900, failures: 15 },
          verdict: { calls: 400, failures: 3 },
          score: { calls: 600, failures: 22 },
        },
      },
      embed: {
        run: { calls: 3, failures: 0 },
        total: { calls: 350, failures: 4 },
      },
      last_error: null,
    },
    recent_runs: [
      {
        id: "run-newest",
        trigger: "schedule",
        started_at: minutesAgo(70),
        finished_at: minutesAgo(65),
        status: "error",
        counts: {
          ingested: 20,
          deduped: 1,
          embedded: 18,
          stories_created: 2,
          stories_updated: 4,
          filtered_out: 1,
          scored: 3,
          orphans_reaped: 0,
        },
        errors: [{ stage: "score", message: "llm call failed: timeout contacting scoring model" }],
        stages: {},
        duration_seconds: 270,
      },
      {
        id: "run-older",
        trigger: "manual",
        started_at: minutesAgo(130),
        finished_at: minutesAgo(127),
        status: "done",
        counts: {
          ingested: 15,
          deduped: 0,
          embedded: 15,
          stories_created: 1,
          stories_updated: 2,
          filtered_out: 0,
          scored: 2,
          orphans_reaped: 0,
        },
        errors: [],
        stages: {},
        duration_seconds: 195,
      },
    ],
    totals: {
      raw_items: 5000,
      raw_embedded: 4800,
      raw_ungrouped: 200,
      raw_last_24h: 600,
      stories: { pending: 15, filtered: 100, scored: 2000, dirty: 30, total: 2145 },
      sources: { rss: { enabled: 7, disabled: 2 }, telegram: { enabled: 3, disabled: 1 } },
      items_by_source: [
        { source_name: "Reuters World", source_type: "rss", count: 1200 },
        { source_name: "Intel Slava", source_type: "telegram", count: 900 },
      ],
    },
    config: {
      poll_interval_minutes: 15,
      sim_high: 0.85,
      sim_low: 0.7,
      active_window_hours: 48,
      decay_half_life_hours: 12,
      embed_model: "voyage-3-large",
      filter_model: "gpt-5.6-luna",
      scoring_model: "gpt-5.6-sol",
    },
    ...overrides,
  };
}

async function flush() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();
  });
}

function findFragment(text) {
  return screen.getAllByText(text, { exact: false });
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("PipelineStatsPanel", () => {
  test("does not fetch when closed", () => {
    render(<PipelineStatsPanel open={false} onClose={vi.fn()} />);

    expect(getPipelineStats).not.toHaveBeenCalled();
  });

  test("root has the open class only when open", async () => {
    getPipelineStats.mockResolvedValue(buildStats());

    const closed = render(<PipelineStatsPanel open={false} onClose={vi.fn()} />);
    const closedRoot = closed.container.querySelector("#pipeline-stats-panel");
    expect(closedRoot).not.toBeNull();
    expect(closedRoot.className.split(" ")).not.toContain("open");
    expect(closedRoot).toHaveAttribute("aria-hidden", "true");
    closed.unmount();

    const opened = render(<PipelineStatsPanel open={true} onClose={vi.fn()} />);
    await flush();
    const openRoot = opened.container.querySelector("#pipeline-stats-panel");
    expect(openRoot.className.split(" ")).toContain("open");
    expect(openRoot).toHaveAttribute("aria-hidden", "false");
  });

  test("fetches on mount and renders the stage cards, running badge, and progress when open", async () => {
    getPipelineStats.mockResolvedValue(buildStats());
    render(<PipelineStatsPanel open={true} onClose={vi.fn()} />);

    await waitFor(() => expect(getPipelineStats).toHaveBeenCalledTimes(1));
    await screen.findByText("Ingest sources");

    expect(screen.getByText("Embed items")).toBeInTheDocument();
    expect(screen.getByText("Reap orphans")).toBeInTheDocument();
    expect(screen.getByText("Group into stories")).toBeInTheDocument();
    expect(screen.getByText("Filter & score")).toBeInTheDocument();

    expect(screen.getAllByText("Running").length).toBeGreaterThan(0);
    expect(findFragment("4/10").length).toBeGreaterThan(0);
    expect(
      findFragment("Ceasefire talks collapse in eastern border region").length,
    ).toBeGreaterThan(0);
  });

  test("renders run counts, database totals, recent runs, and config when open", async () => {
    getPipelineStats.mockResolvedValue(buildStats());
    render(<PipelineStatsPanel open={true} onClose={vi.fn()} />);

    await waitFor(() => expect(getPipelineStats).toHaveBeenCalledTimes(1));
    await screen.findByText("Ingest sources");

    // run counts (ingested = 42, unique across the fixture)
    expect(findFragment("42").length).toBeGreaterThan(0);

    // items by source
    expect(findFragment("Reuters World").length).toBeGreaterThan(0);

    // recent run trigger (only the older, errored run uses "schedule")
    expect(findFragment("schedule").length).toBeGreaterThan(0);

    // error message from the most recent run
    expect(
      findFragment("llm call failed: timeout contacting scoring model").length,
    ).toBeGreaterThan(0);

    // config value
    expect(findFragment("gpt-5.6-luna").length).toBeGreaterThan(0);
  });

  test("shows the error message and keeps prior data when a later poll fails", async () => {
    vi.useFakeTimers();
    try {
      getPipelineStats.mockResolvedValue(buildStats());
      const { container } = render(<PipelineStatsPanel open={true} onClose={vi.fn()} />);

      await flush();
      expect(getPipelineStats).toHaveBeenCalledTimes(1);
      expect(screen.getByText("Ingest sources")).toBeInTheDocument();

      getPipelineStats.mockRejectedValue(new Error("Database unavailable"));

      await act(async () => {
        vi.advanceTimersByTime(2500);
        await Promise.resolve();
        await Promise.resolve();
      });

      expect(getPipelineStats).toHaveBeenCalledTimes(2);
      expect(container.querySelector(".stats-error")).toHaveTextContent("Database unavailable");
      expect(screen.getByText("Ingest sources")).toBeInTheDocument();
    } finally {
      vi.useRealTimers();
    }
  });

  test("shows the error on first load when the fetch fails", async () => {
    getPipelineStats.mockRejectedValue(new Error("Database unavailable"));
    const { container } = render(<PipelineStatsPanel open={true} onClose={vi.fn()} />);

    await waitFor(() => expect(container.querySelector(".stats-error")).not.toBeNull());
    expect(container.querySelector(".stats-error")).toHaveTextContent("Database unavailable");
  });

  test("close button calls onClose", async () => {
    getPipelineStats.mockResolvedValue(buildStats());
    const onClose = vi.fn();
    render(<PipelineStatsPanel open={true} onClose={onClose} />);

    await screen.findByText("PIPELINE STATS");
    fireEvent.click(screen.getByRole("button", { name: "Close pipeline stats" }));

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  describe("polling", () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    test("polls every 2500ms while a run is in progress", async () => {
      getPipelineStats.mockResolvedValue(buildStats({ running: true }));
      render(<PipelineStatsPanel open={true} onClose={vi.fn()} />);

      await flush();
      expect(getPipelineStats).toHaveBeenCalledTimes(1);

      await act(async () => {
        vi.advanceTimersByTime(2500);
        await Promise.resolve();
        await Promise.resolve();
      });
      expect(getPipelineStats).toHaveBeenCalledTimes(2);
    });

    test("polls every 10000ms, not 2500ms, when idle", async () => {
      getPipelineStats.mockResolvedValue(buildStats({ running: false }));
      render(<PipelineStatsPanel open={true} onClose={vi.fn()} />);

      await flush();
      expect(getPipelineStats).toHaveBeenCalledTimes(1);

      await act(async () => {
        vi.advanceTimersByTime(2500);
        await Promise.resolve();
        await Promise.resolve();
      });
      expect(getPipelineStats).toHaveBeenCalledTimes(1);

      await act(async () => {
        vi.advanceTimersByTime(7500);
        await Promise.resolve();
        await Promise.resolve();
      });
      expect(getPipelineStats).toHaveBeenCalledTimes(2);
    });
  });

  test("closing and reopening while a fetch is in flight does not start a second poll chain", async () => {
    vi.useFakeTimers();
    try {
      let resolveFirst;
      getPipelineStats.mockImplementationOnce(
        () => new Promise((resolve) => { resolveFirst = resolve; })
      );
      getPipelineStats.mockResolvedValue(buildStats());

      const { rerender } = render(<PipelineStatsPanel open={true} onClose={vi.fn()} />);
      expect(getPipelineStats).toHaveBeenCalledTimes(1);

      rerender(<PipelineStatsPanel open={false} onClose={vi.fn()} />);
      rerender(<PipelineStatsPanel open={true} onClose={vi.fn()} />);
      await flush();
      expect(getPipelineStats).toHaveBeenCalledTimes(2);

      await act(async () => {
        resolveFirst(buildStats());
        await Promise.resolve();
        await Promise.resolve();
      });

      await act(async () => {
        vi.advanceTimersByTime(2500);
        await Promise.resolve();
        await Promise.resolve();
      });
      expect(getPipelineStats).toHaveBeenCalledTimes(3);

      rerender(<PipelineStatsPanel open={false} onClose={vi.fn()} />);
      await act(async () => {
        vi.advanceTimersByTime(20000);
        await Promise.resolve();
      });
      expect(getPipelineStats).toHaveBeenCalledTimes(3);
    } finally {
      vi.useRealTimers();
    }
  });
});
