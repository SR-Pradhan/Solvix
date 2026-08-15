from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import auth, dashboard, interviews, jobs, users
from app.core.config import settings
from app.core.version import APP_VERSION
from app.db.database import get_db

app = FastAPI(title="Solvix", version=APP_VERSION)

# The frontend runs on its own origin in development, so the browser blocks
# every request without this.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(dashboard.router)
app.include_router(interviews.router)
app.include_router(jobs.router)


@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    await db.execute(text("SELECT 1"))
    # The version travels with the health check so "which build is live?" is
    # answerable without opening a dashboard. The UI footer reads it from here.
    return {"status": "ok", "db": "connected", "version": APP_VERSION}
