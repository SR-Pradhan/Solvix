"""Mock interview sessions.

Separate from `dashboard.py` because everything there answers "what does my
practice look like", and this is a conversation with its own lifecycle.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.groq_client import GroqError, GroqNotConfigured
from app.core.deps import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.schemas.interview import InterviewOut, InterviewReply, InterviewsOut
from app.services import interview_service
from app.services.interview_service import InterviewError

router = APIRouter(prefix="/interviews", tags=["interviews"])


def _handle(exc: Exception) -> HTTPException:
    """Domain errors become status codes here, and only here."""
    if isinstance(exc, InterviewError):
        return HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    if isinstance(exc, GroqNotConfigured):
        return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc))
    return HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc))


@router.post("", response_model=InterviewOut, status_code=status.HTTP_201_CREATED)
async def start_interview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await interview_service.start(db, current_user.id)
    except (InterviewError, GroqError) as exc:
        raise _handle(exc) from exc


@router.get("", response_model=InterviewsOut)
async def list_interviews(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await interview_service.recent(db, current_user.id, min(max(limit, 1), 50))


@router.get("/{interview_id}", response_model=InterviewOut)
async def read_interview(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await interview_service.get(db, current_user.id, interview_id)
    except InterviewError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.post("/{interview_id}/reply", response_model=InterviewOut)
async def reply_to_interview(
    interview_id: int,
    payload: InterviewReply,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await interview_service.reply(
            db, current_user.id, interview_id, payload.answer
        )
    except (InterviewError, GroqError) as exc:
        raise _handle(exc) from exc


@router.post("/{interview_id}/finish", response_model=InterviewOut)
async def finish_interview(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await interview_service.finish(db, current_user.id, interview_id)
    except (InterviewError, GroqError) as exc:
        raise _handle(exc) from exc
