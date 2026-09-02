import asyncio
from datetime import datetime, timedelta

import httpx
from sqlalchemy import func, select
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


def rows_for_resolves(
    events: list[tuple[str, datetime]], known: dict[str, dict]
) -> list[dict]:
    """Submission rows for solves of problems already on record.

    `known` maps a canonical slug to a stored row; the new row copies its
    name, tags and difficulty rather than re-fetching them, and keeps the
    stored id so both solves of one problem share a single identity. Folders
    that are not known are left to the new-problem path.
    """
    rows = []
    for folder, solved_at in events:
        existing = known.get(leetcode_client.slug_from_folder(folder))
        if existing is None:
            continue
        rows.append({**existing, "solved_at": solved_at})
    return rows


async def ingest_leetcode_submissions(
    db: AsyncSession, user_id: int, repo: str, full: bool = False
) -> int:
    """Import solves from the repo: new problems, and repeats of known ones.

    `full` rescans the whole commit history for repeats rather than only what
    is newer than the latest stored solve. Needed once after a repo was first
    imported under the old rule, which recorded only each problem's first
    solve; safe to repeat, since duplicates are refused by the unique index.
    """
    token = settings.github_token

    stored = (
        await db.execute(
            select(
                Submission.external_problem_id,
                Submission.problem_name,
                Submission.tags,
                Submission.difficulty_label,
                func.max(Submission.solved_at).label("latest"),
            )
            .where(Submission.user_id == user_id, Submission.platform == PLATFORM)
            .group_by(
                Submission.external_problem_id,
                Submission.problem_name,
                Submission.tags,
                Submission.difficulty_label,
            )
        )
    ).all()
    known = {row.external_problem_id for row in stored}
    by_slug = {
        leetcode_client.slug_from_folder(row.external_problem_id): {
            "user_id": user_id,
            "platform": PLATFORM,
            "external_problem_id": row.external_problem_id,
            "problem_name": row.problem_name,
            "tags": list(row.tags or []),
            "difficulty_rating": None,
            "difficulty_label": row.difficulty_label,
            "verdict": "OK",
        }
        for row in stored
    }
    newest = max((row.latest for row in stored if row.latest), default=None)

    rows: list[dict] = []
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        slugs = await leethub_client.fetch_solved_slugs(client, repo, token)
        new_slugs = not_yet_imported(slugs, known)

        # Repeats of problems already on record. Scanned from the repo's
        # commit log rather than per folder, so a quiet day costs a couple of
        # requests. A second past the newest stored solve, so that solve is
        # not re-read every time — the unique index would refuse it anyway.
        if by_slug:
            since = None if full or newest is None else newest + timedelta(seconds=1)
            events = await leethub_client.fetch_solution_commits(client, repo, token, since)
            fresh = {leetcode_client.slug_from_folder(f) for f in new_slugs}
            rows.extend(
                rows_for_resolves(
                    [(f, at) for f, at in events
                     if leetcode_client.slug_from_folder(f) not in fresh],
                    by_slug,
                )
            )

        if not new_slugs and not rows:
            return 0

        # Only fetched when there is something new — it covers every problem,
        # so re-reading it for a no-op sync would be wasted.
        tag_map = (
            await leethub_client.fetch_tag_map(client, repo, token) if new_slugs else {}
        )

        semaphore = asyncio.Semaphore(CONCURRENCY)

        async def load(slug: str) -> list[dict]:
            async with semaphore:
                title, difficulty = await leethub_client.fetch_problem_details(
                    client, repo, slug, token
                )
                dates = await leethub_client.fetch_solve_dates(client, repo, slug, token)
            # One row per solve, not one per problem: the folder's history is
            # the full record of every time it was done.
            return [
                {
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
                for solved_at in dates
            ]

        if new_slugs:
            for batch in await asyncio.gather(*(load(s) for s in new_slugs)):
                rows.extend(batch)

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
