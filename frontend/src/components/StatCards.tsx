import type { Stats } from "../api/types";

function Card({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="card stat">
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value}</span>
      {sub && <span className="muted small">{sub}</span>}
    </div>
  );
}

export function StatCards({ stats }: { stats: Stats }) {
  return (
    <div className="stat-grid">
      <Card
        label="Problems solved"
        value={stats.problems_solved.toLocaleString()}
        sub={`${stats.accepted_submissions.toLocaleString()} accepted submissions`}
      />
      <Card
        label="Acceptance rate"
        value={`${(stats.acceptance_rate * 100).toFixed(1)}%`}
        sub={`of ${stats.total_submissions.toLocaleString()} submissions`}
      />
      <Card
        label="Avg difficulty"
        value={stats.avg_difficulty === null ? "—" : String(stats.avg_difficulty)}
        sub={stats.max_difficulty === null ? undefined : `peak ${stats.max_difficulty}`}
      />
      <Card
        label="Current streak"
        value={`${stats.current_streak_days}d`}
        sub={`longest ${stats.longest_streak_days}d`}
      />
    </div>
  );
}
