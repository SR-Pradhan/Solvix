import type { DailyPlan as Data } from "../api/types";

function totalMinutes(data: Data): number {
  return data.tasks.reduce((sum, t) => sum + t.minutes, 0);
}

export function DailyPlan({
  data,
  onRegenerate,
  busy,
}: {
  data: Data;
  onRegenerate: () => void;
  busy: boolean;
}) {
  if (data.unavailable) {
    return (
      <section className="card">
        <header className="card-head">
          <h2>Today's plan</h2>
        </header>
        <p className="muted">{data.unavailable}</p>
      </section>
    );
  }

  const minutes = totalMinutes(data);

  return (
    <section className="card">
      <header className="card-head">
        <h2>Today's plan</h2>
        <span className="muted small">
          {minutes > 0 ? `about ${minutes} minutes` : ""}
        </span>
      </header>

      {data.focus.length > 0 && (
        <div className="chips">
          {data.focus.map((tag) => (
            <span key={tag} className="chip">
              {tag}
            </span>
          ))}
        </div>
      )}

      <ol className="plan-list">
        {data.tasks.map((task, i) => (
          <li key={i}>
            <div className="plan-head">
              <span className="plan-title">{task.title}</span>
              <span className="rating-pill">{task.minutes}m</span>
            </div>
            {task.detail && <p className="muted small plan-detail">{task.detail}</p>}
          </li>
        ))}
      </ol>

      {data.note && <p className="muted small plan-note">{data.note}</p>}

      <button
        type="button"
        className="link show-more"
        onClick={onRegenerate}
        disabled={busy}
      >
        {busy ? "Rebuilding…" : "Build a different plan"}
      </button>
    </section>
  );
}
