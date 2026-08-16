import { useCallback, useEffect, useState } from "react";

import { api } from "../api/client";
import type {
  DailyPlan as DailyPlanData,
  LeetCodeProfile as LeetCodeProfileData,
  RatingDistribution,
  Recommendations as RecommendationsData,
  Stats,
  TagBreakdown,
  Platform,
  Timeline,
  WeakTopics as WeakTopicsData,
  Reminders as RemindersData,
  WeeklyReport as WeeklyReportData,
} from "../api/types";
import { useAuth } from "../auth";
import { AccountMenu } from "../components/AccountMenu";
import { ActivityChart, RatingChart, TagChart } from "../components/Charts";
import { ConnectLeetCode } from "../components/ConnectLeetCode";
import { DailyPlan } from "../components/DailyPlan";
import { LeetCodeProfile } from "../components/LeetCodeProfile";
import { PlatformFilter } from "../components/PlatformFilter";
import { Recommendations } from "../components/Recommendations";
import { Reminders } from "../components/Reminders";
import { DashboardSkeleton } from "../components/Skeleton";
import { StatCards } from "../components/StatCards";
import { VersionFooter } from "../components/VersionFooter";
import { ThemeToggle } from "../components/ThemeToggle";
import { WeakTopics } from "../components/WeakTopics";
import { WeeklyReport } from "../components/WeeklyReport";
import { HandleSetup } from "./HandleSetup";
import { InterviewPage } from "./InterviewPage";
import { ProfilePage } from "./ProfilePage";

interface Dashboard {
  stats: Stats;
  tags: TagBreakdown;
  ratings: RatingDistribution;
  timeline: Timeline;
  weakTopics: WeakTopicsData;
  weekly: WeeklyReportData;
  reminders: RemindersData;
  recommendations: RecommendationsData | null;
}

export function DashboardPage() {
  const { token, user, logout, refreshUser } = useAuth();
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Which platform is syncing, not merely whether one is: a single flag made
  // each button report the other's work, so pressing "Sync LeetCode" showed
  // "Syncing…" on the Codeforces button.
  const [syncingPlatform, setSyncingPlatform] = useState<Platform | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [platform, setPlatform] = useState<Platform | null>(null);
  const [plan, setPlan] = useState<DailyPlanData | null>(null);
  const [lcProfile, setLcProfile] = useState<LeetCodeProfileData | null>(null);
  const [planBusy, setPlanBusy] = useState(false);
  // No router in the app yet, so the profile is a view swap rather than a
  // route. Worth revisiting if a third screen appears.
  const [showProfile, setShowProfile] = useState(false);
  const [showInterview, setShowInterview] = useState(false);
  // Nine cards on one screen is a wall, not a dashboard. The split is by
  // purpose rather than by density: Today is what to act on now, Progress is
  // what to review. A two-column layout was tried first and reverted — it
  // packed the same nine cards tighter, which is not the same as showing
  // fewer.
  const [view, setView] = useState<"today" | "progress">("today");
  // Only true once loading has taken long enough to be worth explaining. A
  // fast load should say nothing at all.
  const [slowLoad, setSlowLoad] = useState(false);

  // Whether the profile card is on screen, which decides two things at once:
  // that card respects the filter, and the difficulty fallback only stands in
  // when the authoritative breakdown is absent.
  const profileVisible = lcProfile !== null && platform !== "codeforces";

  const connected: Platform[] = [];
  if (user?.codeforces_handle) connected.push("codeforces");
  if (user?.leetcode_repo) connected.push("leetcode");

  const load = useCallback(async () => {
    if (!token) return;
    setError(null);
    try {
      const [stats, tags, ratings, timeline, weakTopics, weekly, reminders] =
        await Promise.all([
          api.stats(token, platform),
          api.tags(token, 12, platform),
          api.ratings(token, platform),
          api.timeline(token, 365, platform),
          api.weakTopics(token, 30, platform),
          api.weeklyReport(token, platform),
          api.reminders(token, platform),
        ]);
      setData({
        stats,
        tags,
        ratings,
        timeline,
        weakTopics,
        weekly,
        reminders,
        recommendations: null,
      });

      // The plan may call a language model, so it loads after the charts and
      // is allowed to fail without taking the dashboard down with it.
      api
        .dailyPlan(token)
        .then(setPlan)
        .catch(() => setPlan(null));

      // The card that offers "Refresh from LeetCode" only renders once a
      // profile exists, so an account that has never synced one had no way to
      // get the first — the real total simply never appeared. Fetching it
      // here closes that loop: one public GraphQL call, no button to find.
      api
        .leetcodeProfile(token)
        .then((profile) =>
          profile ?? (user?.leetcode_username ? api.syncLeetcodeProfile(token) : null),
        )
        .then(setLcProfile)
        .catch(() => setLcProfile(null));

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
    // The username rather than the whole user object: `refreshUser` hands back
    // a new object each time, which would reload the entire dashboard for a
    // changed avatar.
  }, [token, platform, user?.leetcode_username]);

  useEffect(() => {
    if (user?.codeforces_handle) void load();
  }, [user?.codeforces_handle, load]);

  // Four seconds is past "the network is fine" and well short of the ~50s a
  // cold start takes, so the explanation appears while it is still useful.
  useEffect(() => {
    if (data) {
      setSlowLoad(false);
      return;
    }
    const timer = setTimeout(() => setSlowLoad(true), 4000);
    return () => clearTimeout(timer);
  }, [data]);

  async function sync(platform: Platform = "codeforces") {
    if (!token) return;
    setSyncingPlatform(platform);
    setError(null);
    setNotice(null);
    const label = platform === "leetcode" ? "LeetCode" : "Codeforces";
    try {
      const { inserted } =
        platform === "leetcode"
          ? await api.ingestLeetcode(token)
          : await api.ingest(token);
      // Named, because two buttons produce this line and "Already up to date"
      // on its own does not say which one finished.
      setNotice(
        inserted === 0
          ? `${label} is already up to date.`
          : `Imported ${inserted.toLocaleString()} new ${label} submissions.`,
      );
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : `${label} sync failed`);
    } finally {
      setSyncingPlatform(null);
    }
  }

  async function regeneratePlan() {
    if (!token) return;
    setPlanBusy(true);
    try {
      setPlan(await api.dailyPlan(token, true));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not rebuild the plan");
    } finally {
      setPlanBusy(false);
    }
  }

  if (!user) return null;

  if (!user.codeforces_handle) {
    return <HandleSetup onDone={refreshUser} />;
  }

  if (showInterview) {
    return <InterviewPage onBack={() => setShowInterview(false)} />;
  }

  if (showProfile) {
    return <ProfilePage onBack={() => setShowProfile(false)} />;
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
          {/* One primary action, then the account. Sync used to live here as
              two buttons; the morning job imports on its own now, so keeping
              them in the header would claim the app still needs driving. */}
          <button className="ghost" onClick={() => setShowInterview(true)}>
            Mock interview
          </button>
          <ThemeToggle />
          <AccountMenu
            user={user}
            syncingPlatform={syncingPlatform}
            onSync={sync}
            onProfile={() => setShowProfile(true)}
            onLogout={logout}
          />
        </div>
      </header>

      {/* Both controls on one line: they are both "narrow what I am looking
          at", and stacking them makes two rows of near-identical chips that
          the reader has to tell apart. */}
      <div className="dash-controls">
        <div className="view-switch" role="tablist" aria-label="Dashboard view">
        <button
          type="button"
          role="tab"
          aria-selected={view === "today"}
          className={view === "today" ? "chip-btn on" : "chip-btn"}
          onClick={() => setView("today")}
        >
          Today
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={view === "progress"}
          className={view === "progress" ? "chip-btn on" : "chip-btn"}
          onClick={() => setView("progress")}
        >
          Progress
        </button>
        </div>

        <PlatformFilter
          available={connected}
          value={platform}
          onChange={setPlatform}
        />
      </div>

      {notice && <p className="notice">{notice}</p>}
      {error && <p className="error">{error}</p>}

      {!data ? (
        <DashboardSkeleton waking={slowLoad} />
      ) : data.stats.total_submissions === 0 ? (
        <section className="card empty-state">
          <h2>Nothing imported yet</h2>
          <p className="muted">
            Solvix imports your history every morning on its own. To see it
            now, use <strong>Sync Codeforces</strong> in the account menu.
          </p>
          {user.leetcode_repo ? null : (
            <p className="muted small">
              Connecting LeetCode as well gives you topic coverage the
              Codeforces tags cannot show.
            </p>
          )}
        </section>
      ) : (
        <>
          {view === "today" ? (
            <>
              {/* Only what today asks of you. Everything here is an action. */}
              {plan && (
                <DailyPlan
                  data={plan}
                  onRegenerate={regeneratePlan}
                  busy={planBusy}
                />
              )}
              <Reminders data={data.reminders} />
              {/* Recommendations come from the Codeforces problemset only, so
                  they are not an answer to "show me LeetCode". */}
              {data.recommendations && platform !== "leetcode" && (
                <Recommendations data={data.recommendations} />
              )}
              {!user.leetcode_repo && <ConnectLeetCode onDone={refreshUser} />}
            </>
          ) : (
            <>
              {/* Everything that answers "how am I doing", which is a
                  different question and a different mood. */}
              <StatCards
                stats={data.stats}
                topics={data.weakTopics}
                profile={lcProfile}
                platform={platform}
              />
              <WeeklyReport data={data.weekly} />
              {/* The filter has to reach every card or it means nothing: a
                  LeetCode profile on a screen narrowed to Codeforces makes the
                  reader doubt whether anything else respected the filter
                  either. */}
              {profileVisible && lcProfile && (
                <LeetCodeProfile data={lcProfile} onSynced={setLcProfile} />
              )}
              <div className="grid-2">
                <WeakTopics data={data.weakTopics} platform={platform} />
                <TagChart data={data.tags} />
              </div>
              {/* The standalone difficulty card is a stand-in for the rating
                  histogram when there are no numeric ratings to plot. Once a
                  LeetCode profile exists it is a second Easy/Medium/Hard
                  breakdown beside the profile card's — same labels, different
                  totals, because one counts imported problems and the other
                  counts every problem solved. Two numbers claiming the same
                  thing teaches the reader to trust neither, so the
                  authoritative one wins and this only appears without it. */}
              {(data.ratings.buckets.length > 0 || !profileVisible) && (
                <RatingChart data={data.ratings} />
              )}
              <ActivityChart data={data.timeline} />
            </>
          )}
        </>
      )}

      <VersionFooter />
    </div>
  );
}
