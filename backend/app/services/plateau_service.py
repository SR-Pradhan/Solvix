"""Whether recent practice is still stretching, or has settled.

Weak-topic scoring asks *which* topics are weak. Pattern clustering asks which
techniques break in company. This asks a question neither can: **is the
difficulty going anywhere?**

Somebody can practise every day, keep a perfect streak, and improve at nothing
— by solving problems they could already solve. That is invisible to every
other measure in the app, because it looks exactly like diligence. It is the
one failure mode a practice tracker can accidentally encourage: rewarding
volume teaches you to pick easy problems.

**Working level.** The hardest tier where enough problems have been solved to
call it demonstrated rather than lucky. Everything is judged relative to it,
because "solves a lot of Easy problems" means something completely different
for someone who has never cleared a Medium.

**Three outcomes, and the distinction matters.**

- *Stretching* — a real share of recent work is above the working level.
- *Coasting* — most recent work is **below** a level already demonstrated.
- *Plateaued* — recent work sits **at** the working level, but almost nothing
  above it. Comfortable, and going nowhere.

Coasting and plateauing need different advice, which is why they are not one
label: one says "stop revisiting solved ground", the other says "you are ready
for the next tier and have not tried it".

**Both platforms, on their own scales.** LeetCode has three named tiers;
Codeforces has a numeric rating, bucketed so that "the next tier up" means a
comparable step on either. Difficulty is never compared across platforms — a
LeetCode Medium and a 1600 are not the same claim, and pretending otherwise
would be the sort of false equivalence the rest of the app avoids.
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.db.models import Submission

ACCEPTED = "OK"

LEETCODE_TIERS = ("Easy", "Medium", "Hard")

# Codeforces rates 800–3500. Bucketed rather than compared directly so that
# "one tier up" is a step somebody can actually feel, instead of the ten points
# between two problems that are the same difficulty in practice.
CODEFORCES_BUCKET = 200

# Solves needed at a tier before it counts as your level rather than a couple
# of lucky ones. Below this, one hard problem you happened to get would rewrite
# the whole assessment.
MIN_AT_LEVEL = 8

# The window recent practice is read from. Three weeks: long enough that a
# quiet week does not read as a plateau, short enough to still be about now.
WINDOW_DAYS = 21

# Fewer solves than this in the window and there is nothing to judge. Saying
# "you have plateaued" to somebody who solved two problems is not an
# observation, it is an insult.
MIN_RECENT = 6

# Share of recent work above the working level that counts as still climbing.
STRETCH_MIN = 0.10
# Share below it that makes the problem "revisiting solved ground" rather than
# "not reaching high enough".
COAST_MAX = 0.50

STRETCHING, PLATEAUED, COASTING, UNKNOWN = (
    "Stretching",
    "Plateaued",
    "Coasting",
    "Not enough recent practice",
)


def tier_of(platform: str, label: str | None, rating: int | None) -> int | None:
    """Where one problem sits on its own platform's ladder.

    None when the platform did not say — an unrated Codeforces problem, or a
    LeetCode row imported before difficulty was recorded. Those are left out
    rather than guessed at, the same way an unknown is treated everywhere else.
    """
    if platform == "leetcode":
        if label in LEETCODE_TIERS:
            return LEETCODE_TIERS.index(label)
        return None
    if rating is None:
        return None
    return rating // CODEFORCES_BUCKET


def label_for(platform: str, tier: int) -> str:
    if platform == "leetcode":
        index = max(0, min(tier, len(LEETCODE_TIERS) - 1))
        return LEETCODE_TIERS[index]
    return f"{tier * CODEFORCES_BUCKET}+"


def top_tier(platform: str) -> int:
    """The last rung, above which there is nothing left to stretch towards."""
    if platform == "leetcode":
        return len(LEETCODE_TIERS) - 1
    # 3500 is the highest rating Codeforces gives out.
    return 3500 // CODEFORCES_BUCKET


def working_level(counts: dict[int, int]) -> int | None:
    """The hardest tier with enough solves behind it to be believed."""
    qualifying = [tier for tier, count in counts.items() if count >= MIN_AT_LEVEL]
    return max(qualifying) if qualifying else None


def assess(recent: list[int], level: int, platform: str) -> dict:
    """Judge a window of recent solves against a demonstrated level."""
    total = len(recent)
    above = sum(1 for tier in recent if tier > level)
    at = sum(1 for tier in recent if tier == level)
    below = total - above - at

    if total < MIN_RECENT:
        status = UNKNOWN
    elif above / total >= STRETCH_MIN:
        status = STRETCHING
    elif below / total > COAST_MAX:
        status = COASTING
    else:
        status = PLATEAUED

    # Somebody at the top of the ladder cannot stretch further, and telling
    # them they have plateaued would be punishing them for finishing it.
    at_ceiling = level >= top_tier(platform)
    if at_ceiling and status in (PLATEAUED, COASTING) and total >= MIN_RECENT:
        status = STRETCHING if above == 0 and below == 0 else status

    return {
        "platform": platform,
        "status": status,
        "working_level": label_for(platform, level),
        "next_level": None if at_ceiling else label_for(platform, level + 1),
        "recent_solved": total,
        "above": above,
        "at": at,
        "below": below,
        "window_days": WINDOW_DAYS,
    }


async def _tiers(
    db: AsyncSession, user_id: int, platform: str, since: date | None = None
) -> list[tuple[int | None, int]]:
    """(tier, count) for a platform, optionally only since a local day."""
    query = select(
        Submission.difficulty_label,
        Submission.difficulty_rating,
        func.count(func.distinct(Submission.external_problem_id)),
    ).where(
        Submission.user_id == user_id,
        Submission.platform == platform,
        Submission.verdict == ACCEPTED,
    )
    if since is not None:
        query = query.where(Submission.solved_at >= clock.utc_start_of(since))

    rows = (
        await db.execute(
            query.group_by(Submission.difficulty_label, Submission.difficulty_rating)
        )
    ).all()

    return [
        (tier_of(platform, label, rating), count)
        for label, rating, count in rows
        if tier_of(platform, label, rating) is not None
    ]


async def for_platform(db: AsyncSession, user_id: int, platform: str) -> dict | None:
    """One platform's verdict, or None when it has nothing to say."""
    all_time = await _tiers(db, user_id, platform)
    if not all_time:
        return None

    counts: dict[int, int] = {}
    for tier, count in all_time:
        counts[tier] = counts.get(tier, 0) + count

    level = working_level(counts)
    if level is None:
        # Practising, but not yet enough at any one tier to say what your level
        # is. Guessing would produce advice built on three problems.
        return None

    today = clock.today()
    recent_rows = await _tiers(db, user_id, platform, today - timedelta(days=WINDOW_DAYS - 1))
    # Expanded back into one entry per solve so the shares are over problems
    # rather than over distinct difficulties.
    recent = [tier for tier, count in recent_rows for _ in range(count)]

    return assess(recent, level, platform)


async def get_plateau(db: AsyncSession, user_id: int) -> dict:
    """Both platforms, each judged on its own ladder."""
    platforms = []
    for platform in ("codeforces", "leetcode"):
        found = await for_platform(db, user_id, platform)
        if found is not None:
            platforms.append(found)

    return {"platforms": platforms, "window_days": WINDOW_DAYS}
