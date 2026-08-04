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

const AXIS = { stroke: "#7c88a1", fontSize: 12 };
const GRID = "#232a3a";

const tooltipStyle = {
  background: "#141922",
  border: "1px solid #2a3242",
  borderRadius: 8,
  color: "#e7ecf5",
};

export function TagChart({ data }: { data: TagBreakdown }) {
  if (!data.tags.length) return <Empty note="No tags yet." />;

  return (
    <ChartCard
      title="Strongest tags"
      note={`${data.total_tags} tags seen`}
      height={Math.max(240, data.tags.length * 28)}
    >
      <BarChart data={data.tags} layout="vertical" margin={{ left: 8, right: 16 }}>
        <CartesianGrid stroke={GRID} horizontal={false} />
        <XAxis type="number" {...AXIS} />
        <YAxis type="category" dataKey="tag" width={150} {...AXIS} />
        <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "#1b2130" }} />
        <Bar dataKey="solved_count" name="solved" fill="#5b8def" radius={[0, 4, 4, 0]} />
      </BarChart>
    </ChartCard>
  );
}

export function RatingChart({ data }: { data: RatingDistribution }) {
  if (!data.buckets.length) return <Empty note="No rated problems yet." />;

  // Codeforces colours ratings by tier; echoing that makes the histogram
  // readable at a glance to anyone who uses the site.
  const colourFor = (rating: number) =>
    rating >= 2400 ? "#ef5b5b" : rating >= 1900 ? "#c07be0" : rating >= 1600 ? "#5b8def" : "#3fb27f";

  return (
    <ChartCard
      title="Difficulty distribution"
      note={data.unrated_count ? `${data.unrated_count} unrated` : undefined}
      height={280}
    >
      <BarChart data={data.buckets} margin={{ left: 0, right: 8 }}>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey="rating" {...AXIS} />
        <YAxis {...AXIS} />
        <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "#1b2130" }} />
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
  if (!data.points.length) return <Empty note="No activity in this window." />;

  return (
    <ChartCard title="Activity" note={`last ${data.days} days`} height={240}>
      <BarChart data={data.points} margin={{ left: 0, right: 8 }}>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey="day" {...AXIS} minTickGap={40} />
        <YAxis allowDecimals={false} {...AXIS} />
        <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "#1b2130" }} />
        <Bar dataKey="solved_count" name="solved" fill="#3fb27f" radius={[3, 3, 0, 0]} />
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
      <ResponsiveContainer width="100%" height={height}>
        {children}
      </ResponsiveContainer>
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
