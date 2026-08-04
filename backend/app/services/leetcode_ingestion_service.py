import asyncio

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients import leethub_client
from app.core.config import settings
from app.db.models import Submission

PLATFORM = "leetcode"
BATCH_SIZE = 500
# Each new problem costs two GitHub calls, so a handful at a time keeps the
# import quick without hammering the API.
CONCURRENCY = 5


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
        new_slugs = [s for s in slugs if s not in known]
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
