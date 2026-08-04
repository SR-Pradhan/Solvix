from datetime import timezone

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.codeforces_client import (
    fetch_submissions_since,
    fetch_user_submissions,
    to_submission_row,
)
from app.db.models import Submission

PLATFORM = "codeforces"
BATCH_SIZE = 500


async def ingest_codeforces_submissions(db: AsyncSession, user_id: int, handle: str) -> int:
    latest = await db.scalar(
        select(func.max(Submission.solved_at)).where(
            Submission.user_id == user_id, Submission.platform == PLATFORM
        )
    )

    if latest is None:
        raw_submissions = await fetch_user_submissions(handle)
    else:
        # solved_at is stored naive-UTC, so attach UTC before converting to the
        # epoch seconds Codeforces compares against.
        since = int(latest.replace(tzinfo=timezone.utc).timestamp())
        raw_submissions = await fetch_submissions_since(handle, since)

    rows = [
        {**to_submission_row(raw), "user_id": user_id, "platform": PLATFORM}
        for raw in raw_submissions
    ]
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
