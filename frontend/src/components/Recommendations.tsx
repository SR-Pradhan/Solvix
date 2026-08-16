import type { Recommendations as Data } from "../api/types";

export function Recommendations({ data }: { data: Data }) {
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
          {data.problems.map((p) => (
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
              </div>
              <p className="muted small row-detail">
                {p.matched_tags.join(", ")}
              </p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
