"""Syncs a LeetCode profile from the public API.

LeetHub only records what you solved after installing it, so a long-standing
account is under-counted. LeetCode's public profile knows the real totals and
per-tag counts without any credentials — it just cannot say *which* problems or
*when*, beyond the twenty most recent.

So the two sources answer different halves:

- profile counts  → true volume and difficulty split
- recent solves   → exact timestamps, ahead of the next LeetHub push
- LeetHub repo    → per-problem history for everything it captured
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients import leetcode_client
from app.db.models import LeetCodeProfile, Submission

PLATFORM = "leetcode"
RECENT_LIMIT = 20


def coverage(profile_total: int, tracked: int) -> dict:
    """How much of the real history Solvix can actually see."""
    missing = max(0, profile_total - tracked)
    percent = round(tracked / profile_total * 100) if profile_total else 0
    return {"tracked": tracked, "missing": missing, "percent": percent}


async def _existing_slugs(db: AsyncSession, user_id: int) -> set[str]:
    rows = (
        await db.scalars(
            select(Submission.external_problem_id).where(
                Submission.user_id == user_id, Submission.platform == PLATFORM
            )
        )
    ).all()
    # Stored ids are LeetHub folder names ("0001-two-sum") for repo imports and
    # bare slugs for profile imports; compare on the slug so the two never
    # duplicate each other.
    return {leetcode_client.slug_from_folder(r) for r in rows}


async def _import_recent(db: AsyncSession, user_id: int, username: str) -> int:
    recent = await leetcode_client.fetch_recent_ac(username, RECENT_LIMIT)
    if not recent:
        return 0

    known = await _existing_slugs(db, user_id)
    inserted = 0

    for entry in recent:
        slug = entry["titleSlug"]
        if slug in known:
            continue

        details = await leetcode_client.fetch_question(slug)
        if details is None:
            continue

        solved_at = datetime.fromtimestamp(
            int(entry["timestamp"]), tz=timezone.utc
        ).replace(tzinfo=None)

        stmt = insert(Submission).values(
            user_id=user_id,
            platform=PLATFORM,
            external_problem_id=slug,
            problem_name=details["title"],
            tags=details["tags"],
            difficulty_rating=None,
            difficulty_label=details["difficulty"],
            verdict="OK",
            solved_at=solved_at,
        )
        result = await db.execute(
            stmt.on_conflict_do_nothing(
                index_elements=[
                    "user_id",
                    "platform",
                    "external_problem_id",
                    "solved_at",
                ]
            )
        )
        inserted += result.rowcount
        known.add(slug)

    return inserted


async def sync_profile(db: AsyncSession, user_id: int, username: str) -> dict:
    profile = await leetcode_client.fetch_profile(username)
    imported = await _import_recent(db, user_id, username)

    stmt = insert(LeetCodeProfile).values(
        user_id=user_id, username=username, payload=profile
    )
    await db.execute(
        stmt.on_conflict_do_update(
            index_elements=["user_id"],
            set_={"username": username, "payload": profile, "synced_at": datetime.utcnow()},
        )
    )
    await db.commit()

    tracked = len(await _existing_slugs(db, user_id))
    return {
        "username": username,
        **profile,
        "coverage": coverage(profile["total_solved"], tracked),
        "imported": imported,
    }


async def get_profile(db: AsyncSession, user_id: int) -> dict | None:
    stored = await db.scalar(
        select(LeetCodeProfile).where(LeetCodeProfile.user_id == user_id)
    )
    if stored is None:
        return None

    tracked = len(await _existing_slugs(db, user_id))
    return {
        "username": stored.username,
        **stored.payload,
        "coverage": coverage(stored.payload.get("total_solved", 0), tracked),
        "imported": 0,
    }
