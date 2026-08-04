import type { WeakTopics as Data } from "../api/types";

function freshness(days: number | null): string {
  if (days === null) return "never solved";
  if (days === 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 30) return `${days}d ago`;
  if (days < 365) return `${Math.round(days / 30)}mo ago`;
  return `${Math.round(days / 365)}y ago`;
}

// Red where weak, green where strong, so the eye lands on what needs work.
function weaknessColour(weakness: number): string {
  if (weakness >= 0.6) return "#ef5b5b";
  if (weakness >= 0.35) return "#e0a13a";
  return "#3fb27f";
}

export function WeakTopics({ data }: { data: Data }) {
  if (!data.topics.length) {
    return (
      <section className="card">
        <header className="card-head">
          <h2>Weakest topics</h2>
        </header>
        <p className="muted">
          Not enough attempts yet — a topic needs at least {data.min_attempts}{" "}
          to be scored.
        </p>
      </section>
    );
  }

  return (
    <section className="card">
      <header className="card-head">
        <h2>Weakest topics</h2>
        <span className="muted small">
          by accuracy and recency · {data.total_topics} scored
        </span>
      </header>

      <table className="topics">
        <thead>
          <tr>
            <th>Topic</th>
            <th>Accuracy</th>
            <th>Solved</th>
            <th>Last</th>
          </tr>
        </thead>
        <tbody>
          {data.topics.map((t) => (
            <tr key={t.tag}>
              <td>
                <span
                  className="dot"
                  style={{ background: weaknessColour(t.weakness) }}
                  title={`weakness ${t.weakness}`}
                />
                {t.tag}
              </td>
              <td>
                <div className="acc">
                  <div className="acc-bar">
                    <div
                      style={{
                        width: `${t.accuracy * 100}%`,
                        background: weaknessColour(t.weakness),
                      }}
                    />
                  </div>
                  <span className="small muted">
                    {(t.accuracy * 100).toFixed(0)}%
                  </span>
                </div>
              </td>
              <td className="small muted">
                {t.solved}/{t.attempts}
              </td>
              <td className="small muted">
                {freshness(t.days_since_last_solve)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {data.skipped_low_volume > 0 && (
        <p className="muted small skipped">
          {data.skipped_low_volume} topic
          {data.skipped_low_volume === 1 ? "" : "s"} hidden — fewer than{" "}
          {data.min_attempts} attempts, so accuracy would be noise.
        </p>
      )}
    </section>
  );
}
