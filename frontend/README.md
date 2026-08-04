# Solvix — Frontend

React + TypeScript + Vite client for the Solvix dashboard.

## Run

The backend must be running on `http://localhost:8000` first (see `../backend`).

```bash
npm install
npm run dev
```

Opens on http://localhost:5173, which is the origin the backend allows via
`cors_origins` in `backend/app/core/config.py`.

To point at a different API, set `VITE_API_BASE`:

```bash
VITE_API_BASE=https://api.example.com npm run dev
```

## Structure

- `src/api/` — typed client; `types.ts` mirrors the backend's Pydantic schemas
- `src/auth.tsx` — JWT context, persisted to localStorage
- `src/pages/` — login, Codeforces handle setup, dashboard
- `src/components/` — stat cards and the three Recharts charts

## Scripts

```bash
npm run dev      # dev server with HMR
npm run build    # typecheck + production build to dist/
npm run preview  # serve the built output
```
