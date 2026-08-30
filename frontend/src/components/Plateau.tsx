import type { PlatformPlateau, Plateau as Data } from "../api/types";

const PLATFORM_NAME: Record<string, string> = {
  codeforces: "Codeforces",
  leetcode: "LeetCode",
};

// Only one of these is good news, so only one is green.
const STATUS_COLOUR: Record<string, string> = {
  Stretching: "var(--ok)",
  Plateaued: "var(--warn)",
  Coasting: "var(--danger)",
};

const ROW_TONE: Record<string, string> = {
  Stretching: "row-done",
  Plateaued: "row-stale",
  Coasting: "row-alert",
};

/** What the verdict means, in the reader's own numbers.
 *
 * The status word alone invites "says who?" — so each sentence quotes the
 * counts it was decided from. Coasting and plateauing get different advice on
 * purpose: one is revisiting solved ground, the other is being ready for the
 * next tier and not trying it.
 */
function explain(p: PlatformPlateau): string {
  const window = `in the last ${p.window_days} days`;

  if (p.status === "Coasting") {
    return `${p.below} of your last ${p.recent_solved} solves were below ${p.working_level}, which you have already shown you can do. Spend that time on ${p.next_level ?? "harder problems"} instead.`;
  }
  if (p.status === "Plateaued") {
    return `${p.at} of ${p.recent_solved} solves ${window} sat at ${p.working_level}, and ${p.above === 0 ? "none" : `only ${p.above}`} went higher. You look ready for ${p.next_level ?? "the next step"}.`;
  }
  if (p.status === "Stretching") {
    return p.next_level === null
      ? `You are working at the hardest tier there is.`
      : `${p.above} of ${p.recent_solved} solves ${window} were above ${p.working_level}. The difficulty is still climbing.`;
  }
  return `Only ${p.recent_solved} solves ${window} — not enough to judge which way the difficulty is going.`;
}

export function Plateau({ data }: { data: Data }) {
  if (!data.platforms.length) return null;

  return (
    <section className="card">
      <header className="card-head">
        <h2>Are you still improving?</h2>
        <span className="muted small">last {data.window_days} days</span>
      </header>

      <ul className="rows">
        {data.platforms.map((p) => (
          <li key={p.platform} className={`row ${ROW_TONE[p.status] ?? "row-todo"}`}>
            <div className="row-head row-head-cols">
              <span className="row-title">
                {PLATFORM_NAME[p.platform] ?? p.platform}
              </span>
              <span
                className="badge"
                style={{
                  color: STATUS_COLOUR[p.status],
                  borderColor: STATUS_COLOUR[p.status],
                }}
              >
                {p.status}
              </span>
              <span className="muted small">{explain(p)}</span>
            </div>
          </li>
        ))}
      </ul>

      <p className="muted small skipped">
        Your level is the hardest difficulty you have solved enough problems at
        for it to count. Each platform is judged on its own scale — a LeetCode
        Medium and a Codeforces 1600 are not the same claim.
      </p>
    </section>
  );
}
