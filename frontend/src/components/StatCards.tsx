import type { Stats, WeakTopics } from "../api/types";

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

function windowLabel(days: number): string {
  if (days % 7 === 0) {
    const weeks = days / 7;
    return weeks === 1 ? "a week" : `${weeks} weeks`;
  }
  return `${days} days`;
}

// Name every stale topic while the list stays readable; past that, name a
// few and count the rest.
const NAMES_SHOWN = 6;

function staleSub(topics: WeakTopics | undefined): string {
  if (!topics) return "";

  const age = windowLabel(topics.stale_horizon_days);
  if (topics.stale_count === 0) return "all revised this week";

  const names = topics.stale_examples;
  if (!names.length) return `not touched in ${age}`;

  if (topics.stale_count <= NAMES_SHOWN) {
    return `${names.join(", ")}. Not touched in ${age}`;
  }

  const shown = names.slice(0, NAMES_SHOWN - 1).join(", ");
  const rest = topics.stale_count - (NAMES_SHOWN - 1);
  return `${shown} and ${rest} more. Not touched in ${age}`;
}

export function StatCards({
  stats,
  topics,
}: {
  stats: Stats;
  topics?: WeakTopics;
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
          value={topics === undefined ? "0" : String(topics.total_topics)}
          sub="distinct tags covered"
        />
      )}

      <Card
        label="Due for revision"
        value={
          topics === undefined
            ? "0"
            : `${topics.stale_count} ${topics.stale_count === 1 ? "topic" : "topics"}`
        }
        sub={staleSub(topics)}
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
