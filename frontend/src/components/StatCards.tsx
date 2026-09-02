import { useState, type ReactNode } from "react";

import type {
  LeetCodeProfile,
  Platform,
  Stats,
  WeakTopics,
} from "../api/types";

function Card({
  label,
  value,
  sub,
  delta,
}: {
  label: string;
  value: string;
  sub?: ReactNode;
  // Movement, shown beside the figure: a total on its own says where you are,
  // not which way you are going.
  delta?: string;
}) {
  return (
    <div className="card stat">
      <span className="stat-label">{label}</span>
      <span className="stat-value">
        {value}
        {delta && <span className="stat-delta">{delta}</span>}
      </span>
      {sub && <span className="muted small">{sub}</span>}
    </div>
  );
}

/** "1 day", not "1 days". A number is only ever plural above one, and a stat
 *  card that gets its own grammar wrong undercuts every figure beside it. */
function days(n: number): string {
  return `${n} ${n === 1 ? "day" : "days"}`;
}

function streakWord(current: number, longest: number): string {
  if (current === 0) return longest ? `best run was ${days(longest)}` : "";
  if (current >= longest) return "your best run yet";
  return `best run ${days(longest)}`;
}

// The parameter is not called `days`: that would shadow the helper above and
// quietly reintroduce the plural bug the day this is called with 1.
function windowLabel(span: number): string {
  if (span % 7 === 0) {
    const weeks = span / 7;
    return weeks === 1 ? "a week" : `${weeks} weeks`;
  }
  return days(span);
}

// Two, because the grid stretches every stat card to the tallest one: five
// topic names ran to three lines and left the other three cards with two lines
// of dead space under their own single line. The rest hide behind a toggle
// rather than being dropped.
const NAMES_SHOWN = 2;

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

/**
 * The real solved count, which the database alone cannot give.
 *
 * LeetHub only recorded problems solved after it was installed, so row counts
 * under-report a long-standing LeetCode account. Where a synced profile knows
 * the true total, swap the tracked LeetCode rows for it.
 */
function solvedTotal(
  stats: Stats,
  profile: LeetCodeProfile | null,
  platform: Platform | null,
): { value: number; untracked: number } {
  if (!profile || platform === "codeforces") {
    return { value: stats.problems_solved, untracked: 0 };
  }

  const untracked = profile.coverage.missing;

  if (platform === "leetcode") {
    return { value: profile.total_solved, untracked };
  }

  // Unfiltered: keep every other platform's real rows, replacing only the
  // LeetCode slice with the profile's authoritative count.
  return {
    value: stats.problems_solved - profile.coverage.tracked + profile.total_solved,
    untracked,
  };
}

export function StatCards({
  stats,
  topics,
  profile = null,
  platform = null,
  weekly = null,
}: {
  stats: Stats;
  topics?: WeakTopics;
  profile?: LeetCodeProfile | null;
  platform?: Platform | null;
  weekly?: { problems_solved: number } | null;
}) {
  const solved = solvedTotal(stats, profile, platform);
  // Every submission accepted means the source only records solutions that
  // passed, so a "100% acceptance" card would be measuring nothing.
  const failuresRecorded = stats.total_submissions > stats.accepted_submissions;

  return (
    <div className="stat-grid">
      <Card
        label="Problems solved"
        value={solved.value.toLocaleString()}
        delta={weekly && weekly.problems_solved > 0 ? `+${weekly.problems_solved} this week` : undefined}
        sub={
          solved.untracked > 0
            ? `${solved.untracked} solved before tracking began`
            : failuresRecorded
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
          stats.current_streak_days === 0 ? "None" : days(stats.current_streak_days)
        }
        sub={streakWord(stats.current_streak_days, stats.longest_streak_days)}
      />
    </div>
  );
}
