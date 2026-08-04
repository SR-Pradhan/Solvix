import { useEffect, useState } from "react";

import { ApiError, api } from "../api/client";
import type { SolvedInTopic } from "../api/types";
import { useAuth } from "../auth";

function ago(days: number): string {
  if (days === 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 14) return `${days} days ago`;
  if (days < 60) return `${Math.round(days / 7)} weeks ago`;
  return `${Math.round(days / 30)} months ago`;
}

export function RevisionProblems({ tag }: { tag: string }) {
  const { token } = useAuth();
  const [data, setData] = useState<SolvedInTopic | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;

    setData(null);
    setError(null);
    api
      .solvedInTopic(token, tag, 8)
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof ApiError ? err.message : "Could not load problems");
      });

    return () => {
      cancelled = true;
    };
  }, [token, tag]);

  if (error) return <p className="error small topic-problems">{error}</p>;
  if (!data) return <p className="muted small topic-problems">Loading…</p>;

  if (!data.problems.length) {
    return (
      <p className="muted small topic-problems">
        No solved problems recorded for this topic yet.
      </p>
    );
  }

  return (
    <ul className="problem-list topic-problems">
      {data.problems.map((p) => (
        <li key={`${p.platform}:${p.id}`}>
          {p.url ? (
            <a href={p.url} target="_blank" rel="noreferrer">
              {p.name}
            </a>
          ) : (
            <span className="small muted">{p.name}</span>
          )}
          <span className="muted small">solved {ago(p.days_ago)}</span>
        </li>
      ))}
    </ul>
  );
}
