import asyncio

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients import leetcode_client, leethub_client
from app.core.config import settings
from app.db.models import Submission

PLATFORM = "leetcode"
BATCH_SIZE = 500
# Each new problem costs two GitHub calls, so a handful at a time keeps the
# import quick without hammering the API.
CONCURRENCY = 5


def not_yet_imported(folder_names: list[str], stored_ids: set[str]) -> list[str]:
    """Which repo folders are genuinely new, compared on the canonical slug.

    The two LeetCode import paths name the same problem differently: the repo
    calls it `0190-reverse-bits`, the profile's recent-solves list calls it
    `reverse-bits`. Comparing the raw strings meant a problem the profile had
    already imported looked new to the repo import, so it was stored a second
    time under the other name — inflating the solved count and giving one
    problem two revision schedules, which showed up as the same title twice in
    a day's reminders.

    `slug_from_folder` already existed to reconcile the two shapes; it was only
    ever applied in one direction. Both sides are normalised here.
    """
    known = {leetcode_client.slug_from_folder(stored) for stored in stored_ids}
    return [
        folder
        for folder in folder_names
        if leetcode_client.slug_from_folder(folder) not in known
    ]


async def ingest_leetcode_submissions(db: AsyncSession, user_id: int, repo: str) -> int:
    token = settings.github_token

    known = set(
        (
            await db.scalars(
                select(Submission.external_problem_id).where(
                    Submission.user_id == user_id, Submission.platform == PLATFORM
                )
            )
        ).all()
    )

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        slugs = await leethub_client.fetch_solved_slugs(client, repo, token)
        new_slugs = not_yet_imported(slugs, known)
        if not new_slugs:
            return 0

        # Only fetched when there is something new — it covers every problem,
        # so re-reading it for a no-op sync would be wasted.
        tag_map = await leethub_client.fetch_tag_map(client, repo, token)

        semaphore = asyncio.Semaphore(CONCURRENCY)

        async def load(slug: str) -> dict | None:
            async with semaphore:
                title, difficulty = await leethub_client.fetch_problem_details(
                    client, repo, slug, token
                )
                solved_at = await leethub_client.fetch_first_commit_date(
                    client, repo, slug, token
                )
            if solved_at is None:
                return None
            return {
                "user_id": user_id,
                "platform": PLATFORM,
                "external_problem_id": slug,
                "problem_name": title or slug,
                "tags": tag_map.get(slug, []),
                "difficulty_rating": None,
                "difficulty_label": difficulty,
                "verdict": "OK",  # LeetHub only pushes accepted solutions.
                "solved_at": solved_at,
            }

        rows = [r for r in await asyncio.gather(*(load(s) for s in new_slugs)) if r]

    if not rows:
        return 0

    inserted = 0
    for i in range(0, len(rows), BATCH_SIZE):
        stmt = insert(Submission).values(rows[i : i + BATCH_SIZE])
        stmt = stmt.on_conflict_do_nothing(
            index_elements=["user_id", "platform", "external_problem_id", "solved_at"]
        )
        result = await db.execute(stmt)
        inserted += result.rowcount

    await db.commit()
    return inserted
