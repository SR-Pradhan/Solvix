import type { Reminders as Data } from "../api/types";

const KIND_LABELS: Record<string, string> = {
  problem: "Revisit",
  topic: "Topic",
};

export function Reminders({ data }: { data: Data }) {
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

      <ul className="topic-list">
        {data.reminders.map((r) => (
          <li key={`${r.kind}:${r.subject}`}>
            <span className="topic-name">{r.title}</span>
            <span className="badge">{KIND_LABELS[r.kind] ?? r.kind}</span>
            <span className="muted small topic-why">{r.reason}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
