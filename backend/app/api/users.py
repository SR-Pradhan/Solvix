from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.schemas.user import (
    SetCodeforcesHandle,
    SetLeetcodeRepo,
    SetLeetcodeUsername,
    UserOut,
)

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


@router.put("/me/leetcode-repo", response_model=UserOut)
async def set_leetcode_repo(
    payload: SetLeetcodeRepo,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user.leetcode_repo = payload.leetcode_repo
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.put("/me/leetcode-username", response_model=UserOut)
async def set_leetcode_username(
    payload: SetLeetcodeUsername,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user.leetcode_username = payload.leetcode_username.strip()
    await db.commit()
    await db.refresh(current_user)
    return current_user
