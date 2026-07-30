from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.schemas.user import SetCodeforcesHandle, UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
async def read_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me/codeforces-handle", response_model=UserOut)
async def set_codeforces_handle(
    payload: SetCodeforcesHandle,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user.codeforces_handle = payload.codeforces_handle
    await db.commit()
    await db.refresh(current_user)
    return current_user
