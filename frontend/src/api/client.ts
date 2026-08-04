import type {
  RatingDistribution,
  Stats,
  TagBreakdown,
  Timeline,
  Token,
  User,
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

  ingest: (token: string) =>
    request<{ inserted: number }>("/dashboard/ingest/codeforces", token, {
      method: "POST",
    }),

  stats: (token: string) => request<Stats>("/dashboard/stats", token),

  tags: (token: string, limit = 12) =>
    request<TagBreakdown>(`/dashboard/tags?limit=${limit}`, token),

  ratings: (token: string) =>
    request<RatingDistribution>("/dashboard/rating-distribution", token),

  timeline: (token: string, days = 365) =>
    request<Timeline>(`/dashboard/timeline?days=${days}`, token),
};
