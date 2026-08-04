import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { RatingDistribution, TagBreakdown, Timeline } from "../api/types";
import { useThemeTokens, type ChartTokens } from "../theme";

/* Recharts writes its colours into SVG attributes, where `var(--border)` is
   not resolved. So the theme is read out of the cascade first and handed over
   as plain values. */

function axis(t: ChartTokens) {
  return { stroke: t.muted, fontSize: 12 };
}

function tooltip(t: ChartTokens) {
  return {
    background: t.surface,
    border: `1px solid ${t.border}`,
    borderRadius: 8,
    color: t.text,
  };
}

export function TagChart({ data }: { data: TagBreakdown }) {
  const t = useThemeTokens();
  if (!data.tags.length) return <Empty note="No tags yet." />;

  // Sized to the longest label rather than fixed: "dp" and "constructive
  // algorithms" need very different gutters, and a fixed 150px either clips
  // the long ones or wastes a third of a narrow column on the short ones.
  const labelWidth = Math.min(
    150,
    Math.max(70, ...data.tags.map((tag) => tag.tag.length * 6.6 + 12)),
  );

  return (
    <ChartCard
      title="Strongest tags"
      note={`${data.total_tags} tags seen`}
      height={Math.max(240, data.tags.length * 28)}
    >
      <BarChart data={data.tags} layout="vertical" margin={{ left: 8, right: 16 }}>
        <CartesianGrid stroke={t.border} horizontal={false} />
        <XAxis type="number" {...axis(t)} />
        <YAxis type="category" dataKey="tag" width={labelWidth} {...axis(t)} />
        <Tooltip contentStyle={tooltip(t)} cursor={{ fill: t["surface-2"] }} />
        <Bar dataKey="solved_count" name="solved" fill={t.accent} radius={[0, 4, 4, 0]} />
      </BarChart>
    </ChartCard>
  );
}

function labelColour(t: ChartTokens, label: string): string {
  return { Easy: t.ok, Medium: t.warn, Hard: t.danger }[label] ?? t.accent;
}

function LeetCodeLabels({ data }: { data: RatingDistribution }) {
  const t = useThemeTokens();
  if (!data.labels.length) return null;
  const total = data.labels.reduce((sum, l) => sum + l.solved_count, 0);

  return (
    <div className="labels">
      {data.labels.map((l) => (
        <div key={l.label} className="label-row">
          <span className="small" style={{ color: labelColour(t, l.label) }}>
            {l.label}
          </span>
          <div className="label-bar">
            <div
              style={{
                width: `${(l.solved_count / total) * 100}%`,
                background: labelColour(t, l.label),
              }}
            />
          </div>
          <span className="small muted">{l.solved_count}</span>
        </div>
      ))}
    </div>
  );
}

export function RatingChart({ data }: { data: RatingDistribution }) {
  const t = useThemeTokens();

  // A LeetCode-only user has no numeric ratings at all, so the labelled
  // breakdown stands in for the histogram rather than showing an empty chart.
  if (!data.buckets.length) {
    return data.labels.length ? (
      <section className="card">
        <header className="card-head">
          <h2>Difficulty</h2>
          <span className="muted small">LeetCode</span>
        </header>
        <LeetCodeLabels data={data} />
      </section>
    ) : (
      <Empty note="No rated problems yet." />
    );
  }

  // Codeforces colours ratings by tier; echoing that makes the histogram
  // readable at a glance to anyone who uses the site.
  const colourFor = (rating: number) =>
    rating >= 2400
      ? t.danger
      : rating >= 1900
        ? t.violet
        : rating >= 1600
          ? t.accent
          : t.ok;

  return (
    <ChartCard
      title="Difficulty distribution"
      note={data.unrated_count ? `${data.unrated_count} unrated` : undefined}
      height={280}
    >
      <BarChart data={data.buckets} margin={{ left: 0, right: 8 }}>
        <CartesianGrid stroke={t.border} vertical={false} />
        <XAxis dataKey="rating" {...axis(t)} />
        <YAxis {...axis(t)} />
        <Tooltip contentStyle={tooltip(t)} cursor={{ fill: t["surface-2"] }} />
        <Bar dataKey="solved_count" name="solved" radius={[4, 4, 0, 0]}>
          {data.buckets.map((b) => (
            <Cell key={b.rating} fill={colourFor(b.rating)} />
          ))}
        </Bar>
      </BarChart>
    </ChartCard>
  );
}

export function ActivityChart({ data }: { data: Timeline }) {
  const t = useThemeTokens();
  if (!data.points.length) return <Empty note="No activity in this window." />;

  return (
    <ChartCard title="Activity" note={`last ${data.days} days`} height={240}>
      <BarChart data={data.points} margin={{ left: 0, right: 8 }}>
        <CartesianGrid stroke={t.border} vertical={false} />
        <XAxis dataKey="day" {...axis(t)} minTickGap={40} />
        <YAxis allowDecimals={false} {...axis(t)} />
        <Tooltip contentStyle={tooltip(t)} cursor={{ fill: t["surface-2"] }} />
        <Bar dataKey="solved_count" name="solved" fill={t.ok} radius={[3, 3, 0, 0]} />
      </BarChart>
    </ChartCard>
  );
}

function ChartCard({
  title,
  note,
  height,
  children,
}: {
  title: string;
  note?: string;
  height: number;
  children: React.ReactElement;
}) {
  return (
    <section className="card">
      <header className="card-head">
        <h2>{title}</h2>
        {note && <span className="muted small">{note}</span>}
      </header>
      {/* An explicit height, not just min-height: the chart inside sizes itself
          as a percentage of its parent, and a percentage of an auto height is
          zero. Inside a stretched grid card, `flex: 1` overrides this and lets
          the plot grow to fill the card instead. */}
      <div className="chart-fill" style={{ height, minHeight: height }}>
        <ResponsiveContainer width="100%" height="100%">
          {children}
        </ResponsiveContainer>
      </div>
    </section>
  );
}

function Empty({ note }: { note: string }) {
  return (
    <section className="card">
      <p className="muted">{note}</p>
    </section>
  );
}
