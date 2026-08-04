import { useState, type ReactNode } from "react";

import type { Stats, WeakTopics } from "../api/types";

function Card({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub?: ReactNode;
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

// Beyond this the card grows taller than its neighbours, so the rest hide
// behind a toggle rather than being dropped.
const NAMES_SHOWN = 5;

function DueCard({ topics }: { topics?: WeakTopics }) {
  const [expanded, setExpanded] = useState(false);

  if (!topics) return <Card label="Due for revision" value="0" />;

  const { stale_count: count, stale_topics: names } = topics;
  const age = windowLabel(topics.stale_horizon_days);
  const value = `${count} ${count === 1 ? "topic" : "topics"}`;

  if (count === 0) {
    return (
      <Card label="Due for revision" value={value} sub="all revised this week" />
    );
  }

  const hidden = count - NAMES_SHOWN;
  const visible = expanded ? names : names.slice(0, NAMES_SHOWN);

  return (
    <Card
      label="Due for revision"
      value={value}
      sub={
        <>
          {visible.join(", ")}
          {hidden > 0 && (
            <>
              {" "}
              <button
                type="button"
                className="link inline"
                onClick={() => setExpanded(!expanded)}
              >
                {expanded ? "show fewer" : `and ${hidden} more`}
              </button>
            </>
          )}
          . Not touched in {age}
        </>
      }
    />
  );
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

      <DueCard topics={topics} />

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
