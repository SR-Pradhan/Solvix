from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.codeforces_client import CodeforcesError
from app.core.deps import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.services.ingestion_service import ingest_codeforces_submissions

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.post("/ingest/codeforces")
async def ingest_codeforces(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.codeforces_handle:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Set your codeforces_handle first via PUT /users/me/codeforces-handle",
        )

    try:
        inserted = await ingest_codeforces_submissions(
            db, user_id=current_user.id, handle=current_user.codeforces_handle
        )
    except CodeforcesError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))

    return {"inserted": inserted}
