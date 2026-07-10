import { useCallback, useEffect, useRef, useState } from "react";

import {
  getPipelineStatus,
  logout,
  resumePipeline,
  stopPipeline,
  triggerPipelineRun,
} from "../api.js";
import { formatTimeAgo } from "../time.js";

const POLL_INTERVAL_MS = 5000;

const Header = ({ onRefreshed, onLogout }) => {
  const [status, setStatus] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const pollTimer = useRef(null);

  const loadStatus = useCallback(async () => {
    try {
      const body = await getPipelineStatus();
      setStatus(body);
      return body;
    } catch {
      return null;
    }
  }, []);

  useEffect(() => {
    loadStatus();
    return () => clearTimeout(pollTimer.current);
  }, [loadStatus]);

  const pollUntilFinished = useCallback(async () => {
    const body = await loadStatus();
    if (body && body.running) {
      pollTimer.current = setTimeout(pollUntilFinished, POLL_INTERVAL_MS);
      return;
    }
    setRefreshing(false);
    onRefreshed();
  }, [loadStatus, onRefreshed]);

  const startRefresh = async () => {
    if (refreshing) return;
    setRefreshing(true);
    try {
      await triggerPipelineRun();
    } catch {
      // 409 = already running — polling below still tracks it to completion
    }
    pollTimer.current = setTimeout(pollUntilFinished, POLL_INTERVAL_MS);
  };

  const submitLogout = async () => {
    try {
      await logout();
    } finally {
      onLogout();
    }
  };

  const paused = Boolean(status && status.paused);

  const togglePaused = async () => {
    try {
      await (paused ? resumePipeline() : stopPipeline());
    } catch {
      // status reload below re-syncs the button either way
    }
    loadStatus();
  };

  const lastRun = status && status.run ? status.run : null;

  return (
    <header id="app-header">
      <h1 id="app-title">NEWS</h1>
      <div id="header-status">
        {paused && <span className="paused-indicator">paused</span>}
        {status && status.running && <span className="run-indicator">updating…</span>}
        {!refreshing && lastRun && lastRun.finished_at && (
          <span className="last-run">updated {formatTimeAgo(lastRun.finished_at)}</span>
        )}
      </div>
      <div id="header-actions">
        <button className="header-btn" onClick={startRefresh} disabled={refreshing}>
          {refreshing ? "Refreshing…" : "Refresh"}
        </button>
        <button className="header-btn header-btn-secondary" onClick={togglePaused}>
          {paused ? "Resume" : "Stop"}
        </button>
        <button className="header-btn header-btn-secondary" onClick={submitLogout}>
          Logout
        </button>
      </div>
    </header>
  );
};

export default Header;
