"""Weekly practice snapshots.

Finished weeks are stored rather than recomputed. The scoring rules in
`topic_service` will change as the product evolves, and a report of what
happened in March should keep saying what it said in March rather than being
silently rewritten by today's formula.
"""

from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.db.models import Submission, WeeklyReport
from app.services import topic_service

ACCEPTED = "OK"
HIGHLIGHT_COUNT = 3
# A topic needs some volume before calling it a strength means anything.
MIN_SOLVED_FOR_STRENGTH = 3


def week_start_for(day: date) -> date:
    """The Monday of the week containing `day`."""
    return day - timedelta(days=day.weekday())


def pick_highlights(topics: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split scored topics into the weakest few and the strongest few.

    `topics` arrives weakest-first. Strengths are taken from the other end, but
    only from topics with enough solves to be meaningful — otherwise a tag
    touched once and passed becomes a "strength".
    """
    weakest = [
        {"tag": t["tag"], "accuracy": t["accuracy"], "solved": t["solved"]}
        for t in topics[:HIGHLIGHT_COUNT]
    ]

    eligible = [t for t in topics if t["solved"] >= MIN_SOLVED_FOR_STRENGTH]
    strongest = [
        {"tag": t["tag"], "accuracy": t["accuracy"], "solved": t["solved"]}
        for t in reversed(eligible[-HIGHLIGHT_COUNT:])
    ]

    # A tag can be both ends of a short list; the weakest reading wins.
    weak_tags = {t["tag"] for t in weakest}
    strongest = [t for t in strongest if t["tag"] not in weak_tags]

    return weakest, strongest


async def _week_activity(
    db: AsyncSession, user_id: int, start: date, end: date, platform: str | None = None
) -> dict:
    """Counts for problems first solved inside [start, end]."""
    window_start = clock.utc_start_of(start)
    window_end = clock.utc_start_of(end + timedelta(days=1))

    # First accepted solve per problem, so re-solving an old problem does not
    # count as new progress this week.
    first_solves = (
        select(
            Submission.external_problem_id,
            Submission.platform,
            func.min(Submission.solved_at).label("first_solved_at"),
        )
        .where(
            Submission.user_id == user_id,
            Submission.verdict == ACCEPTED,
            *((Submission.platform == platform,) if platform else ()),
        )
        .group_by(Submission.external_problem_id, Submission.platform)
        .subquery()
    )

    rows = (
        await db.execute(
            select(first_solves.c.platform, func.count())
            .where(
                first_solves.c.first_solved_at >= window_start,
                first_solves.c.first_solved_at < window_end,
            )
            .group_by(first_solves.c.platform)
        )
    ).all()

    by_platform = {platform: count for platform, count in rows}

    active_days = (
        await db.execute(
            select(func.count(func.distinct(clock.local_day(Submission.solved_at)))).where(
                Submission.user_id == user_id,
                Submission.verdict == ACCEPTED,
                Submission.solved_at >= window_start,
                Submission.solved_at < window_end,
                *((Submission.platform == platform,) if platform else ()),
            )
        )
    ).scalar_one()

    return {
        "problems_solved": sum(by_platform.values()),
        "by_platform": by_platform,
        "active_days": active_days,
    }


async def _build_report(
    db: AsyncSession, user_id: int, start: date, platform: str | None = None
) -> dict:
    end = start + timedelta(days=6)
    activity = await _week_activity(db, user_id, start, end, platform)
    topics = (
        await topic_service.get_weak_topics(db, user_id, platform=platform)
    )["topics"]
    weakest, strongest = pick_highlights(topics)

    return {
        "week_start": start.isoformat(),
        "week_end": end.isoformat(),
        **activity,
        "weakest": weakest,
        "strongest": strongest,
    }


async def get_weekly_report(
    db: AsyncSession,
    user_id: int,
    week_start: date | None = None,
    platform: str | None = None,
) -> dict:
    today = clock.today()
    current_week = week_start_for(today)
    start = week_start or current_week
    finished = start < current_week

    # Only the unfiltered view is frozen. A per-platform slice is a lens on the
    # same week, not a different week, so storing one under the same key would
    # let whichever filter loaded first define the archived snapshot.
    if finished and platform is None:
        stored = await db.scalar(
            select(WeeklyReport).where(
                WeeklyReport.user_id == user_id, WeeklyReport.week_start == start
            )
        )
        if stored:
            return {"in_progress": False, **stored.payload}

    report = await _build_report(db, user_id, start, platform)

    # Only finished weeks are frozen. The current week is still accumulating,
    # so storing it would pin a half-finished snapshot for good.
    if finished and platform is None:
        stmt = insert(WeeklyReport).values(
            user_id=user_id, week_start=start, payload=report
        )
        await db.execute(
            stmt.on_conflict_do_nothing(index_elements=["user_id", "week_start"])
        )
        await db.commit()

    return {"in_progress": not finished, **report}
