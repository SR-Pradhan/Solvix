import time
from collections import Counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.codeforces_client import fetch_problemset
from app.db.models import Submission

ACCEPTED = "OK"
PLATFORM = "codeforces"

# A tag needs a reasonable pool of problems before "you have not done many of
# these" means anything — otherwise obscure tags dominate every result.
MIN_PROBLEMS_PER_TAG = 40
MIN_SOLVED_FOR_SIGNAL = 10
DEFAULT_TARGET_RATING = 1200
# Aim slightly above current level: at or below it there is nothing to learn,
# far above it the problems are unattemptable.
BAND_BELOW, BAND_ABOVE = 0, 200

_cache: dict[str, tuple[float, list[dict]]] = {}
CACHE_TTL_SECONDS = 3600


async def _problemset() -> list[dict]:
    """Cached problemset — it is ~10k problems and changes only when contests end."""
    hit = _cache.get("problems")
    if hit and time.monotonic() - hit[0] < CACHE_TTL_SECONDS:
        return hit[1]

    problems = await fetch_problemset()
    _cache["problems"] = (time.monotonic(), problems)
    return problems


async def _solved(db: AsyncSession, user_id: int) -> list[tuple[str, list[str], int | None]]:
    rows = (
        await db.execute(
            select(
                Submission.external_problem_id,
                Submission.tags,
                Submission.difficulty_rating,
            )
            .where(
                Submission.user_id == user_id,
                Submission.platform == PLATFORM,
                Submission.verdict == ACCEPTED,
            )
            .distinct(Submission.external_problem_id)
            .order_by(Submission.external_problem_id)
        )
    ).all()
    return [(r[0], r[1] or [], r[2]) for r in rows]


def _weak_tags(
    solved_tag_counts: Counter, total_solved: int, problemset: list[dict], top_n: int
) -> list[dict]:
    """Tags the user has under-practised relative to how common they are.

    Comparing shares rather than raw counts stops the result being a list of
    rare tags nobody solves much of.
    """
    global_counts: Counter = Counter()
    for problem in problemset:
        global_counts.update(problem.get("tags", []))

    total_problems = len(problemset) or 1

    scored = []
    for tag, pool in global_counts.items():
        if pool < MIN_PROBLEMS_PER_TAG:
            continue
        solved = solved_tag_counts.get(tag, 0)
        user_share = solved / total_solved if total_solved else 0.0
        global_share = pool / total_problems
        deficit = global_share - user_share
        if deficit <= 0:
            continue
        scored.append(
            {
                "tag": tag,
                "solved_count": solved,
                "deficit": round(deficit, 4),
            }
        )

    scored.sort(key=lambda t: (-t["deficit"], t["tag"]))
    return scored[:top_n]


def _target_rating(ratings: list[int]) -> int:
    if not ratings:
        return DEFAULT_TARGET_RATING
    # The 90th percentile: what the user manages when stretching. A mean or
    # median would be dragged down by the pile of warm-up problems that most
    # solve histories contain.
    ranked = sorted(ratings)
    stretch = ranked[min(len(ranked) - 1, int(len(ranked) * 0.9))]
    return int(round(stretch / 100) * 100)


async def get_recommendations(db: AsyncSession, user_id: int, limit: int = 10) -> dict:
    solved = await _solved(db, user_id)
    solved_ids = {pid for pid, _, _ in solved}
    tag_counts = Counter(tag for _, tags, _ in solved for tag in tags)
    ratings = [r for _, _, r in solved if r is not None]

    if len(solved) < MIN_SOLVED_FOR_SIGNAL:
        return {
            "target_rating": DEFAULT_TARGET_RATING,
            "weak_tags": [],
            "problems": [],
            "note": (
                f"Solve at least {MIN_SOLVED_FOR_SIGNAL} problems so Solvix can "
                "tell which tags you are weak at."
            ),
        }

    problemset = await _problemset()
    weak = _weak_tags(tag_counts, len(solved), problemset, top_n=5)
    weak_names = {t["tag"] for t in weak}
    target = _target_rating(ratings)
    low, high = target - BAND_BELOW, target + BAND_ABOVE

    candidates = []
    for problem in problemset:
        rating = problem.get("rating")
        contest_id = problem.get("contestId")
        index = problem.get("index")
        if rating is None or contest_id is None or index is None:
            continue
        if not (low <= rating <= high):
            continue
        pid = f"{contest_id}{index}"
        if pid in solved_ids:
            continue
        matched = weak_names.intersection(problem.get("tags", []))
        if not matched:
            continue
        candidates.append(
            {
                "problem_id": pid,
                "contest_id": contest_id,
                "name": problem.get("name", pid),
                "rating": rating,
                "tags": problem.get("tags", []),
                "matched_tags": sorted(matched),
                "url": f"https://codeforces.com/problemset/problem/{contest_id}/{index}",
            }
        )

    # More weak tags hit means more relevant; recent contests first as a
    # tiebreak, since newer problems are better maintained.
    candidates.sort(key=lambda c: (-len(c["matched_tags"]), -c["contest_id"]))

    return {
        "target_rating": target,
        "weak_tags": weak,
        "problems": candidates[:limit],
        "note": None,
    }
