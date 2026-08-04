from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.codeforces_client import CodeforcesError, CodeforcesHandleError
from app.clients.leethub_client import (
    LeetHubError,
    LeetHubRateLimited,
    LeetHubRepoError,
)
from app.core.deps import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.schemas.dashboard import (
    DailyPlanOut,
    RatingDistributionOut,
    RecommendationsOut,
    RemindersOut,
    StatsOut,
    TagBreakdownOut,
    TimelineOut,
    WeakTopicsOut,
    WeeklyReportOut,
)
from app.clients.groq_client import GroqError, GroqNotConfigured
from app.services import (
    plan_service,
    reminder_service,
    report_service,
    recommendation_service,
    stats_service,
    topic_service,
)
from app.services.ingestion_service import ingest_codeforces_submissions
from app.services.leetcode_ingestion_service import ingest_leetcode_submissions

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

PLATFORMS = ("codeforces", "leetcode")
PlatformQuery = Query(default=None, description="Restrict to one platform; omit for all")


def _validated(platform: str | None) -> str | None:
    if platform is not None and platform not in PLATFORMS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"platform must be one of {', '.join(PLATFORMS)}",
        )
    return platform


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
    except CodeforcesHandleError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Codeforces rejected the handle "
            f"'{current_user.codeforces_handle}': {e}",
        )
    except CodeforcesError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))

    return {"inserted": inserted}


@router.post("/ingest/leetcode")
async def ingest_leetcode(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.leetcode_repo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Set your leetcode_repo first via PUT /users/me/leetcode-repo",
        )

    try:
        inserted = await ingest_leetcode_submissions(
            db, user_id=current_user.id, repo=current_user.leetcode_repo
        )
    except LeetHubRepoError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except LeetHubRateLimited as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e)
        )
    except LeetHubError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))

    return {"inserted": inserted}


@router.get("/stats", response_model=StatsOut)
async def read_stats(
    platform: str | None = PlatformQuery,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await stats_service.get_stats(db, current_user.id, platform=_validated(platform))


@router.get("/tags", response_model=TagBreakdownOut)
async def read_tags(
    limit: int | None = Query(default=None, ge=1, le=100),
    platform: str | None = PlatformQuery,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await stats_service.get_tag_breakdown(
        db, current_user.id, limit=limit, platform=_validated(platform)
    )


@router.get("/rating-distribution", response_model=RatingDistributionOut)
async def read_rating_distribution(
    platform: str | None = PlatformQuery,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await stats_service.get_rating_distribution(
        db, current_user.id, platform=_validated(platform)
    )


@router.get("/recommendations", response_model=RecommendationsOut)
async def read_recommendations(
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await recommendation_service.get_recommendations(
            db, current_user.id, limit=limit
        )
    except CodeforcesError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get("/daily-plan", response_model=DailyPlanOut)
async def read_daily_plan(
    regenerate: bool = Query(default=False, description="Discard today's stored plan"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await plan_service.get_daily_plan(
            db, current_user.id, regenerate=regenerate
        )
    except GroqNotConfigured as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        )
    except GroqError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get("/reminders", response_model=RemindersOut)
async def read_reminders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await reminder_service.list_reminders(db, current_user.id)


@router.post("/reminders/run", response_model=RemindersOut)
async def trigger_reminders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await reminder_service.run_reminders(db, current_user.id)


@router.get("/weekly-report", response_model=WeeklyReportOut)
async def read_weekly_report(
    week_start: date | None = Query(
        default=None, description="Monday of the week to report on; omit for this week"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await report_service.get_weekly_report(
        db, current_user.id, week_start=week_start
    )


@router.get("/weak-topics", response_model=WeakTopicsOut)
async def read_weak_topics(
    limit: int | None = Query(default=None, ge=1, le=100),
    platform: str | None = PlatformQuery,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await topic_service.get_weak_topics(
        db, current_user.id, limit=limit, platform=_validated(platform)
    )


@router.get("/timeline", response_model=TimelineOut)
async def read_timeline(
    days: int = Query(default=365, ge=1, le=1825),
    platform: str | None = PlatformQuery,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await stats_service.get_timeline(
        db, current_user.id, days=days, platform=_validated(platform)
    )
