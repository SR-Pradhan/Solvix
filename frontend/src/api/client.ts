import type {
  DailyPlan,
  LeetCodeProfile,
  RatingDistribution,
  Recommendations,
  Reminders,
  SolvedInTopic,
  Stats,
  TagBreakdown,
  Timeline,
  Platform,
  Token,
  UnsolvedInTopic,
  User,
  WeakTopics,
  WeeklyReport,
} from "./types";

const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  path: string,
  token: string | null,
  init: RequestInit = {},
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((init.headers as Record<string, string>) ?? {}),
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, "Cannot reach the API. Is the backend running?");
  }

  if (!res.ok) {
    throw new ApiError(res.status, await readDetail(res));
  }
  return (await res.json()) as T;
}

// FastAPI puts a string in `detail` for raised HTTPExceptions but a list of
// field errors for 422s, so both shapes need flattening into one message.
async function readDetail(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) {
      return body.detail
        .map((e: { loc?: string[]; msg: string }) =>
          e.loc ? `${e.loc.slice(1).join(".")}: ${e.msg}` : e.msg,
        )
        .join(", ");
    }
  } catch {
    /* fall through to the status text */
  }
  return res.statusText || `Request failed (${res.status})`;
}

function qs(
  params: Record<string, string | number | boolean | null | undefined>,
): string {
  const parts = Object.entries(params)
    .filter(([, v]) => v !== null && v !== undefined)
    .map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`);
  return parts.length ? `?${parts.join("&")}` : "";
}

export const api = {
  register: (email: string, password: string, displayName?: string) =>
    request<User>("/auth/register", null, {
      method: "POST",
      body: JSON.stringify({
        email,
        password,
        display_name: displayName || null,
      }),
    }),

  login: (email: string, password: string) =>
    request<Token>("/auth/login", null, {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  me: (token: string) => request<User>("/users/me", token),

  setHandle: (token: string, handle: string) =>
    request<User>("/users/me/codeforces-handle", token, {
      method: "PUT",
      body: JSON.stringify({ codeforces_handle: handle }),
    }),

  setLeetcodeRepo: (token: string, repo: string) =>
    request<User>("/users/me/leetcode-repo", token, {
      method: "PUT",
      body: JSON.stringify({ leetcode_repo: repo }),
    }),

  ingestLeetcode: (token: string) =>
    request<{ inserted: number }>("/dashboard/ingest/leetcode", token, {
      method: "POST",
    }),

  ingest: (token: string) =>
    request<{ inserted: number }>("/dashboard/ingest/codeforces", token, {
      method: "POST",
    }),

  stats: (token: string, platform?: Platform | null) =>
    request<Stats>(`/dashboard/stats${qs({ platform })}`, token),

  tags: (token: string, limit = 12, platform?: Platform | null) =>
    request<TagBreakdown>(`/dashboard/tags${qs({ limit, platform })}`, token),

  ratings: (token: string, platform?: Platform | null) =>
    request<RatingDistribution>(
      `/dashboard/rating-distribution${qs({ platform })}`,
      token,
    ),

  timeline: (token: string, days = 365, platform?: Platform | null) =>
    request<Timeline>(`/dashboard/timeline${qs({ days, platform })}`, token),

  solvedInTopic: (token: string, tag: string, limit = 8) =>
    request<SolvedInTopic>(
      `/dashboard/topics/${encodeURIComponent(tag)}/solved${qs({ limit })}`,
      token,
    ),

  unsolvedInTopic: (
    token: string,
    tag: string,
    platform: Platform,
    limit = 10,
  ) =>
    request<UnsolvedInTopic>(
      `/dashboard/topics/${encodeURIComponent(tag)}/unsolved${qs({ platform, limit })}`,
      token,
    ),

  setLeetcodeUsername: (token: string, username: string) =>
    request<User>("/users/me/leetcode-username", token, {
      method: "PUT",
      body: JSON.stringify({ leetcode_username: username }),
    }),

  leetcodeProfile: (token: string) =>
    request<LeetCodeProfile | null>("/dashboard/leetcode-profile", token),

  syncLeetcodeProfile: (token: string) =>
    request<LeetCodeProfile>("/dashboard/sync/leetcode-profile", token, {
      method: "POST",
    }),

  reminders: (token: string, platform?: Platform | null) =>
    request<Reminders>(`/dashboard/reminders${qs({ platform })}`, token),

  weeklyReport: (token: string, platform?: Platform | null) =>
    request<WeeklyReport>(`/dashboard/weekly-report${qs({ platform })}`, token),

  dailyPlan: (token: string, regenerate = false) =>
    request<DailyPlan>(`/dashboard/daily-plan${qs({ regenerate })}`, token),

  weakTopics: (token: string, limit = 8, platform?: Platform | null) =>
    request<WeakTopics>(`/dashboard/weak-topics${qs({ limit, platform })}`, token),

  recommendations: (token: string, limit = 10) =>
    request<Recommendations>(`/dashboard/recommendations?limit=${limit}`, token),
};
