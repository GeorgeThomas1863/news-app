import { useCallback, useEffect, useRef, useState } from "react";

import { getPipelineStats } from "../api.js";
import { formatTimeAgo } from "../time.js";

const RUNNING_POLL_MS = 2500;
const IDLE_POLL_MS = 10000;

const STAGES = ["ingest", "embed", "reap", "group", "score"];

const COUNT_FIELDS = [
  "ingested",
  "deduped",
  "embedded",
  "stories_created",
  "stories_updated",
  "filtered_out",
  "scored",
  "orphans_reaped",
];

const LLM_SITES = ["filter", "verdict", "score"];

const CONFIG_FIELDS = [
  "poll_interval_minutes",
  "sim_high",
  "sim_low",
  "active_window_hours",
  "decay_half_life_hours",
  "embed_model",
  "filter_model",
  "scoring_model",
];

const PipelineStatsPanel = ({ open, onClose }) => {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);
  const timerRef = useRef(null);

  const fetchStats = useCallback(async () => {
    try {
      const body = await getPipelineStats();
      setStats(body);
      setError(null);
      return body;
    } catch (err) {
      setError(err.message);
      return null;
    }
  }, []);

  // Recurring poll loop: interval depends on whether the pipeline is running,
  // so each cycle re-decides its own delay from the fetch it just made.
  // `session` is created per open and flagged inactive on close, so a fetch
  // still in flight when the panel closes (or closes and reopens) cannot
  // reschedule itself into a second concurrent chain.
  const pollLoop = useCallback(
    async (session) => {
      const body = await fetchStats();
      if (!session.active) return;
      const delay = body && body.running ? RUNNING_POLL_MS : IDLE_POLL_MS;
      timerRef.current = setTimeout(() => pollLoop(session), delay);
    },
    [fetchStats]
  );

  useEffect(() => {
    if (!open) return undefined;

    const session = { active: true };
    pollLoop(session);
    return () => {
      session.active = false;
      clearTimeout(timerRef.current);
    };
  }, [open, pollLoop]);

  return (
    <aside
      id="pipeline-stats-panel"
      className={open ? "stats-panel open" : "stats-panel"}
      aria-hidden={!open}
    >
      <div className="stats-panel-header">
        <h2>PIPELINE STATS</h2>
        <button className="stats-close-btn" aria-label="Close pipeline stats" onClick={onClose}>
          ✕
        </button>
      </div>
      <div className="stats-panel-body">
        {error && <p className="stats-error">{error}</p>}
        {!stats ? (
          <p className="stats-loading">Loading…</p>
        ) : (
          <>
            <StatusSection stats={stats} />
            <StagesSection live={stats.live} />
            <CountsSection counts={stats.live && stats.live.counts} />
            <LlmSection live={stats.live} />
            <DatabaseSection totals={stats.totals} />
            <RecentRunsSection runs={stats.recent_runs} />
            <ConfigSection config={stats.config} />
          </>
        )}
      </div>
    </aside>
  );
};

const StatusSection = ({ stats }) => {
  const run = stats.live && stats.live.run;
  const badge = runBadge(stats);
  const elapsed = run ? computeElapsedSeconds(run.started_at, run.finished_at) : null;

  return (
    <section className="stats-section">
      <div className="stats-status-line">
        <span className={`stats-status-badge stats-status-${badge.className}`}>{badge.label}</span>
        {run && run.trigger && <span className="stats-status-trigger">{run.trigger}</span>}
        {run && run.started_at && (
          <span className="stats-status-started">started {formatTimeAgo(run.started_at)}</span>
        )}
        {elapsed !== null && (
          <span className="stats-status-elapsed">elapsed {formatDuration(elapsed)}</span>
        )}
      </div>
    </section>
  );
};

const StagesSection = ({ live }) => {
  const stages = (live && live.stages) || {};

  return (
    <section className="stats-section">
      <h3 className="stats-section-title">Stages</h3>
      <div className="stats-stage-list">
        {STAGES.map((name) => (
          <StageCard key={name} name={name} stage={stages[name]} />
        ))}
      </div>
    </section>
  );
};

const StageCard = ({ name, stage }) => {
  const status = (stage && stage.status) || "idle";
  const current = (stage && stage.current) || 0;
  const total = stage && stage.total;
  const hasProgress = Boolean(total && total > 0);
  const pct = hasProgress ? Math.min(100, Math.round((current / total) * 100)) : 0;
  const duration =
    stage && stage.started_at
      ? formatDuration(
          stage.duration_seconds ?? computeElapsedSeconds(stage.started_at, stage.finished_at)
        )
      : null;

  return (
    <div className={`stats-card stats-card-${status}`}>
      <div className="stats-card-head">
        <span className="stats-card-title">{stageLabel(name)}</span>
        <span className={`stats-badge stats-badge-${status}`}>{stageStatusLabel(status)}</span>
      </div>
      {hasProgress && (
        <div className="stats-progress-row">
          <div className="stats-progress-track">
            <div className="stats-progress-fill" style={{ width: `${pct}%` }} />
          </div>
          <span className="stats-progress-count">
            {current}/{total}
          </span>
        </div>
      )}
      {stage && stage.detail && <div className="stats-detail">{stage.detail}</div>}
      {duration && <div className="stats-elapsed">{duration}</div>}
    </div>
  );
};

const CountsSection = ({ counts }) => {
  const data = counts || {};

  return (
    <section className="stats-section">
      <h3 className="stats-section-title">Run counts</h3>
      <div className="stats-grid">
        {COUNT_FIELDS.map((key) => (
          <div className="stats-kv" key={key}>
            <span className="stats-kv-label">{countLabel(key)}</span>
            <span className="stats-kv-value">{data[key] ?? 0}</span>
          </div>
        ))}
      </div>
    </section>
  );
};

const LlmSection = ({ live }) => {
  const llm = (live && live.llm) || {};
  const embed = (live && live.embed) || {};
  const llmRun = llm.run || {};
  const llmTotal = llm.total || {};

  return (
    <section className="stats-section">
      <h3 className="stats-section-title">LLM calls</h3>
      <div className="stats-llm-list">
        {LLM_SITES.map((site) => (
          <LlmRow key={site} label={llmSiteLabel(site)} run={llmRun[site]} total={llmTotal[site]} />
        ))}
        <LlmRow label="Embed" run={embed.run} total={embed.total} />
      </div>
    </section>
  );
};

const LlmRow = ({ label, run, total }) => {
  const runData = run || { calls: 0, failures: 0 };
  const totalData = total || { calls: 0, failures: 0 };

  return (
    <div className="stats-llm-row">
      <span className="stats-llm-label">{label}</span>
      <span className="stats-llm-value">
        this run: {runData.calls ?? 0} calls, {runData.failures ?? 0} failed
      </span>
      <span className="stats-llm-value">
        total: {totalData.calls ?? 0} calls, {totalData.failures ?? 0} failed
      </span>
    </div>
  );
};

const DatabaseSection = ({ totals }) => {
  const data = totals || {};
  const stories = data.stories || {};
  const sources = data.sources || {};
  const rss = sources.rss || {};
  const telegram = sources.telegram || {};
  const itemsBySource = data.items_by_source || [];

  return (
    <section className="stats-section">
      <h3 className="stats-section-title">Database</h3>
      <div className="stats-grid">
        <div className="stats-kv">
          <span className="stats-kv-label">Raw items</span>
          <span className="stats-kv-value">{data.raw_items ?? 0}</span>
        </div>
        <div className="stats-kv">
          <span className="stats-kv-label">Embedded</span>
          <span className="stats-kv-value">{data.raw_embedded ?? 0}</span>
        </div>
        <div className="stats-kv">
          <span className="stats-kv-label">Ungrouped</span>
          <span className="stats-kv-value">{data.raw_ungrouped ?? 0}</span>
        </div>
        <div className="stats-kv">
          <span className="stats-kv-label">Last 24h</span>
          <span className="stats-kv-value">{data.raw_last_24h ?? 0}</span>
        </div>
        <div className="stats-kv">
          <span className="stats-kv-label">Stories pending</span>
          <span className="stats-kv-value">{stories.pending ?? 0}</span>
        </div>
        <div className="stats-kv">
          <span className="stats-kv-label">Stories filtered</span>
          <span className="stats-kv-value">{stories.filtered ?? 0}</span>
        </div>
        <div className="stats-kv">
          <span className="stats-kv-label">Stories scored</span>
          <span className="stats-kv-value">{stories.scored ?? 0}</span>
        </div>
        <div className="stats-kv">
          <span className="stats-kv-label">Stories dirty</span>
          <span className="stats-kv-value">{stories.dirty ?? 0}</span>
        </div>
        <div className="stats-kv">
          <span className="stats-kv-label">Stories total</span>
          <span className="stats-kv-value">{stories.total ?? 0}</span>
        </div>
        <div className="stats-kv">
          <span className="stats-kv-label">RSS sources</span>
          <span className="stats-kv-value">
            {rss.enabled ?? 0} on / {rss.disabled ?? 0} off
          </span>
        </div>
        <div className="stats-kv">
          <span className="stats-kv-label">Telegram sources</span>
          <span className="stats-kv-value">
            {telegram.enabled ?? 0} on / {telegram.disabled ?? 0} off
          </span>
        </div>
      </div>
      <h4 className="stats-subsection-title">Items by source</h4>
      <ul className="stats-source-list">
        {itemsBySource.map((row) => (
          <li className="stats-source-row" key={`${row.source_type}-${row.source_name}`}>
            <span className="stats-source-name">{row.source_name}</span>
            <span className="stats-source-type">{row.source_type}</span>
            <span className="stats-source-count">{row.count}</span>
          </li>
        ))}
        {itemsBySource.length === 0 && <li className="stats-source-empty">No items yet</li>}
      </ul>
    </section>
  );
};

const RecentRunsSection = ({ runs }) => {
  const list = runs || [];
  const latest = list[0];
  const latestErrors = latest && latest.errors ? latest.errors : [];

  return (
    <section className="stats-section">
      <h3 className="stats-section-title">Recent runs</h3>
      <div className="stats-runs-list">
        {list.map((run) => (
          <RunRow key={run.id} run={run} />
        ))}
        {list.length === 0 && <p className="stats-runs-empty">No runs yet</p>}
      </div>
      {latestErrors.length > 0 && (
        <div className="stats-run-errors">
          <h4 className="stats-subsection-title">Latest run errors</h4>
          <ul className="stats-error-list">
            {latestErrors.map((err, index) => (
              <li className="stats-error-row" key={index}>
                {err.stage}: {err.message}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
};

const RunRow = ({ run }) => {
  const counts = run.counts || {};
  const errorCount = run.errors ? run.errors.length : 0;

  return (
    <div className="stats-run-row">
      <span className={`stats-badge stats-badge-${runStatusClass(run.status)}`}>
        {runStatusLabel(run.status)}
      </span>
      <span className="stats-run-trigger">{run.trigger}</span>
      <span className="stats-run-started">{run.started_at ? formatTimeAgo(run.started_at) : "—"}</span>
      <span className="stats-run-duration">{formatDuration(run.duration_seconds)}</span>
      <span className="stats-run-counts">
        ingested {counts.ingested ?? 0} / scored {counts.scored ?? 0}
      </span>
      <span className="stats-run-errors-count">
        {errorCount} error{errorCount === 1 ? "" : "s"}
      </span>
    </div>
  );
};

const ConfigSection = ({ config }) => {
  const data = config || {};

  return (
    <section className="stats-section">
      <h3 className="stats-section-title">Config</h3>
      <div className="stats-grid">
        {CONFIG_FIELDS.map((key) => (
          <div className="stats-kv" key={key}>
            <span className="stats-kv-label">{configLabel(key)}</span>
            <span className="stats-kv-value">{formatConfigValue(data[key])}</span>
          </div>
        ))}
      </div>
    </section>
  );
};

const STAGE_LABELS = {
  ingest: "Ingest sources",
  embed: "Embed items",
  reap: "Reap orphans",
  group: "Group into stories",
  score: "Filter & score",
};

const stageLabel = (name) => STAGE_LABELS[name] || name;

const STAGE_STATUS_LABELS = {
  idle: "Idle",
  running: "Running",
  done: "Done",
  stopped: "Stopped",
  error: "Error",
};

const stageStatusLabel = (status) => STAGE_STATUS_LABELS[status] || status;

const COUNT_LABELS = {
  ingested: "Ingested",
  deduped: "Deduped",
  embedded: "Embedded",
  stories_created: "Stories created",
  stories_updated: "Stories updated",
  filtered_out: "Filtered out",
  scored: "Scored",
  orphans_reaped: "Orphans reaped",
};

const countLabel = (key) => COUNT_LABELS[key] || key;

const LLM_SITE_LABELS = {
  filter: "Filter",
  verdict: "Verdict",
  score: "Score",
};

const llmSiteLabel = (site) => LLM_SITE_LABELS[site] || site;

const RUN_STATUS_LABELS = {
  running: "Running",
  success: "Success",
  error: "Error",
  stopped: "Stopped",
};

const runStatusLabel = (status) => RUN_STATUS_LABELS[status] || status || "Unknown";

const runStatusClass = (status) => {
  if (status === "running") return "running";
  if (status === "success") return "done";
  if (status === "error") return "error";
  return "idle";
};

const CONFIG_LABELS = {
  poll_interval_minutes: "Poll interval (min)",
  sim_high: "Similarity high",
  sim_low: "Similarity low",
  active_window_hours: "Active window (h)",
  decay_half_life_hours: "Decay half-life (h)",
  embed_model: "Embed model",
  filter_model: "Filter model",
  scoring_model: "Scoring model",
};

const configLabel = (key) => CONFIG_LABELS[key] || key;

const formatConfigValue = (value) => {
  if (value === null || value === undefined || value === "") return "—";
  return value;
};

const runBadge = (stats) => {
  if (stats.running) return { label: "Running", className: "running" };
  if (stats.paused) return { label: "Paused", className: "paused" };
  return { label: "Idle", className: "idle" };
};

// finishedAt is null while a run/stage is still in progress, so the elapsed
// time is measured against now instead.
const computeElapsedSeconds = (startedAt, finishedAt) => {
  if (!startedAt) return null;
  const start = new Date(startedAt).getTime();
  const end = finishedAt ? new Date(finishedAt).getTime() : Date.now();
  if (Number.isNaN(start) || Number.isNaN(end)) return null;
  return (end - start) / 1000;
};

const formatDuration = (seconds) => {
  if (seconds === null || seconds === undefined || Number.isNaN(seconds)) return "--:--";
  const total = Math.max(0, Math.round(seconds));
  const minutes = Math.floor(total / 60);
  const secs = total % 60;
  return `${minutes}:${String(secs).padStart(2, "0")}`;
};

export default PipelineStatsPanel;
