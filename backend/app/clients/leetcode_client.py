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
