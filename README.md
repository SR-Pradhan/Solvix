# Solvix

Competitive programming analytics. Import your Codeforces submissions and see
what you have actually been practising — solved counts, tag strengths,
difficulty spread, and activity over time.

![stack](https://img.shields.io/badge/FastAPI-backend-009485)
![stack](https://img.shields.io/badge/React%20%2B%20Vite-frontend-5b8def)
![stack](https://img.shields.io/badge/PostgreSQL-15-336791)

## What it does

- **Imports** your full Codeforces submission history, then syncs incrementally
- **Deduplicates** attempts into problems — ten wrong answers on one problem
  count as one solve, not eleven
- **Breaks down** solves by tag and difficulty rating
- **Tracks** daily activity, current streak, and longest streak
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
```

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
| POST   | `/dashboard/ingest/codeforces`    | Import or sync submissions       |
| GET    | `/dashboard/stats`                | Totals, streaks, acceptance rate |
| GET    | `/dashboard/tags`                 | Solves per tag                   |
| GET    | `/dashboard/rating-distribution`  | Solves per difficulty            |
| GET    | `/dashboard/timeline`             | Solves per day                   |
| GET    | `/dashboard/recommendations`      | Problems picked from weak tags   |

All `/users` and `/dashboard` routes need `Authorization: Bearer <token>`.

## Layout

```
backend/    FastAPI app, Alembic migrations, tests
frontend/   React client
```

## Tests

```bash
cd backend && ../.venv/bin/python -m pytest
```

## Roadmap

- [x] Problem recommendations from weak tags
- [ ] LeetCode ingestion via LeetHub-synced GitHub repo
- [ ] AtCoder ingestion
- [ ] Deployment
