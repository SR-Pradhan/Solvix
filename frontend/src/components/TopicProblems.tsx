import { useEffect, useState } from "react";

import { ApiError, api } from "../api/client";
import type { UnsolvedInTopic } from "../api/types";
import { useAuth } from "../auth";

const DIFFICULTY_COLOURS: Record<string, string> = {
  Easy: "var(--ok)",
  Medium: "var(--warn)",
  Hard: "var(--danger)",
};

export function TopicProblems({
  tag,
  platform,
}: {
  tag: string;
  platform: "codeforces" | "leetcode";
}) {
  const { token } = useAuth();
  const [data, setData] = useState<UnsolvedInTopic | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;

    setData(null);
    setError(null);
    api
      .unsolvedInTopic(token, tag, platform, 10)
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(
          err instanceof ApiError ? err.message : "Could not load problems",
        );
      });

    // The row can be collapsed before the request lands; without this the
    // response would set state on a component nobody is looking at.
    return () => {
      cancelled = true;
    };
  }, [token, tag, platform]);

  if (error) return <p className="error small topic-problems">{error}</p>;
  if (!data) return <p className="muted small topic-problems">Loading…</p>;

  if (!data.problems.length) {
    return (
      <p className="muted small topic-problems">
        Nothing left unsolved here on {platform === "leetcode" ? "LeetCode" : "Codeforces"}.
      </p>
    );
  }

  return (
    <ul className="problem-list topic-problems">
      {data.problems.map((p) => (
        <li key={p.id}>
          <a href={p.url} target="_blank" rel="noreferrer">
            {p.name}
          </a>
          <span
            className="rating-pill"
            style={{
              color: p.difficulty ? DIFFICULTY_COLOURS[p.difficulty] : undefined,
            }}
          >
            {p.difficulty ?? p.rating ?? "?"}
          </span>
        </li>
      ))}
    </ul>
  );
}
