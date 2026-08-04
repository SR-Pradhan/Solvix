import { useCallback, useEffect, useState } from "react";

import { api } from "../api/client";
import type {
  RatingDistribution,
  Recommendations as RecommendationsData,
  Stats,
  TagBreakdown,
  Platform,
  Timeline,
  WeakTopics as WeakTopicsData,
} from "../api/types";
import { useAuth } from "../auth";
import { ActivityChart, RatingChart, TagChart } from "../components/Charts";
import { ConnectLeetCode } from "../components/ConnectLeetCode";
import { PlatformFilter } from "../components/PlatformFilter";
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
  const [platform, setPlatform] = useState<Platform | null>(null);

  const connected: Platform[] = [];
  if (user?.codeforces_handle) connected.push("codeforces");
  if (user?.leetcode_repo) connected.push("leetcode");

  const load = useCallback(async () => {
    if (!token) return;
    setError(null);
    try {
      const [stats, tags, ratings, timeline, weakTopics] = await Promise.all([
        api.stats(token, platform),
        api.tags(token, 12, platform),
        api.ratings(token, platform),
        api.timeline(token, 365, platform),
        api.weakTopics(token, 8, platform),
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
  }, [token, platform]);

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
            {[
              user.display_name ?? user.email,
              user.codeforces_handle && `@${user.codeforces_handle}`,
            ]
              .filter(Boolean)
              .join(", ")}
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

      <PlatformFilter
        available={connected}
        value={platform}
        onChange={setPlatform}
      />

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
          <StatCards stats={data.stats} topics={data.weakTopics} />
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
