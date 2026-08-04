"""Scores each tag by how weak the user is at it.

Weakness combines two signals the raw solve counts miss:

- **accuracy** — a tag you pass on the first try is not the same as one you
  brute-force through ten wrong answers, even at equal solve counts
- **recency** — a tag solved well six months ago has decayed; one solved
  yesterday has not

The result feeds the AI daily plan, stale-topic reminders, and the weekly
report, so the scoring lives here rather than in any one of them.
"""

from datetime import date, datetime, timezone

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Submission

ACCEPTED = "OK"

# Below this, accuracy is noise rather than signal — one wrong answer on a
# single attempt would read as a 0% tag.
MIN_ATTEMPTS = 3
# How long a tag takes to go fully stale.
STALE_HORIZON_DAYS = 60
# Accuracy matters more than recency: being unable to solve a topic is a
# bigger problem than not having touched it lately.
ACCURACY_WEIGHT, RECENCY_WEIGHT = 0.6, 0.4


def utc_today() -> date:
    return datetime.now(timezone.utc).date()


def score_topic(
    attempts: int, accepted: int, last_solved: date | None, today: date
) -> tuple[float, float, int | None]:
    """Return (weakness, accuracy, days_since_last_solve) for one tag."""
    accuracy = accepted / attempts if attempts else 0.0

    if last_solved is None:
        days_since = None
        staleness = 1.0
    else:
        days_since = max(0, (today - last_solved).days)
        staleness = min(days_since / STALE_HORIZON_DAYS, 1.0)

    weakness = ACCURACY_WEIGHT * (1 - accuracy) + RECENCY_WEIGHT * staleness
    return round(weakness, 4), round(accuracy, 4), days_since


async def get_weak_topics(
    db: AsyncSession, user_id: int, limit: int | None = None
) -> dict:
    # unnest expands one row per (submission, tag) so the aggregates below
    # count attempts per tag rather than per submission.
    tagged = (
        select(
            func.unnest(Submission.tags).label("tag"),
            Submission.external_problem_id.label("problem_id"),
            Submission.verdict.label("verdict"),
            Submission.solved_at.label("solved_at"),
        )
        .where(Submission.user_id == user_id)
        .subquery()
    )

    rows = (
        await db.execute(
            select(
                tagged.c.tag,
                func.count().label("attempts"),
                func.count().filter(tagged.c.verdict == ACCEPTED).label("accepted"),
                func.count(distinct(tagged.c.problem_id))
                .filter(tagged.c.verdict == ACCEPTED)
                .label("solved"),
                func.max(tagged.c.solved_at)
                .filter(tagged.c.verdict == ACCEPTED)
                .label("last_solved"),
            ).group_by(tagged.c.tag)
        )
    ).all()

    today = utc_today()
    topics = []
    skipped = 0

    for row in rows:
        if row.attempts < MIN_ATTEMPTS:
            skipped += 1
            continue
        last_solved = row.last_solved.date() if row.last_solved else None
        weakness, accuracy, days_since = score_topic(
            row.attempts, row.accepted, last_solved, today
        )
        topics.append(
            {
                "tag": row.tag,
                "attempts": row.attempts,
                "accepted": row.accepted,
                "solved": row.solved,
                "accuracy": accuracy,
                "last_solved_at": last_solved,
                "days_since_last_solve": days_since,
                "weakness": weakness,
            }
        )

    topics.sort(key=lambda t: (-t["weakness"], t["tag"]))

    return {
        "topics": topics[:limit] if limit else topics,
        "total_topics": len(topics),
        "skipped_low_volume": skipped,
        "min_attempts": MIN_ATTEMPTS,
    }
