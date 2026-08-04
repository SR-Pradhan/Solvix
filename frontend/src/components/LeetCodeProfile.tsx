import { useState } from "react";

import { ApiError, api } from "../api/client";
import type { LeetCodeProfile as Data } from "../api/types";
import { useAuth } from "../auth";

const BAR_COLOURS: Record<string, string> = {
  easy: "var(--ok)",
  medium: "var(--warn)",
  hard: "var(--danger)",
};

function Split({ label, value, total }: { label: string; value: number; total: number }) {
  return (
    <div className="label-row">
      <span className="small" style={{ color: BAR_COLOURS[label.toLowerCase()] }}>
        {label}
      </span>
      <div className="label-bar">
        <div
          style={{
            width: total ? `${(value / total) * 100}%` : 0,
            background: BAR_COLOURS[label.toLowerCase()],
          }}
        />
      </div>
      <span className="small muted">{value}</span>
    </div>
  );
}

export function LeetCodeProfile({
  data,
  onSynced,
}: {
  data: Data;
  onSynced: (next: Data) => void;
}) {
  const { token } = useAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function resync() {
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      onSynced(await api.syncLeetcodeProfile(token));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sync failed");
    } finally {
      setBusy(false);
    }
  }

  const { coverage } = data;

  return (
    <section className="card">
      <header className="card-head">
        <h2>LeetCode profile</h2>
        <span className="muted small">@{data.username}</span>
      </header>

      <div className="week-figures">
        <div>
          <span className="stat-value">{data.total_solved}</span>
          <span className="muted small">solved on LeetCode</span>
        </div>
        <div>
          <span className="stat-value">{coverage.tracked}</span>
          <span className="muted small">tracked in detail</span>
        </div>
      </div>

      <div className="labels" style={{ marginTop: 14 }}>
        <Split label="Easy" value={data.easy} total={data.total_solved} />
        <Split label="Medium" value={data.medium} total={data.total_solved} />
        <Split label="Hard" value={data.hard} total={data.total_solved} />
      </div>

      {data.hard === 0 && data.total_solved > 20 && (
        <p className="muted small skipped">
          You have not solved a Hard problem yet. Worth starting before
          interviews.
        </p>
      )}

      {coverage.missing > 0 && (
        <p className="muted small skipped">
          {coverage.missing} problems were solved before LeetHub was installed,
          so Solvix knows the count but not the dates. Topic timing is based on
          the {coverage.tracked} it can see ({coverage.percent}%).
        </p>
      )}

      {error && <p className="error small">{error}</p>}

      <button
        type="button"
        className="pill-btn plan-rebuild"
        onClick={resync}
        disabled={busy}
      >
        {busy ? "Syncing…" : "Refresh from LeetCode"}
      </button>
    </section>
  );
}
