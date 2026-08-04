import { useCallback, useEffect, useState } from "react";

import { api } from "../api/client";
import type {
  RatingDistribution,
  Recommendations as RecommendationsData,
  Stats,
  TagBreakdown,
  Timeline,
  WeakTopics as WeakTopicsData,
} from "../api/types";
import { useAuth } from "../auth";
import { ActivityChart, RatingChart, TagChart } from "../components/Charts";
import { ConnectLeetCode } from "../components/ConnectLeetCode";
import { Recommendations } from "../components/Recommendations";
import { StatCards } from "../components/StatCards";
import { WeakTopics } from "../components/WeakTopics";
import { HandleSetup } from "./HandleSetup";

interface Dashboard {
  stats: Stats;
  tags: TagBreakdown;
  ratings: RatingDistribution;
  timeline: Timeline;
  weakTopics: WeakTopicsData;
  recommendations: RecommendationsData | null;
}

export function DashboardPage() {
  const { token, user, logout, refreshUser } = useAuth();
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    setError(null);
    try {
      const [stats, tags, ratings, timeline, weakTopics] = await Promise.all([
        api.stats(token),
        api.tags(token, 12),
        api.ratings(token),
        api.timeline(token, 365),
        api.weakTopics(token, 8),
      ]);
      setData({
        stats,
        tags,
        ratings,
        timeline,
        weakTopics,
        recommendations: null,
      });

      // Recommendations pull the whole Codeforces problemset on a cold cache,
      // so they arrive after the charts rather than holding them up.
      try {
        const recommendations = await api.recommendations(token, 10);
        setData((prev) => (prev ? { ...prev, recommendations } : prev));
      } catch {
        /* the rest of the dashboard is still worth showing */
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard");
    }
  }, [token]);

  useEffect(() => {
    if (user?.codeforces_handle) void load();
  }, [user?.codeforces_handle, load]);

  async function sync(platform: "codeforces" | "leetcode" = "codeforces") {
    if (!token) return;
    setSyncing(true);
    setError(null);
    setNotice(null);
    try {
      const { inserted } =
        platform === "leetcode"
          ? await api.ingestLeetcode(token)
          : await api.ingest(token);
      setNotice(
        inserted === 0
          ? "Already up to date."
          : `Imported ${inserted.toLocaleString()} new submissions.`,
      );
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sync failed");
    } finally {
      setSyncing(false);
    }
  }

  if (!user) return null;

  if (!user.codeforces_handle) {
    return <HandleSetup onDone={refreshUser} />;
  }

  return (
    <div className="page">
      <header className="topbar">
        <div>
          <h1 className="brand">Solvix</h1>
          <span className="muted small">
            {user.display_name ?? user.email} · @{user.codeforces_handle}
          </span>
        </div>
        <div className="actions">
          <button onClick={() => sync("codeforces")} disabled={syncing}>
            {syncing ? "Syncing…" : "Sync Codeforces"}
          </button>
          {user.leetcode_repo && (
            <button
              className="ghost"
              onClick={() => sync("leetcode")}
              disabled={syncing}
            >
              Sync LeetCode
            </button>
          )}
          <button className="ghost" onClick={logout}>
            Log out
          </button>
        </div>
      </header>

      {notice && <p className="notice">{notice}</p>}
      {error && <p className="error">{error}</p>}

      {!data ? (
        <p className="muted">Loading…</p>
      ) : data.stats.total_submissions === 0 ? (
        <section className="card">
          <p>
            Nothing imported yet. Hit <strong>Sync Codeforces</strong> to pull
            your submissions.
          </p>
        </section>
      ) : (
        <>
          <StatCards stats={data.stats} />
          {!user.leetcode_repo && <ConnectLeetCode onDone={refreshUser} />}
          {data.recommendations && (
            <Recommendations data={data.recommendations} />
          )}
          <div className="grid-2">
            <WeakTopics data={data.weakTopics} />
            <TagChart data={data.tags} />
            <RatingChart data={data.ratings} />
          </div>
          <ActivityChart data={data.timeline} />
        </>
      )}
    </div>
  );
}
