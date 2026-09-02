import { useState } from "react";

import type { Platform, WeakTopics as Data } from "../api/types";
import { ProblemsToggle } from "./ProblemsToggle";
import { TopicProblems } from "./TopicProblems";

// Plain words instead of a 0-1 score: nobody reads "weakness 0.78".
const STATUS_COLOUR: Record<string, string> = {
  "Needs work": "var(--danger)",
  Rusty: "var(--warn)",
  Solid: "var(--ok)",
};

// The row's left edge, in the same three colours. Scanning a column of edges
// is faster than reading a column of words.
const ROW_TONE: Record<string, string> = {
  "Needs work": "row-alert",
  Rusty: "row-stale",
  Solid: "row-done",
};

function freshness(days: number | null): string {
  if (days === null) return "never";
  if (days === 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 14) return `${days} days ago`;
  if (days < 60) return `${Math.round(days / 7)} weeks ago`;
  if (days < 365) return `${Math.round(days / 30)} months ago`;
  return `over a year ago`;
}

function reason(
  status: string,
  accuracy: number | null,
  days: number | null,
): string {
  if (accuracy !== null && accuracy < 0.5) {
    return `only ${Math.round(accuracy * 100)}% of attempts pass`;
  }
  if (status === "Solid") return `going well`;
  return `not practised since ${freshness(days)}`;
}

// Enough rows to fill the card next to the tag chart, so the toggle sits at
// the bottom rather than leaving a gap under it.
const ROWS_SHOWN = 8;

export function WeakTopics({
  data,
  platform,
}: {
  data: Data;
  platform: Platform | null;
}) {
  // Declared before any early return: hooks must run in the same order on
  // every render, and this list is empty until the first import finishes.
  const [expanded, setExpanded] = useState(false);
  const [openTag, setOpenTag] = useState<string | null>(null);

  if (!data.topics.length) {
    return (
      <section className="card">
        <header className="card-head">
          <h2>What to work on</h2>
        </header>
        <p className="muted">
          Not enough practice yet. A topic needs at least {data.min_attempts}{" "}
          attempts before Solvix can judge it.
        </p>
      </section>
    );
  }

  const accuracyIsReal = data.scored_on_accuracy > 0;
  const visible = expanded ? data.topics : data.topics.slice(0, ROWS_SHOWN);
  const hidden = data.topics.length - visible.length;

  return (
    <section className="card">
      <header className="card-head">
        <h2>What to work on</h2>
        <span className="muted small">weakest first</span>
      </header>

      <ul className="rows">
        {visible.map((t) => (
          /* The edge repeats the status the badge names. Both stay: colour
             alone is not readable to everyone, and a word alone does not carry
             down a column at a glance. */
          <li key={t.tag} className={`row ${ROW_TONE[t.status] ?? "row-todo"}`}>
            <div className="row-head row-head-cols">
              <span className="row-title">{t.tag}</span>
              <span
                className="badge"
                style={{
                  color: STATUS_COLOUR[t.status],
                  borderColor: STATUS_COLOUR[t.status],
                }}
              >
                {t.status}
              </span>
              <span className="muted small">
                {reason(t.status, t.accuracy, t.days_since_last_solve)}
              </span>
              <ProblemsToggle
                open={openTag === t.tag}
                label={t.tag}
                onClick={() => setOpenTag(openTag === t.tag ? null : t.tag)}
              />
            </div>
            {/* The words say "37% pass"; the bar lets you compare eight rows
                without reading eight numbers. Only where a pass rate exists —
                a recency-only topic has nothing to draw. */}
            {t.accuracy !== null && (
              <div
                className="meter"
                role="img"
                aria-label={`${Math.round(t.accuracy * 100)}% of attempts pass`}
              >
                <div
                  className="meter-fill"
                  style={{
                    width: `${Math.round(t.accuracy * 100)}%`,
                    background: STATUS_COLOUR[t.status],
                  }}
                />
              </div>
            )}
            {openTag === t.tag && (
              <TopicProblems
                tag={t.tag}
                // With no filter chosen, ask the platform the tag came from:
                // capitalised tags are LeetCode's, lowercase are Codeforces'.
                platform={
                  platform ??
                  (t.tag === t.tag.toLowerCase() ? "codeforces" : "leetcode")
                }
              />
            )}
          </li>
        ))}
      </ul>

      {(hidden > 0 || expanded) && (
        <button
          type="button"
          className="show-more"
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? "Show fewer" : `Show ${hidden} more`}
        </button>
      )}

      {!accuracyIsReal && (
        <p className="muted small skipped">
          Ranked by how long since you practised each topic. LeetCode only
          records problems you solved, so there is no pass rate to judge.
          Connect Codeforces for that.
        </p>
      )}
    </section>
  );
}
