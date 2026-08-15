import type {
  DailyPlan,
  Health,
  Interview,
  Interviews,
  LeetCodeProfile,
  RatingDistribution,
  Recommendations,
  Reminders,
  SolvedInTopic,
  Stats,
  TagBreakdown,
  Timeline,
  PendingEmailChange,
  Platform,
  ProfileChanges,
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

/** One retry, for the free instance's cold start.
 *
 * The API sleeps after 15 minutes idle and takes up to a minute to come back,
 * and the first request while it is waking fails at the network layer. Failing
 * the user's login for that reads as a broken site, so the request is tried
 * once more after a pause — long enough for the wake to finish, short enough
 * that a genuinely dead backend still reports quickly.
 */
async function fetchWithWakeRetry(
  url: string,
  init: RequestInit,
): Promise<Response> {
  try {
    return await fetch(url, init);
  } catch (first) {
    // Only idempotent-by-nature failures reach here: a request that never
    // left the browser cannot have been applied on the server.
    await new Promise((resolve) => setTimeout(resolve, 3000));
    try {
      return await fetch(url, init);
    } catch {
      throw first;
    }
  }
}

async function send(
  path: string,
  token: string | null,
  init: RequestInit,
): Promise<Response> {
  // A multipart upload has to keep the browser's own Content-Type, which
  // carries the boundary marker. Declaring JSON over it makes the body
  // unparseable at the far end.
  const headers: Record<string, string> = {
    ...(init.body instanceof FormData
      ? {}
      : { "Content-Type": "application/json" }),
    ...((init.headers as Record<string, string>) ?? {}),
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  let res: Response;
  try {
    res = await fetchWithWakeRetry(`${BASE}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(
      0,
      "The server is still waking up. Give it a few seconds and try again.",
    );
  }

  if (!res.ok) {
    throw new ApiError(res.status, await readDetail(res));
  }
  return res;
}

async function request<T>(
  path: string,
  token: string | null,
  init: RequestInit = {},
): Promise<T> {
  return (await (await send(path, token, init)).json()) as T;
}

/** For endpoints that answer 204, where parsing a body would throw. */
async function requestEmpty(
  path: string,
  token: string | null,
  init: RequestInit = {},
): Promise<void> {
  await send(path, token, init);
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
  /** Unauthenticated: also how the UI learns which build is live. */
  health: () => request<Health>("/health", null),

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

  updateProfile: (token: string, changes: ProfileChanges) =>
    request<User>("/users/me", token, {
      method: "PATCH",
      body: JSON.stringify(changes),
    }),

  pendingEmailChange: (token: string) =>
    request<PendingEmailChange | null>("/users/me/email/pending", token),

  requestEmailChange: (token: string, newEmail: string, password: string) =>
    request<PendingEmailChange>("/users/me/email/request", token, {
      method: "POST",
      body: JSON.stringify({ new_email: newEmail, password }),
    }),

  verifyEmailChange: (token: string, code: string) =>
    request<User>("/users/me/email/verify", token, {
      method: "POST",
      body: JSON.stringify({ code }),
    }),

  cancelEmailChange: (token: string) =>
    requestEmpty("/users/me/email/pending", token, { method: "DELETE" }),

  startInterview: (token: string) =>
    request<Interview>("/interviews", token, { method: "POST" }),

  listInterviews: (token: string) =>
    request<Interviews>("/interviews", token),

  replyToInterview: (token: string, id: number, answer: string) =>
    request<Interview>(`/interviews/${id}/reply`, token, {
      method: "POST",
      body: JSON.stringify({ answer }),
    }),

  finishInterview: (token: string, id: number) =>
    request<Interview>(`/interviews/${id}/finish`, token, { method: "POST" }),

  // Returns a replacement token: changing a password retires every token
  // issued before it, including the one making this call.
  changePassword: (token: string, current: string, next: string) =>
    request<Token>("/users/me/password", token, {
      method: "POST",
      body: JSON.stringify({
        current_password: current,
        new_password: next,
      }),
    }),

  uploadAvatar: (token: string, file: File) => {
    const body = new FormData();
    body.append("file", file);
    // No Content-Type header: the browser has to set it itself so it can add
    // the multipart boundary, and naming it here would produce a bodiless
    // request the server cannot parse.
    return request<User>("/users/me/avatar", token, { method: "POST", body });
  },

  deleteAvatar: (token: string) =>
    request<User>("/users/me/avatar", token, { method: "DELETE" }),

  /**
   * The avatar as an object URL.
   *
   * An `<img src>` cannot carry an Authorization header, so the bytes are
   * fetched here and wrapped in a blob URL. The caller must revoke it.
   */
  avatarUrl: async (token: string): Promise<string | null> => {
    const res = await fetch(`${BASE}/users/me/avatar`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) return null;
    return URL.createObjectURL(await res.blob());
  },

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
