"""Scores each tag by how weak the user is at it.

Weakness combines two signals the raw solve counts miss:

- **accuracy** — a tag you pass first try is not the same as one you
  brute-forced through ten wrong answers, even at equal solve counts
- **recency** — a tag solved well six months ago has decayed; one solved
  yesterday has not

Accuracy is only meaningful on platforms that record failed attempts. LeetHub
commits solutions only once they pass, so LeetCode data is 100% accurate by
construction; scoring it on accuracy would be scoring an artefact. Those tags
fall back to recency alone and say so.

The result feeds the AI daily plan, stale-topic reminders, and the weekly
report, so the scoring lives here rather than in any one of them.
"""

from datetime import date, datetime, timezone

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Submission

ACCEPTED = "OK"

# Platforms whose imports include failed attempts, so accuracy means something.
PLATFORMS_WITH_FAILURES = ("codeforces",)

# Below this, accuracy is noise rather than signal — one wrong answer on a
# single attempt would read as a 0% tag.
MIN_ATTEMPTS = 3
# How long a tag takes to fully decay in the weakness score. Kept generous so
# the ranking keeps its resolution: if everything older than a week counted as
# maximally stale, recency would stop separating topics at all.
STALE_HORIZON_DAYS = 90
# When a topic becomes due for revision. Short on purpose, so the "going stale"
# list is a this-week to-do rather than a backlog.
REVISION_DUE_DAYS = 7
# Accuracy matters more than recency: being unable to solve a topic is a
# bigger problem than not having touched it lately.
ACCURACY_WEIGHT, RECENCY_WEIGHT = 0.6, 0.4

# Plain-language bands, so the UI never has to show a raw score.
STATUS_BANDS = ((0.60, "Needs work"), (0.35, "Rusty"), (0.0, "Solid"))
# Bands in days, for topics with no pass rate to score against. Anchored to the
# same 14-day mark the revision reminders use, so a topic flagged as due is
# never simultaneously labelled "Solid".
STALE_STATUS_BANDS = ((42, "Needs work"), (14, "Rusty"), (0, "Solid"))


def utc_today() -> date:
    return datetime.now(timezone.utc).date()


def status_for(
    weakness: float, accuracy: float | None = None, days_since: int | None = None
) -> str:
    """Plain-language label for a topic.

    With no pass rate the weakness score is recency rescaled, and the numeric
    bands were calibrated for a combined score — a topic untouched for a month
    lands at 0.31 and reads "Solid" while the reminder card calls it due. For
    those topics the label comes from the age directly.
    """
    if accuracy is None:
        age = days_since if days_since is not None else 10_000
        for threshold, label in STALE_STATUS_BANDS:
            if age >= threshold:
                return label
        return "Solid"

    for threshold, label in STATUS_BANDS:
        if weakness >= threshold:
            return label
    return "Solid"


def _is_stale(days_since: int | None) -> bool:
    """Never solved, or not revised within the revision window."""
    return days_since is None or days_since >= REVISION_DUE_DAYS


def score_topic(
    rated_attempts: int,
    rated_accepted: int,
    last_solved: date | None,
    today: date,
) -> tuple[float, float | None, int | None]:
    """Return (weakness, accuracy, days_since_last_solve) for one tag.

    `accuracy` is None when the tag has too few attempts on a platform that
    records failures; weakness then rests on recency alone.
    """
    if last_solved is None:
        days_since = None
        staleness = 1.0
    else:
        # A future date means clock skew, not a bonus.
        days_since = max(0, (today - last_solved).days)
        staleness = min(days_since / STALE_HORIZON_DAYS, 1.0)

    if rated_attempts < MIN_ATTEMPTS:
        return round(staleness, 4), None, days_since

    accuracy = rated_accepted / rated_attempts
    weakness = ACCURACY_WEIGHT * (1 - accuracy) + RECENCY_WEIGHT * staleness
    return round(weakness, 4), round(accuracy, 4), days_since


async def get_weak_topics(
    db: AsyncSession,
    user_id: int,
    limit: int | None = None,
    platform: str | None = None,
) -> dict:
    # unnest expands one row per (submission, tag) so the aggregates below
    # count attempts per tag rather than per submission.
    query = select(
        func.unnest(Submission.tags).label("tag"),
        Submission.external_problem_id.label("problem_id"),
        Submission.verdict.label("verdict"),
        Submission.platform.label("platform"),
        Submission.solved_at.label("solved_at"),
    ).where(Submission.user_id == user_id)
    if platform:
        query = query.where(Submission.platform == platform)
    tagged = query.subquery()

    rated = tagged.c.platform.in_(PLATFORMS_WITH_FAILURES)

    rows = (
        await db.execute(
            select(
                tagged.c.tag,
                func.count().label("attempts"),
                func.count().filter(tagged.c.verdict == ACCEPTED).label("accepted"),
                func.count(distinct(tagged.c.problem_id))
                .filter(tagged.c.verdict == ACCEPTED)
                .label("solved"),
                func.count().filter(rated).label("rated_attempts"),
                func.count()
                .filter(rated, tagged.c.verdict == ACCEPTED)
                .label("rated_accepted"),
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
            row.rated_attempts, row.rated_accepted, last_solved, today
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
                "status": status_for(weakness, accuracy, days_since),
            }
        )

    topics.sort(key=lambda t: (-t["weakness"], t["tag"]))
    scored_on_accuracy = sum(1 for t in topics if t["accuracy"] is not None)

    # Counted over every topic, not just the ones returned, so the figure does
    # not change when the caller asks for a shorter list.
    stale = [t for t in topics if _is_stale(t["days_since_last_solve"])]

    return {
        "topics": topics[:limit] if limit else topics,
        "total_topics": len(topics),
        "skipped_low_volume": skipped,
        "min_attempts": MIN_ATTEMPTS,
        "scored_on_accuracy": scored_on_accuracy,
        "stale_count": len(stale),
        "stale_horizon_days": REVISION_DUE_DAYS,
        # Every due topic, so the UI can reveal the full list on demand.
        "stale_topics": [t["tag"] for t in stale],
    }


async def weak_topics_with_platform(
    db: AsyncSession, user_id: int, limit: int = 8
) -> list[dict]:
    """Weak topics, each labelled with the platform it was scored on.

    `get_weak_topics` deliberately does not return a platform: scoring is done
    per platform and the caller passes which one. But anything that acts on a
    topic — recommending a problem, choosing an interview question — needs to
    know where to look, and a tag alone cannot say. So this scores each
    platform in turn and keeps the label, the same way the reminder job does.

    Sorted across platforms by weakness, because the caller wants "what is
    weakest", not "what is weakest on Codeforces and then what is weakest on
    LeetCode".
    """
    combined: list[dict] = []
    for platform in PLATFORMS_WITH_FAILURES + ("leetcode",):
        scored = await get_weak_topics(db, user_id, platform=platform)
        for topic in scored["topics"]:
            combined.append({**topic, "platform": platform})

    combined.sort(key=lambda t: t["weakness"], reverse=True)
    return combined[:limit]
