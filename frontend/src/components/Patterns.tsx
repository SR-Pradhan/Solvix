import type { Pattern, Patterns as Data } from "../api/types";

// Named for how the combination behaves, in the same three colours the rest of
// the dashboard uses for severity.
const SEVERITY_COLOUR: Record<string, string> = {
  "Breaks down": "var(--danger)",
  Struggles: "var(--warn)",
  Slips: "var(--muted)",
};

const ROW_TONE: Record<string, string> = {
  "Breaks down": "row-alert",
  Struggles: "row-stale",
  Slips: "row-todo",
};

function percent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

/** The one sentence that makes the number mean something.
 *
 * The score is a comparison, so the row has to show both halves of it — a bare
 * "34%" reads as an ordinary weak spot, which is the one thing this card is
 * built to distinguish itself from.
 */
function comparison(pattern: Pattern): string {
  const alone = pattern.parts
    .map((part) => `${part.tag} ${percent(part.accuracy)}`)
    .join(", ");
  return `${percent(pattern.accuracy)} together over ${pattern.attempts} attempts — alone, ${alone}`;
}

export function Patterns({ data }: { data: Data }) {
  if (!data.patterns.length) {
    return (
      <section className="card">
        <header className="card-head">
          <h2>Tricky combinations</h2>
        </header>
        {data.pairs_considered > 0 ? (
          /* A real finding, not missing data: enough pairs were weighed and
             none of them underperformed. Saying "no data" here would report a
             good result as a broken one. */
          <p className="muted">
            Nothing stands out. Across {data.pairs_considered} technique pairs,
            none is meaningfully harder than the techniques that make it up.
          </p>
        ) : (
          <p className="muted">
            Needs Codeforces practice. This compares how often you pass when two
            techniques appear together against how often you pass them
            separately, so it only works where failed attempts are recorded —
            LeetCode only stores problems you solved.
          </p>
        )}
      </section>
    );
  }

  return (
    <section className="card">
      <header className="card-head">
        <h2>Tricky combinations</h2>
        <span className="muted small">biggest drop first</span>
      </header>

      <ul className="rows">
        {data.patterns.map((pattern) => (
          <li
            key={pattern.tags.join("+")}
            className={`row ${ROW_TONE[pattern.severity] ?? "row-todo"}`}
          >
            <div className="row-head row-head-cols">
              <span className="row-title">{pattern.tags.join(" + ")}</span>
              <span
                className="badge"
                style={{
                  color: SEVERITY_COLOUR[pattern.severity],
                  borderColor: SEVERITY_COLOUR[pattern.severity],
                }}
              >
                {pattern.severity}
              </span>
              <span className="muted small">{comparison(pattern)}</span>
            </div>
          </li>
        ))}
      </ul>

      <p className="muted small skipped">
        These are pairs you handle worse together than either technique alone,
        so they are worth drilling as a combination rather than separately.
        Codeforces only — LeetCode records no failed attempts to measure.
      </p>
    </section>
  );
}
