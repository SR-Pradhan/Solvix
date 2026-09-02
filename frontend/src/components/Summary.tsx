import type { DailyPlan, Reminders, Stats, User } from "../api/types";

function greeting(): string {
  const h = new Date().getHours();
  if (h < 5) return "Late night";
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

/** Everything the reader wants before the cards: who, how long, what next.
 *
 * A dashboard that opens straight onto twelve equal cards makes the reader do
 * the summarising. This does it for them in one line — the streak is the
 * number people actually check, and the focus is what the plan or the top
 * reminder is asking for today.
 */
export function Summary({
  user,
  stats,
  reminders,
  plan,
}: {
  user: User;
  stats: Stats;
  reminders: Reminders;
  plan: DailyPlan | null;
}) {
  const name = (user.display_name ?? user.email).split(/[\s@]/)[0];
  const focus = plan?.focus?.[0] ?? reminders.reminders[0]?.title ?? null;
  const due = reminders.reminders.length;
  const streak = stats.current_streak_days;

  return (
    <section className="summary" aria-label="Today at a glance">
      <div>
        <h2 className="summary-greeting">
          {greeting()}, {name}.
        </h2>
        <p className="summary-line muted">
          {streak > 0
            ? `${streak}-day streak${streak === stats.longest_streak_days && streak > 1 ? " — your best" : ""}. `
            : "No streak running. "}
          {due > 0 ? `${due} thing${due > 1 ? "s" : ""} to revise today. ` : "Nothing due today. "}
          {focus ? (
            <>
              Focus: <strong>{focus}</strong>.
            </>
          ) : null}
        </p>
      </div>
      <div className="summary-figures">
        <div className="summary-figure">
          <span className="summary-number">{streak}</span>
          <span className="summary-label">day streak</span>
        </div>
        <div className="summary-figure">
          <span className="summary-number">{stats.problems_solved}</span>
          <span className="summary-label">solved</span>
        </div>
        <div className="summary-figure">
          <span className="summary-number">{due}</span>
          <span className="summary-label">due today</span>
        </div>
      </div>
    </section>
  );
}
