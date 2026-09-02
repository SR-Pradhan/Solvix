import { useState } from "react";

import type { Recommendations as Data } from "../api/types";

// Ten identical rows is a wall; five is a shortlist you might actually pick from.
const SHOWN = 5;

export function Recommendations({ data }: { data: Data }) {
  // Before the early return: hooks must run in the same order every render.
  const [expanded, setExpanded] = useState(false);

  if (data.note) {
    return (
      <section className="card">
        <header className="card-head">
          <h2>Recommended next</h2>
        </header>
        <p className="muted">{data.note}</p>
      </section>
    );
  }

  return (
    <section className="card">
      <header className="card-head">
        <h2>Recommended next</h2>
        <span className="muted small">
          rated ~{data.target_rating}, from your weakest tags
        </span>
      </header>

      <div className="chips">
        {data.weak_tags.map((t) => (
          <span key={t.tag} className="chip" title={`${t.solved_count} solved`}>
            {t.tag}
          </span>
        ))}
      </div>

      {data.problems.length === 0 ? (
        <p className="muted">
          Nothing left unsolved in this range. You have cleared it.
        </p>
      ) : (
        <ul className="rows">
          {(expanded ? data.problems : data.problems.slice(0, SHOWN)).map((p) => (
            /* Unsolved and suggested, so the same accent as a planned task:
               something to go and do. */
            <li key={p.problem_id} className="row row-todo">
              <div className="row-head">
                <a
                  className="row-title"
                  href={p.url}
                  target="_blank"
                  rel="noreferrer"
                >
                  {p.name}
                </a>
                <span className="rating-pill">{p.rating}</span>
                <a className="row-action" href={p.url} target="_blank" rel="noreferrer">
                  Open <span aria-hidden="true">↗</span>
                </a>
              </div>
              <div className="tag-chips">
                {p.matched_tags.map((t) => (
                  <span key={t} className="tag-chip">{t}</span>
                ))}
              </div>
            </li>
          ))}
        </ul>
      )}
      {data.problems.length > SHOWN && (
        <button type="button" className="show-more" onClick={() => setExpanded(!expanded)}>
          {expanded ? "Show fewer" : `Show ${data.problems.length - SHOWN} more`}
        </button>
      )}
    </section>
  );
}
