"""Spaced-repetition revision reminders.

Two kinds, from the same data the rest of Solvix already ingests:

- **problem** — you solved something a few days ago, and the spacing effect says
  now is when revisiting it pays. Time-sensitive, so these win the cap.
- **topic** — a tag that is both weak and stale. Not urgent on any given day,
  so these fill whatever slots are left.

Generation is deliberately separate from delivery. Today the dashboard reads
these rows; an email sender later is another reader, not a rewrite.
"""

from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Reminder, Submission
from app.services import topic_service

ACCEPTED = "OK"

# Revisit a solved problem after this long — the first spacing interval.
REVISIT_AFTER_DAYS = 3
# A topic must be untouched this long before it is worth nagging about.
STALE_THRESHOLD_DAYS = 14
# And weak enough to be worth the slot.
WEAK_THRESHOLD = 0.35
# Cap per run, so a long-inactive account is not flooded at once.
MAX_PER_RUN = 5


def describe_problem(name: str, days: int) -> str:
    if days == 1:
        return "solved yesterday"
    return f"solved {days} days ago"


def describe_topic(days_since: int | None, accuracy: float | None) -> str:
    if days_since is None:
        staleness = "never solved"
    elif days_since >= 365:
        staleness = "not practised in over a year"
    elif days_since >= 60:
        staleness = f"not practised in {round(days_since / 30)} months"
    else:
        staleness = f"not practised in {round(days_since / 7)} weeks"

    if accuracy is not None and accuracy < 0.5:
        return f"{staleness}, and only {round(accuracy * 100)}% of attempts pass"
    return staleness


def select_reminders(
    problems: list[dict], topics: list[dict], cap: int = MAX_PER_RUN
) -> list[dict]:
    """Merge both kinds into one capped list.

    Problem reminders come first: their window is a specific few days, while a
    stale topic is equally stale tomorrow.
    """
    return (problems + topics)[:cap]


def topic_is_due(topic: dict) -> bool:
    """Weak *and* stale — either alone is not a reminder.

    When a platform records no failed attempts there is no pass rate, so the
    weakness score is recency restated. Applying the weakness bar on top of the
    staleness bar would then just be the staleness test twice, at a stricter
    cutoff than the configured one — a LeetCode topic untouched for three weeks
    would score 0.23 and never fire. For those topics staleness alone decides.
    """
    days = topic["days_since_last_solve"]
    stale = days is None or days >= STALE_THRESHOLD_DAYS
    if not stale:
        return False
    if topic["accuracy"] is None:
        return True
    return topic["weakness"] >= WEAK_THRESHOLD


async def _problems_to_revisit(
    db: AsyncSession, user_id: int, today: date
) -> list[dict]:
    """Problems whose first solve was exactly REVISIT_AFTER_DAYS ago."""
    target = today - timedelta(days=REVISIT_AFTER_DAYS)
    window_start = datetime.combine(target, datetime.min.time())
    window_end = window_start + timedelta(days=1)

    first_solves = (
        select(
            Submission.external_problem_id,
            Submission.platform,
            func.min(Submission.problem_name).label("problem_name"),
            func.min(Submission.solved_at).label("first_solved_at"),
        )
        .where(Submission.user_id == user_id, Submission.verdict == ACCEPTED)
        .group_by(Submission.external_problem_id, Submission.platform)
        .subquery()
    )

    rows = (
        await db.execute(
            select(
                first_solves.c.external_problem_id,
                first_solves.c.platform,
                first_solves.c.problem_name,
            )
            .where(
                first_solves.c.first_solved_at >= window_start,
                first_solves.c.first_solved_at < window_end,
            )
            .order_by(first_solves.c.external_problem_id)
        )
    ).all()

    return [
        {
            "kind": "problem",
            "subject": f"{platform}:{pid}",
            "title": name or pid,
            "reason": describe_problem(name or pid, REVISIT_AFTER_DAYS),
        }
        for pid, platform, name in rows
    ]


async def run_reminders(db: AsyncSession, user_id: int) -> dict:
    """Generate today's reminders and persist them."""
    today = date.today()

    problems = await _problems_to_revisit(db, user_id, today)

    scored = (await topic_service.get_weak_topics(db, user_id))["topics"]
    topics = [
        {
            "kind": "topic",
            "subject": t["tag"],
            "title": t["tag"],
            "reason": describe_topic(t["days_since_last_solve"], t["accuracy"]),
        }
        for t in scored
        if topic_is_due(t)
    ]

    selected = select_reminders(problems, topics)

    for item in selected:
        stmt = insert(Reminder).values(
            user_id=user_id,
            run_date=today,
            kind=item["kind"],
            subject=item["subject"],
            title=item["title"],
            reason=item["reason"],
        )
        # Re-running on the same day refreshes nothing and duplicates nothing.
        await db.execute(
            stmt.on_conflict_do_nothing(
                index_elements=["user_id", "run_date", "kind", "subject"]
            )
        )
    await db.commit()

    return {
        "run_date": today,
        "generated": len(selected),
        "reminders": selected,
    }


async def list_reminders(db: AsyncSession, user_id: int) -> dict:
    """Today's stored reminders, generating them on first read of the day."""
    today = date.today()

    rows = (
        await db.execute(
            select(Reminder)
            .where(Reminder.user_id == user_id, Reminder.run_date == today)
            .order_by(Reminder.id)
        )
    ).scalars().all()

    if not rows:
        return await run_reminders(db, user_id)

    return {
        "run_date": today,
        "generated": len(rows),
        "reminders": [
            {
                "kind": r.kind,
                "subject": r.subject,
                "title": r.title,
                "reason": r.reason,
            }
            for r in rows
        ],
    }
