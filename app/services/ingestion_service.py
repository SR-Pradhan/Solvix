from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.codeforces_client import fetch_user_submissions, to_submission_row
from app.db.models import Submission


async def ingest_codeforces_submissions(db: AsyncSession, user_id: int, handle: str) -> int:
    raw_submissions = await fetch_user_submissions(handle)

    rows = [
        {**to_submission_row(raw), "user_id": user_id, "platform": "codeforces"}
        for raw in raw_submissions
    ]
    if not rows:
        return 0

    batch_size = 500
    inserted = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        stmt = insert(Submission).values(batch)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=["user_id", "platform", "external_problem_id", "solved_at"]
        )
        result = await db.execute(stmt)
        inserted += result.rowcount

    await db.commit()
    return inserted
