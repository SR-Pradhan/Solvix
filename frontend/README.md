# Solvix — Frontend

Not scaffolded yet. This will hold the React + Vite client that consumes the
backend's dashboard endpoints:

- `GET /dashboard/stats`
- `GET /dashboard/tags`
- `GET /dashboard/rating-distribution`
- `GET /dashboard/timeline`

The backend allows this origin via `cors_origins` in `backend/app/core/config.py`,
which defaults to `http://localhost:5173` (Vite's dev port).
