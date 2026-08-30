# Solvix

An AI-powered DSA practice tracker for placement preparation. It reads your
Codeforces and LeetCode history automatically, works out which topics have
decayed, and turns that into a daily plan and spaced revision reminders.

The constraint that shapes everything: **no manual logging.** Every figure is
derived from data the platforms already hold, and several otherwise-obvious
features are deliberately absent for that reason.

**Live:** [solvix-roan.vercel.app](https://solvix-roan.vercel.app) .
API [solvix-api.onrender.com/docs](https://solvix-api.onrender.com/docs)

> The API runs on a free instance that sleeps when idle, so the first request
> after a quiet spell takes about 50 seconds to wake it.

![stack](https://img.shields.io/badge/FastAPI-backend-009485)
![stack](https://img.shields.io/badge/React%20%2B%20Vite-frontend-5b8def)
![stack](https://img.shields.io/badge/PostgreSQL-Neon-336791)
![tests](https://img.shields.io/badge/tests-357-3ecf8e)

## What it does

- **Imports** your full Codeforces history, then syncs incrementally; LeetCode
  comes from a LeetHub-synced GitHub repo plus the public profile for the true
  solved total the repo cannot know
- **Deduplicates** attempts into problems — ten wrong answers on one problem
  count as one solve, not eleven
- **Scores** each topic by accuracy and recency, so a tag you brute-forced
  through or last touched months ago ranks as weak. The two platforms are
  scored separately, because only one of them records failures
- **Plans** your day with an agent, not a prompt: it calls tools to read your
  weak topics, what is due, what you have never solved, and shows what it
  checked before deciding. Cached once per day
- **Reminds** you to revisit solved problems on a widening ladder — 3, 7, 14,
  30, 60 days — adjusted by how the revisit went where the platform records
  enough to tell
- **Emails** that list each morning, with links, so it can be acted on without
  opening the app
- **Clusters** techniques into pairs and reports only the ones you handle worse
  *together* than either technique alone — 69% on bitmasks and 79% on
  implementation, but 34% where both are needed. Ranking pairs by raw accuracy
  would just relist your weakest single tag, so a pair has to beat both its
  parts to appear
- **Recommends** unsolved problems from the tags you practise least, at a
  difficulty just above your current level
- **Interviews** you about a problem you have never solved, from a topic you
  are weak on — probing the approach and the complexity, then writing an honest
  assessment. Kept apart from the topic scores, because a pass rate and an
  interviewer's impression are different kinds of claim
- **Reports** each finished week, frozen as it was rather than recomputed by
  today's rules, and ranks everyone practising that week

## Stack

| Layer     | Tech                                                    |
| --------- | ------------------------------------------------------- |
| Backend   | FastAPI, async SQLAlchemy, Alembic, JWT auth            |
| Database  | PostgreSQL (Docker locally, Neon in production)         |
| Frontend  | React, TypeScript, Vite, Recharts                       |
| LLM       | Groq (`llama-3.3-70b-versatile`), JSON mode             |
| Scheduled | GitHub Actions — the API sleeps when idle, so the clock lives outside it |

## Getting started

**Requirements:** Docker, Python 3.13, Node 20+

```bash
git clone https://github.com/SR-Pradhan/Solvix.git
cd Solvix
docker compose up -d
```

Create `backend/.env`:

```env
DATABASE_URL=postgresql+asyncpg://solvix:solvix@localhost:5432/solvix
JWT_SECRET_KEY=change-me

# Optional. Needed for LeetCode imports: raises GitHub's API limit from
# 60 to 5000 requests per hour. Create one at github.com/settings/tokens.
GITHUB_TOKEN=

# Optional. Enables the AI daily plan. Free key from console.groq.com/keys.
GROQ_API_KEY=

# Optional. Without these, verification emails are written to the server log
# instead of being sent, which is enough to use the app in development.
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
MAIL_FROM=Solvix <no-reply@solvix.local>

# Optional. Shared secret for POST /jobs/daily-reminders, which a scheduler
# calls once a day. Unset means that endpoint refuses every request.
CRON_KEY=
APP_URL=http://localhost:5173

# The timezone every calendar day is measured in — streaks, "this week", which
# revisions fall due. Not a display setting: it decides which day a submission
# belongs to, so changing it moves history.
TIMEZONE=Asia/Kolkata

# How many proxies sit in front of the API. Render adds one; put a CDN in front
# as well and this becomes 2. It decides which X-Forwarded-For entry the rate
# limiter believes, so too high trusts an address the caller wrote.
TRUSTED_PROXY_HOPS=1
```

### Scheduled reminders

`POST /jobs/daily-reminders` generates the day's reminders for every account
and emails whoever has something due. It authenticates with a shared secret in
the `X-Cron-Key` header rather than a user token, because no user is present:

```bash
curl -X POST https://solvix-api.onrender.com/jobs/daily-reminders \
  -H "X-Cron-Key: $CRON_KEY"
```

The schedule itself lives outside the app — the API sleeps when idle, so an
in-process timer would only fire while someone happened to be using it.

Render's free instances block outbound SMTP (ports 25, 465 and 587), so mail
cannot leave the deployed API at all. `?deliver=false` therefore returns the
composed messages instead of sending them, and the scheduler delivers:

```bash
curl -X POST "https://solvix-api.onrender.com/jobs/daily-reminders?deliver=false" \
  -H "X-Cron-Key: $CRON_KEY"
```

Composition stays in the app either way — the wording is the part worth
testing, and it should not drift into a workflow tool.

**Backend** — http://localhost:8000 (docs at `/docs`):

```bash
cd backend
python -m venv ../.venv && ../.venv/bin/pip install -r requirements.txt
../.venv/bin/alembic upgrade head
../.venv/bin/uvicorn app.main:app --reload
```

**Frontend** — http://localhost:5173:

```bash
cd frontend
npm install
npm run dev
```

Register, enter your Codeforces handle, and the first import starts
automatically.

## API

| Method | Endpoint                          | Purpose                          |
| ------ | --------------------------------- | -------------------------------- |
| POST   | `/auth/register`                  | Create an account                |
| POST   | `/auth/login`                     | Get a JWT                        |
| GET    | `/users/me`                       | Current user                     |
| PUT    | `/users/me/codeforces-handle`     | Set the handle to sync           |
| PUT    | `/users/me/leetcode-repo`         | Set the LeetHub repo to sync     |
| POST   | `/dashboard/ingest/codeforces`    | Import or sync Codeforces        |
| POST   | `/dashboard/ingest/leetcode`      | Import or sync LeetCode          |
| GET    | `/dashboard/stats`                | Totals, streaks, acceptance rate |
| GET    | `/dashboard/tags`                 | Solves per tag                   |
| GET    | `/dashboard/rating-distribution`  | Solves per difficulty            |
| GET    | `/dashboard/timeline`             | Solves per day                   |
| GET    | `/dashboard/weak-topics`          | Tags scored by accuracy + recency|
| GET    | `/dashboard/patterns`             | Tag pairs worse than both their parts |
| GET    | `/dashboard/recommendations`      | Problems picked from weak tags   |
| GET    | `/dashboard/daily-plan`           | Today's plan, with the agent's reasoning |
| GET    | `/dashboard/leaderboard`          | This week's standings            |
| POST   | `/interviews`                     | Start a mock interview           |
| POST   | `/interviews/{id}/reply`          | Answer, and get the next question |
| POST   | `/jobs/daily-reminders`           | Scheduled: import, decide, email |

All `/users` and `/dashboard` routes need `Authorization: Bearer <token>`.

Auth details worth knowing: login allows five failed attempts per caller in
five minutes before a fifteen-minute pause, and a password change bumps a
`token_version` on the user row, which retires every token issued before it —
a stateless JWT made revocable without a session store. The same bump is
exposed as "sign out everywhere else". Deleting an account removes every row
belonging to it, and a test asserts that list covers every table carrying a
`user_id`. `/health` reports the running version, which the UI footer
displays.

The table above is the core of the API, not all of it. The full, always-current
list is generated from the code and browsable at
[`/docs`](https://solvix-api.onrender.com/docs).

## Layout

```
backend/    FastAPI app, Alembic migrations, tests
  app/api/        HTTP only — no business rules, no third-party calls
  app/services/   the actual thinking, including both agents
  app/clients/    Codeforces, GitHub, LeetCode, Groq, SMTP
  app/db/         models and the session factory
frontend/   React client
.github/    the daily reminder schedule
```

`api/` never calls a client directly and `services/` never raises an
`HTTPException`, which is why the same service answers a web request and a
scheduled job with nothing adapted between them.

Scheduled work is kept outside the API: the free instance sleeps when idle, so
an in-process timer would only fire while somebody happened to be using the
app. The scheduler decides *when*; Solvix decides *what*, so replacing it
changes no behaviour. It runs as
[`.github/workflows/daily-reminders.yml`](.github/workflows/daily-reminders.yml).

## Deployment

| Piece    | Host                                                          |
| -------- | ------------------------------------------------------------- |
| Database | Neon (managed Postgres)                                       |
| API      | Render, from [`render.yaml`](render.yaml) — migrations run on every boot |
| Frontend | Vercel, root directory `frontend`                             |

Two settings the app needs in production, both environment variables so nothing
is hardcoded to one machine:

- `DATABASE_URL` — must use the `postgresql+asyncpg://` scheme and `?ssl=require`.
  asyncpg does not understand the `sslmode=require` that hosted providers hand out.
- `CORS_ORIGINS` — the deployed frontend's address. Accepts a comma-separated
  list or a JSON array.

The frontend reads `VITE_API_BASE` at build time, so changing it needs a rebuild,
not just a restart.

## Tests

```bash
cd backend && ../.venv/bin/python -m pytest
```

306 tests, under a second, with no database and no network — the logic worth
testing is written as pure functions over values, and third-party calls are
stubbed at the HTTP layer. They aim at boundaries rather than coverage: exactly
at the staleness threshold, when a platform records no failures, when the model
returns nonsense, when a problem index is `E2` rather than `E`, when a date is
in the future, when a total is zero.

That shape is what made a deliberate bug sweep productive late on: four defects
fell out of feeding edge cases to those functions, and three were a hazard
already handled elsewhere in the codebase and forgotten in one place.

