from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import auth, dashboard, users
from app.db.database import get_db

app = FastAPI(title="Solvix")
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(dashboard.router)


@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    await db.execute(text("SELECT 1"))
    return {"status": "ok", "db": "connected"}
