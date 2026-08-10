# Solvix

Competitive programming analytics. Import your Codeforces submissions and see
what you have actually been practising — solved counts, tag strengths,
difficulty spread, and activity over time.

**Live:** [solvix-roan.vercel.app](https://solvix-roan.vercel.app) ·
API [solvix-api.onrender.com/docs](https://solvix-api.onrender.com/docs)

> The API runs on a free instance that sleeps when idle, so the first request
> after a quiet spell takes about 50 seconds to wake it.

![stack](https://img.shields.io/badge/FastAPI-backend-009485)
![stack](https://img.shields.io/badge/React%20%2B%20Vite-frontend-5b8def)
![stack](https://img.shields.io/badge/PostgreSQL-15-336791)

## What it does

- **Imports** your full Codeforces submission history, then syncs incrementally
- **Imports** LeetCode solves from a LeetHub-synced GitHub repo
- **Deduplicates** attempts into problems — ten wrong answers on one problem
  count as one solve, not eleven
- **Breaks down** solves by tag and difficulty rating
- **Tracks** daily activity, current streak, and longest streak
- **Scores** each topic by accuracy and recency, so a tag you brute-forced
  through or last touched months ago ranks as weak
- **Recommends** unsolved problems from the tags you practise least, at a
  difficulty just above your current level

## Stack

| Layer    | Tech                                                     |
| -------- | -------------------------------------------------------- |
| Backend  | FastAPI, async SQLAlchemy, Alembic, JWT auth              |
| Database | PostgreSQL 15 (Docker)                                   |
| Frontend | React, TypeScript, Vite, Recharts                        |

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
| GET    | `/dashboard/recommendations`      | Problems picked from weak tags   |

All `/users` and `/dashboard` routes need `Authorization: Bearer <token>`.

Auth details worth knowing: login allows five failed attempts per caller in
five minutes before a fifteen-minute pause, and a password change bumps a
`token_version` on the user row, which retires every token issued before it —
a stateless JWT made revocable without a session store. `/health` reports the
running version, which the UI footer displays.

The table above is the core of the API, not all of it. The full, always-current
list is generated from the code and browsable at
[`/docs`](https://solvix-api.onrender.com/docs).

## Layout

```
backend/    FastAPI app, Alembic migrations, tests
frontend/   React client
```

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

