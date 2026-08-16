import { useState } from "react";

import type { Reminders as Data } from "../api/types";
import { ProblemsToggle } from "./ProblemsToggle";
import { RevisionProblems } from "./RevisionProblems";

export function Reminders({ data }: { data: Data }) {
  // Declared before the empty-list early return so hook order stays stable.
  const [openTag, setOpenTag] = useState<string | null>(null);

  if (!data.reminders.length) {
    return (
      <section className="card">
        <header className="card-head">
          <h2>Revise today</h2>
        </header>
        <p className="muted">
          Nothing due. Everything you have practised is still fresh.
        </p>
      </section>
    );
  }

  return (
    <section className="card">
      <header className="card-head">
        <h2>Revise today</h2>
        <span className="muted small">
          {data.reminders.length === 1 ? "1 reminder" : `${data.reminders.length} reminders`}
        </span>
      </header>

      <ul className="rows">
        {data.reminders.map((r) => (
          <li
            key={`${r.kind}:${r.subject}`}
            /* The left edge says which kind this is before any of the words
               do: amber for a topic going stale, accent for a problem whose
               revision has simply come round. */
            className={r.kind === "topic" ? "row row-stale" : "row row-todo"}
          >
            <div className="row-head">
              {/* A revisit reminder that does not open the problem leaves the
                  reader to go and find it, which is where a reminder gets
                  ignored. Topics have no page to link to, so they stay text. */}
              {r.url ? (
                <a
                  className="row-title"
                  href={r.url}
                  target="_blank"
                  rel="noreferrer"
                >
                  {r.title}
                </a>
              ) : (
                <span className="row-title">{r.title}</span>
              )}
              <span className="muted small">{r.reason}</span>
              {r.kind === "topic" && (
                <ProblemsToggle
                  open={openTag === r.subject}
                  label={r.title}
                  onClick={() =>
                    setOpenTag(openTag === r.subject ? null : r.subject)
                  }
                />
              )}
            </div>
            {openTag === r.subject && <RevisionProblems tag={r.subject} />}
          </li>
        ))}
      </ul>
    </section>
  );
}
