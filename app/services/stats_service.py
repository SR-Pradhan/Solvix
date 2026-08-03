from datetime import date, datetime, timedelta, timezone

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Submission

ACCEPTED = "OK"


def utc_today() -> date:
    return datetime.now(timezone.utc).date()


def compute_streaks(active_days: list[date], today: date) -> tuple[int, int]:
    """Return (current_streak, longest_streak) in days.

    A day counts as active if the user solved at least one problem on it. The
    current streak stays alive if the last active day is today or yesterday, so
    a user mid-day does not lose their streak before the day is over.
    """
    if not active_days:
        return 0, 0

    days = sorted(set(active_days))

    longest = run = 1
    for prev, cur in zip(days, days[1:]):
        run = run + 1 if cur - prev == timedelta(days=1) else 1
        longest = max(longest, run)

    current = 0
    if today - days[-1] <= timedelta(days=1):
        current = 1
        for i in range(len(days) - 1, 0, -1):
            if days[i] - days[i - 1] != timedelta(days=1):
                break
            current += 1

    return current, longest


def _solved_problems(user_id: int):
    """One row per distinct problem solved, taken from its first accepted submission.

    Codeforces reports every attempt, so a problem solved after ten wrong
    answers appears eleven times. Collapsing on external_problem_id keeps the
    stats about problems rather than about keystrokes.
    """
    return (
        select(
            Submission.external_problem_id,
            Submission.problem_name,
            Submission.tags,
            Submission.difficulty_rating,
            Submission.solved_at,
        )
        .where(Submission.user_id == user_id, Submission.verdict == ACCEPTED)
        .distinct(Submission.external_problem_id)
        .order_by(Submission.external_problem_id, Submission.solved_at)
        .subquery()
    )


async def get_stats(db: AsyncSession, user_id: int) -> dict:
    solved = _solved_problems(user_id)

    solved_row = (
        await db.execute(
            select(
                func.count().label("problems_solved"),
                func.avg(solved.c.difficulty_rating).label("avg_difficulty"),
                func.max(solved.c.difficulty_rating).label("max_difficulty"),
            ).select_from(solved)
        )
    ).one()

    totals_row = (
        await db.execute(
            select(
                func.count().label("total_submissions"),
                func.count()
                .filter(Submission.verdict == ACCEPTED)
                .label("accepted_submissions"),
            ).where(Submission.user_id == user_id)
        )
    ).one()

    active_days = (
        (
            await db.execute(
                select(func.date(Submission.solved_at))
                .where(Submission.user_id == user_id, Submission.verdict == ACCEPTED)
                .distinct()
            )
        )
        .scalars()
        .all()
    )
    current_streak, longest_streak = compute_streaks(list(active_days), utc_today())

    total = totals_row.total_submissions
    accepted = totals_row.accepted_submissions

    return {
        "problems_solved": solved_row.problems_solved,
        "total_submissions": total,
        "accepted_submissions": accepted,
        "acceptance_rate": round(accepted / total, 4) if total else 0.0,
        "avg_difficulty": round(float(solved_row.avg_difficulty), 1)
        if solved_row.avg_difficulty is not None
        else None,
        "max_difficulty": solved_row.max_difficulty,
        "current_streak_days": current_streak,
        "longest_streak_days": longest_streak,
    }


async def get_tag_breakdown(db: AsyncSession, user_id: int, limit: int | None = None) -> dict:
    solved = _solved_problems(user_id)
    unnested = select(func.unnest(solved.c.tags).label("tag")).select_from(solved).subquery()

    count_col = func.count().label("solved_count")
    query = (
        select(unnested.c.tag, count_col)
        .group_by(unnested.c.tag)
        .order_by(desc(count_col), unnested.c.tag)
    )

    rows = (await db.execute(query)).all()
    total_tags = len(rows)
    if limit is not None:
        rows = rows[:limit]

    return {
        "total_tags": total_tags,
        "tags": [{"tag": row.tag, "solved_count": row.solved_count} for row in rows],
    }


async def get_rating_distribution(db: AsyncSession, user_id: int) -> dict:
    solved = _solved_problems(user_id)

    rows = (
        await db.execute(
            select(solved.c.difficulty_rating, func.count().label("solved_count"))
            .select_from(solved)
            .where(solved.c.difficulty_rating.is_not(None))
            .group_by(solved.c.difficulty_rating)
            .order_by(solved.c.difficulty_rating)
        )
    ).all()

    unrated = (
        await db.execute(
            select(func.count())
            .select_from(solved)
            .where(solved.c.difficulty_rating.is_(None))
        )
    ).scalar_one()

    return {
        "buckets": [
            {"rating": row.difficulty_rating, "solved_count": row.solved_count} for row in rows
        ],
        "unrated_count": unrated,
    }


async def get_timeline(db: AsyncSession, user_id: int, days: int) -> dict:
    """Distinct problems solved per day over the trailing `days` window.

    A problem re-solved on a later day counts again for that day: this feeds an
    activity heatmap, not the unique-solved total.
    """
    since = datetime.combine(utc_today() - timedelta(days=days - 1), datetime.min.time())
    day_col = func.date(Submission.solved_at).label("day")

    rows = (
        await db.execute(
            select(day_col, func.count(func.distinct(Submission.external_problem_id)))
            .where(
                Submission.user_id == user_id,
                Submission.verdict == ACCEPTED,
                Submission.solved_at >= since,
            )
            .group_by(day_col)
            .order_by(day_col)
        )
    ).all()

    return {
        "days": days,
        "points": [{"day": row[0], "solved_count": row[1]} for row in rows],
    }
