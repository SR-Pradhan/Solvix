"""Reads the public LeetCode problem catalogue.

LeetCode has no REST API, but its GraphQL endpoint answers `problemsetQuestionList`
without authentication. That gives every problem's slug, title, difficulty and
tags — enough to work out which problems in a topic a user has not solved, since
LeetHub already tells us which ones they have.

Submission *history* still needs a session cookie and is deliberately not
attempted here.
"""

import re
import time

import httpx

GRAPHQL_URL = "https://leetcode.com/graphql"
PROBLEM_URL = "https://leetcode.com/problems/{slug}/"

# The catalogue changes when LeetCode adds problems, which is not often.
CACHE_TTL_SECONDS = 6 * 3600
PAGE_SIZE = 100

QUERY = """
query($cat: String, $skip: Int, $limit: Int, $filters: QuestionListFilterInput) {
  problemsetQuestionList: questionList(
    categorySlug: $cat, skip: $skip, limit: $limit, filters: $filters
  ) {
    total: totalNum
    questions: data {
      titleSlug
      title
      difficulty
      paidOnly: isPaidOnly
      topicTags { name slug }
    }
  }
}
"""

_cache: dict[str, tuple[float, list[dict]]] = {}


class LeetCodeError(Exception):
    """The catalogue could not be read."""


class LeetCodeUserNotFound(LeetCodeError):
    """The username does not exist — the caller's mistake, not an outage."""


def tag_slug(tag: str) -> str:
    """Turn a display tag into LeetCode's slug form.

    LeetHub records tags as they appear on the site ("Binary Search"), while the
    GraphQL filter wants slugs ("binary-search").
    """
    cleaned = re.sub(r"[^a-z0-9]+", "-", tag.lower()).strip("-")
    return cleaned


def slug_from_folder(folder: str) -> str:
    """Recover a problem slug from a LeetHub folder name.

    LeetHub names folders "0001-two-sum"; the catalogue keys on "two-sum".
    """
    return re.sub(r"^\d+-", "", folder.strip())


async def fetch_problems_for_tag(tag: str, limit: int = PAGE_SIZE) -> list[dict]:
    """Every catalogue problem carrying `tag`, newest API shape, cached."""
    slug = tag_slug(tag)
    if not slug:
        return []

    hit = _cache.get(slug)
    if hit and time.monotonic() - hit[0] < CACHE_TTL_SECONDS:
        return hit[1]

    payload = {
        "query": QUERY,
        "variables": {
            "cat": "",
            "skip": 0,
            "limit": limit,
            "filters": {"tags": [slug]},
        },
    }

    try:
        async with httpx.AsyncClient(timeout=25) as client:
            response = await client.post(
                GRAPHQL_URL,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    # LeetCode rejects requests without a browser-like agent.
                    "User-Agent": "Mozilla/5.0 (compatible; Solvix/1.0)",
                },
            )
    except httpx.RequestError as e:
        raise LeetCodeError(f"Could not reach LeetCode: {e}") from e

    if response.status_code >= 400:
        raise LeetCodeError(f"LeetCode returned HTTP {response.status_code}")

    try:
        listing = response.json()["data"]["problemsetQuestionList"]
        questions = listing["questions"] or []
    except (ValueError, KeyError, TypeError) as e:
        raise LeetCodeError("LeetCode returned an unexpected response shape") from e

    _cache[slug] = (time.monotonic(), questions)
    return questions


PROFILE_QUERY = """
query($u: String!) {
  matchedUser(username: $u) {
    submitStatsGlobal { acSubmissionNum { difficulty count } }
    tagProblemCounts {
      advanced { tagName problemsSolved }
      intermediate { tagName problemsSolved }
      fundamental { tagName problemsSolved }
    }
  }
}
"""

RECENT_AC_QUERY = """
query($u: String!, $n: Int) {
  recentAcSubmissionList(username: $u, limit: $n) {
    title
    titleSlug
    timestamp
  }
}
"""

QUESTION_QUERY = """
query($slug: String!) {
  question(titleSlug: $slug) {
    title
    difficulty
    topicTags { name }
  }
}
"""


async def _graphql(client: httpx.AsyncClient, query: str, variables: dict) -> dict:
    try:
        response = await client.post(
            GRAPHQL_URL,
            json={"query": query, "variables": variables},
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (compatible; Solvix/1.0)",
            },
        )
    except httpx.RequestError as e:
        raise LeetCodeError(f"Could not reach LeetCode: {e}") from e

    if response.status_code >= 400:
        raise LeetCodeError(f"LeetCode returned HTTP {response.status_code}")

    try:
        body = response.json()
    except ValueError as e:
        raise LeetCodeError("LeetCode returned a non-JSON response") from e

    data = body.get("data")
    if data is None:
        raise LeetCodeError("LeetCode returned no data for that query")
    return data


def parse_profile(data: dict) -> dict:
    """Flatten the profile response into totals, difficulty split and tags."""
    user = data.get("matchedUser")
    if not user:
        raise LeetCodeUserNotFound(
            "No LeetCode user with that username. Check the spelling."
        )

    counts = {
        row["difficulty"]: row["count"]
        for row in user["submitStatsGlobal"]["acSubmissionNum"]
    }

    buckets = user.get("tagProblemCounts") or {}
    tags = [
        {"tag": row["tagName"], "solved": row["problemsSolved"]}
        for bucket in ("fundamental", "intermediate", "advanced")
        for row in buckets.get(bucket) or []
        if row["problemsSolved"] > 0
    ]
    tags.sort(key=lambda t: (-t["solved"], t["tag"]))

    return {
        "total_solved": counts.get("All", 0),
        "easy": counts.get("Easy", 0),
        "medium": counts.get("Medium", 0),
        "hard": counts.get("Hard", 0),
        "tags": tags,
    }


async def fetch_profile(username: str) -> dict:
    async with httpx.AsyncClient(timeout=25) as client:
        data = await _graphql(client, PROFILE_QUERY, {"u": username})
    return parse_profile(data)


async def fetch_recent_ac(username: str, limit: int = 20) -> list[dict]:
    """The most recent accepted submissions, with real LeetCode timestamps.

    Public, but capped at 20 by LeetCode — enough to catch solves that have not
    reached the LeetHub repo yet, not enough to rebuild a full history.
    """
    async with httpx.AsyncClient(timeout=25) as client:
        data = await _graphql(client, RECENT_AC_QUERY, {"u": username, "n": limit})
    return data.get("recentAcSubmissionList") or []


async def fetch_question(slug: str) -> dict | None:
    """Title, difficulty and tags for one problem."""
    async with httpx.AsyncClient(timeout=25) as client:
        data = await _graphql(client, QUESTION_QUERY, {"slug": slug})

    question = data.get("question")
    if not question:
        return None
    return {
        "title": question.get("title") or slug,
        "difficulty": question.get("difficulty"),
        "tags": [t["name"] for t in question.get("topicTags") or []],
    }
