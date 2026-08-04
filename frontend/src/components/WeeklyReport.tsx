import type { WeeklyReport as Data } from "../api/types";

const PLATFORM_LABELS: Record<string, string> = {
  codeforces: "Codeforces",
  leetcode: "LeetCode",
};

function formatRange(start: string, end: string): string {
  const opts: Intl.DateTimeFormatOptions = { day: "numeric", month: "short" };
  const from = new Date(start).toLocaleDateString(undefined, opts);
  const to = new Date(end).toLocaleDateString(undefined, opts);
  return `${from} to ${to}`;
}

function TopicRow({ label, tags }: { label: string; tags: string[] }) {
  if (!tags.length) return null;
  return (
    <div className="week-topics">
      <span className="stat-label">{label}</span>
      <div className="chips">
        {tags.map((tag) => (
          <span key={tag} className="chip">
            {tag}
          </span>
        ))}
      </div>
    </div>
  );
}

export function WeeklyReport({ data }: { data: Data }) {
  const platforms = Object.entries(data.by_platform);

  return (
    <section className="card">
      <header className="card-head">
        <h2>This week</h2>
        <span className="muted small">
          {formatRange(data.week_start, data.week_end)}
          {data.in_progress ? ", still going" : ""}
        </span>
      </header>

      <div className="week-figures">
        <div>
          <span className="stat-value">{data.problems_solved}</span>
          <span className="muted small">
            {data.problems_solved === 1 ? "new problem" : "new problems"}
          </span>
        </div>
        <div>
          <span className="stat-value">{data.active_days}</span>
          <span className="muted small">
            {data.active_days === 1 ? "active day" : "active days"}
          </span>
        </div>
      </div>

      {platforms.length > 0 && (
        <p className="muted small">
          {platforms
            .map(([key, n]) => `${n} on ${PLATFORM_LABELS[key] ?? key}`)
            .join(", ")}
        </p>
      )}

      {data.problems_solved === 0 && (
        <p className="muted">
          Nothing solved yet this week. Your plan above is a good place to start.
        </p>
      )}

      <TopicRow label="Needs work" tags={data.weakest.map((t) => t.tag)} />
      <TopicRow label="Going well" tags={data.strongest.map((t) => t.tag)} />
    </section>
  );
}
