"""A weekly leaderboard.

**Weekly, not all-time.** A lifetime total ranks people by when they started,
which nobody can act on: an account four months old cannot be caught this
month, so the board stops being a contest and becomes a wall. Resetting every
Monday means the standings are always about the week you are actually in — and
it matches what the product is about, which is not going stale rather than
accumulating a number.

**Ranked on volume, tied on consistency.** Problems solved leads because it is
what a week of practice produces. Ties break on active days, so somebody who
spread six problems across four days places above somebody who did six in one
sitting — the app's whole argument is that regular practice beats bursts.

Nothing here exposes an email address. A leaderboard is the one screen where
one account's data is shown to another, so the only fields that cross that line
are a display name and the figures being ranked.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.db.models import Submission, User
from app.services.report_service import week_start_for

ACCEPTED = "OK"

# Enough to see where you stand without turning the card into a directory.
TOP_N = 10


def display_name_for(user: User) -> str:
    """What another user is allowed to see.

    Never the email address. A missing display name falls back to the
    Codeforces handle, which is already public on Codeforces, and only then to
    something anonymous — the alternative is leaking an address to everyone on
    the board.
    """
    if user.display_name and user.display_name.strip():
        return user.display_name.strip()
    if user.codeforces_handle:
        return f"@{user.codeforces_handle}"
    return "Anonymous"


def rank(entries: list[dict]) -> list[dict]:
    """Order the board and number it, sharing a place on a genuine tie.

    Standard competition ranking: two people on 6 both place 2nd and the next
    is 4th. Numbering them 2nd and 3rd would invent a difference the data does
    not contain, which on a board of two or three people is most of the board.
    """
    ordered = sorted(
        entries,
        # Volume first, then consistency, then name so the order is stable
        # rather than dependent on however the rows came back.
        key=lambda e: (-e["solved"], -e["active_days"], e["name"].lower()),
    )

    place = 0
    previous: tuple[int, int] | None = None
    for index, entry in enumerate(ordered, start=1):
        current = (entry["solved"], entry["active_days"])
        if current != previous:
            place = index
            previous = current
        entry["place"] = place

    return ordered


async def weekly(db: AsyncSession, user_id: int, today: date | None = None) -> dict:
    """This week's standings, with the caller marked."""
    today = today or clock.today()
    start = week_start_for(today)

    rows = (
        await db.execute(
            select(
                User,
                func.count(func.distinct(Submission.external_problem_id)).label("solved"),
                func.count(func.distinct(clock.local_day(Submission.solved_at))).label("days"),
            )
            .join(
                Submission,
                (Submission.user_id == User.id)
                & (Submission.verdict == ACCEPTED)
                & (clock.local_day(Submission.solved_at) >= start),
            )
            # An outer join would list everybody with a zero, which reads as a
            # roll-call of people who did nothing. A week you sat out is not a
            # placing.
            .group_by(User.id)
        )
    ).all()

    entries = [
        {
            "name": display_name_for(user),
            "solved": solved,
            "active_days": days,
            "is_you": user.id == user_id,
        }
        for user, solved, days in rows
    ]

    ranked = rank(entries)
    you = next((e for e in ranked if e["is_you"]), None)

    return {
        "week_start": start,
        "entries": ranked[:TOP_N],
        # Sent separately so the caller can be told where they stand even when
        # they fall outside the visible top ten.
        "your_place": you["place"] if you else None,
        "total_ranked": len(ranked),
    }
