from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.codeforces_client import (
    fetch_submissions_since,
    fetch_user_submissions,
    to_submission_row,
)
from app.db.models import Submission, SyncState

PLATFORM = "codeforces"
BATCH_SIZE = 500


def choose_fetch_start(
    full_import_done: bool, latest_solved_at: datetime | None
) -> int | None:
    """Where the next fetch should begin. None means "fetch everything".

    Resuming from the newest stored submission is only sound once a full import
    has actually completed. An interrupted first import leaves a handful of
    recent rows behind, and resuming from those would silently declare the
    entire older history already imported — the app looks synced while showing
    almost nothing.
    """
    if not full_import_done or latest_solved_at is None:
        return None
    # solved_at is stored naive-UTC, so attach UTC before converting to the
    # epoch seconds Codeforces compares against.
    return int(latest_solved_at.replace(tzinfo=timezone.utc).timestamp())


async def _sync_state(db: AsyncSession, user_id: int) -> SyncState:
    state = await db.scalar(
        select(SyncState).where(
            SyncState.user_id == user_id, SyncState.platform == PLATFORM
        )
    )
    if state is None:
        state = SyncState(user_id=user_id, platform=PLATFORM)
        db.add(state)
    return state


async def ingest_codeforces_submissions(db: AsyncSession, user_id: int, handle: str) -> int:
    state = await _sync_state(db, user_id)
    latest = await db.scalar(
        select(func.max(Submission.solved_at)).where(
            Submission.user_id == user_id, Submission.platform == PLATFORM
        )
    )

    since = choose_fetch_start(state.full_import_completed_at is not None, latest)
    if since is None:
        raw_submissions = await fetch_user_submissions(handle)
    else:
        raw_submissions = await fetch_submissions_since(handle, since)

    rows = [
        {**to_submission_row(raw), "user_id": user_id, "platform": PLATFORM}
        for raw in raw_submissions
    ]

    inserted = 0
    for i in range(0, len(rows), BATCH_SIZE):
        stmt = insert(Submission).values(rows[i : i + BATCH_SIZE])
        stmt = stmt.on_conflict_do_nothing(
            index_elements=["user_id", "platform", "external_problem_id", "solved_at"]
        )
        result = await db.execute(stmt)
        inserted += result.rowcount

    # Marked only here, after the fetch returned and the rows are about to be
    # committed in the same transaction. A fetch that raised never reaches this
    # line, so the next run starts over rather than resuming from a partial
    # import.
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if since is None:
        state.full_import_completed_at = now
    state.last_synced_at = now

    await db.commit()
    return inserted
