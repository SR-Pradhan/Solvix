import type { Stats } from "../api/types";

function Card({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <div className="card stat">
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value}</span>
      {sub && <span className="muted small">{sub}</span>}
    </div>
  );
}

function streakWord(current: number, longest: number): string {
  if (current === 0) return longest ? `best run was ${longest} days` : "";
  if (current >= longest) return "your best run yet";
  return `best run ${longest} days`;
}

export function StatCards({
  stats,
  topicsCovered,
}: {
  stats: Stats;
  topicsCovered?: number;
}) {
  // Every submission accepted means the source only records solutions that
  // passed, so a "100% acceptance" card would be measuring nothing.
  const failuresRecorded = stats.total_submissions > stats.accepted_submissions;

  return (
    <div className="stat-grid">
      <Card
        label="Problems solved"
        value={stats.problems_solved.toLocaleString()}
        sub={
          failuresRecorded
            ? `across ${stats.total_submissions.toLocaleString()} attempts`
            : undefined
        }
      />

      {failuresRecorded ? (
        <Card
          label="First-try success"
          value={`${Math.round(stats.acceptance_rate * 100)}%`}
          sub="of your submissions pass"
        />
      ) : (
        <Card
          label="Topics practised"
          value={topicsCovered === undefined ? "0" : String(topicsCovered)}
          sub="distinct tags covered"
        />
      )}

      <Card
        label="Typical difficulty"
        value={
          stats.avg_difficulty === null
            ? "Not rated"
            : String(stats.avg_difficulty)
        }
        sub={
          stats.max_difficulty === null
            ? "no Codeforces problems imported yet"
            : `Codeforces rating. Hardest so far ${stats.max_difficulty}`
        }
      />

      <Card
        label="Current streak"
        value={
          stats.current_streak_days === 0
            ? "None"
            : `${stats.current_streak_days} days`
        }
        sub={streakWord(stats.current_streak_days, stats.longest_streak_days)}
      />
    </div>
  );
}
