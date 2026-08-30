"""What is left to solve in a given topic.

Both platforms answer the same question from opposite directions: we know what
the user has solved, and each platform publishes what exists. The difference is
the practice list.
"""

import re
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.clients import leetcode_client
from app.db.models import Submission
from app.services.recommendation_service import _problemset as codeforces_problemset

ACCEPTED = "OK"
DIFFICULTY_ORDER = {"Easy": 0, "Medium": 1, "Hard": 2}


def problem_url(platform: str, external_id: str) -> str | None:
    """Rebuild a link to a problem from the id we stored for it.

    Codeforces ids are the contest number followed by the index ("1234A", and
    occasionally "2249E2"), so the split is digits-then-rest rather than a
    fixed length. LeetCode ids are LeetHub folder names.
    """
    if platform == "leetcode":
        slug = leetcode_client.slug_from_folder(external_id)
        return leetcode_client.PROBLEM_URL.format(slug=slug) if slug else None

    match = re.match(r"^(\d+)(.+)$", external_id)
    if not match:
        return None
    contest, index = match.groups()
    return f"https://codeforces.com/problemset/problem/{contest}/{index}"


async def solved_in_topic(
    db: AsyncSession, user_id: int, tag: str, limit: int = 10
) -> dict:
    """Problems already solved in a topic, stalest first.

    This is the revision list: what to re-attempt in a topic that has decayed,
    ordered by how long it has been since you last got it right.
    """
    rows = (
        await db.execute(
            select(
                Submission.external_problem_id,
                Submission.platform,
                func.min(Submission.problem_name).label("problem_name"),
                func.max(Submission.solved_at).label("last_solved_at"),
            )
            .where(
                Submission.user_id == user_id,
                Submission.verdict == ACCEPTED,
                Submission.tags.any(tag),
            )
            .group_by(Submission.external_problem_id, Submission.platform)
            # Longest since the last correct solve comes first — that is the
            # one whose memory has decayed most.
            .order_by(func.max(Submission.solved_at))
            .limit(limit)
        )
    ).all()

    today = clock.today()
    problems = []
    for pid, platform, name, last_solved in rows:
        days = (today - last_solved.date()).days
        problems.append(
            {
                "id": pid,
                "name": name or pid,
                "platform": platform,
                "last_solved_at": last_solved.date(),
                "days_ago": max(0, days),
                "url": problem_url(platform, pid),
            }
        )

    return {"tag": tag, "problems": problems}


async def _solved_ids(db: AsyncSession, user_id: int, platform: str) -> set[str]:
    rows = (
        await db.scalars(
            select(Submission.external_problem_id).where(
                Submission.user_id == user_id,
                Submission.platform == platform,
                Submission.verdict == ACCEPTED,
            )
        )
    ).all()
    return set(rows)


async def _leetcode_unsolved(
    db: AsyncSession, user_id: int, tag: str, limit: int
) -> list[dict]:
    solved_folders = await _solved_ids(db, user_id, "leetcode")
    solved_slugs = {leetcode_client.slug_from_folder(f) for f in solved_folders}

    catalogue = await leetcode_client.fetch_problems_for_tag(tag)

    unsolved = [
        {
            "id": q["titleSlug"],
            "name": q["title"],
            "difficulty": q["difficulty"],
            "rating": None,
            "tags": [t["name"] for t in q.get("topicTags", [])],
            "url": leetcode_client.PROBLEM_URL.format(slug=q["titleSlug"]),
        }
        for q in catalogue
        # Premium problems are not openable without a subscription, so
        # suggesting them is a dead end.
        if not q.get("paidOnly") and q["titleSlug"] not in solved_slugs
    ]

    unsolved.sort(key=lambda p: (DIFFICULTY_ORDER.get(p["difficulty"], 9), p["name"]))
    return unsolved[:limit]


async def _codeforces_unsolved(
    db: AsyncSession, user_id: int, tag: str, limit: int
) -> list[dict]:
    solved = await _solved_ids(db, user_id, "codeforces")
    catalogue = await codeforces_problemset()

    unsolved = []
    for problem in catalogue:
        contest_id = problem.get("contestId")
        index = problem.get("index")
        if contest_id is None or index is None:
            continue
        if tag not in problem.get("tags", []):
            continue
        pid = f"{contest_id}{index}"
        if pid in solved:
            continue
        unsolved.append(
            {
                "id": pid,
                "name": problem.get("name", pid),
                "difficulty": None,
                "rating": problem.get("rating"),
                "tags": problem.get("tags", []),
                "url": (
                    f"https://codeforces.com/problemset/problem/{contest_id}/{index}"
                ),
            }
        )

    # Easiest first: the point is to get unstuck on a weak topic, not to find
    # the hardest problem carrying that tag. Unrated problems go last.
    unsolved.sort(key=lambda p: (p["rating"] is None, p["rating"] or 0, p["name"]))
    return unsolved[:limit]


async def unsolved_in_topic(
    db: AsyncSession, user_id: int, tag: str, platform: str, limit: int = 20
) -> dict:
    if platform == "leetcode":
        problems = await _leetcode_unsolved(db, user_id, tag, limit)
    else:
        problems = await _codeforces_unsolved(db, user_id, tag, limit)

    return {"tag": tag, "platform": platform, "problems": problems}
