"""Reads solved LeetCode problems out of a LeetHub 2.0-synced GitHub repo.

LeetCode has no public API, but the LeetHub browser extension commits every
accepted solution to GitHub in a fixed layout:

    <repo>/
      README.md                  topic tags, grouped by tag
      stats.json                 every solved problem folder
      0001-two-sum/
        README.md                <h2>title</h2><h3>difficulty</h3>
        0001-two-sum.java        the solution

so the GitHub API gives us tags, difficulty, and solve dates without scraping.
"""

import re
from datetime import datetime

import httpx

GITHUB_API = "https://api.github.com"
GITHUB_RAW = "https://raw.githubusercontent.com"

# Files LeetHub keeps at the repo root that are not problems.
NON_PROBLEM_PATHS = {"README.md", "stats.json"}

TITLE_RE = re.compile(r"<h2><a href=\"[^\"]*\">(?:\d+\.\s*)?(.*?)</a></h2>", re.I)
DIFFICULTY_RE = re.compile(r"<h3>(Easy|Medium|Hard)</h3>", re.I)
# Rows in the root README's tag tables: | [0001-two-sum](https://...) |
TAG_HEADING_RE = re.compile(r"^##\s+(.+?)\s*$", re.M)
TAG_ROW_RE = re.compile(r"\|\s*\[([^\]]+)\]\(")


class LeetHubError(Exception):
    """The repo could not be read."""


class LeetHubRepoError(LeetHubError):
    """The repo name is wrong, private, or not a LeetHub repo — the user's mistake."""


class LeetHubRateLimited(LeetHubError):
    """GitHub's rate limit was hit; a token raises it from 60/hour to 5000."""


def _headers(token: str | None) -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


async def _get(client: httpx.AsyncClient, url: str, token: str | None) -> httpx.Response:
    try:
        response = await client.get(url, headers=_headers(token))
    except httpx.RequestError as e:
        raise LeetHubError(f"Could not reach GitHub: {e}") from e

    if response.status_code == 404:
        raise LeetHubRepoError("Repository or file not found. Check the owner/repo name.")
    if response.status_code in (403, 429) and "rate limit" in response.text.lower():
        raise LeetHubRateLimited(
            "GitHub rate limit reached. Set GITHUB_TOKEN in the backend .env "
            "to raise the limit from 60 to 5000 requests per hour."
        )
    if response.status_code >= 400:
        raise LeetHubError(f"GitHub returned HTTP {response.status_code}")
    return response


def parse_tag_map(readme: str) -> dict[str, list[str]]:
    """Map problem slug -> tags, from the root README's per-topic tables."""
    tags_by_problem: dict[str, list[str]] = {}

    sections = TAG_HEADING_RE.split(readme)
    # split() yields [preamble, heading, body, heading, body, ...]
    for i in range(1, len(sections) - 1, 2):
        tag = sections[i].strip()
        if tag.lower() == "leetcode topics":
            continue
        for slug in TAG_ROW_RE.findall(sections[i + 1]):
            tags_by_problem.setdefault(slug, []).append(tag)

    return tags_by_problem


def parse_problem_readme(readme: str) -> tuple[str | None, str | None]:
    """Extract (title, difficulty) from a problem's README."""
    title = TITLE_RE.search(readme)
    difficulty = DIFFICULTY_RE.search(readme)
    return (
        title.group(1).strip() if title else None,
        difficulty.group(1).capitalize() if difficulty else None,
    )


async def fetch_solved_slugs(
    client: httpx.AsyncClient, repo: str, token: str | None
) -> list[str]:
    """Every problem folder in the repo, from LeetHub's own stats.json."""
    response = await _get(client, f"{GITHUB_RAW}/{repo}/HEAD/stats.json", token)
    try:
        stats = response.json()
    except ValueError as e:
        raise LeetHubRepoError("stats.json is not valid JSON — is this a LeetHub repo?") from e

    shas = stats.get("leetcode", {}).get("shas")
    if not isinstance(shas, dict):
        raise LeetHubRepoError(
            "stats.json has no LeetHub problem list — is this a LeetHub 2.0 repo?"
        )
    return sorted(slug for slug in shas if slug not in NON_PROBLEM_PATHS)


async def fetch_tag_map(
    client: httpx.AsyncClient, repo: str, token: str | None
) -> dict[str, list[str]]:
    response = await _get(client, f"{GITHUB_RAW}/{repo}/HEAD/README.md", token)
    return parse_tag_map(response.text)


async def fetch_problem_details(
    client: httpx.AsyncClient, repo: str, slug: str, token: str | None
) -> tuple[str | None, str | None]:
    response = await _get(client, f"{GITHUB_RAW}/{repo}/HEAD/{slug}/README.md", token)
    return parse_problem_readme(response.text)


async def fetch_first_commit_date(
    client: httpx.AsyncClient, repo: str, slug: str, token: str | None
) -> datetime | None:
    """When the problem folder first appeared — i.e. when it was solved."""
    response = await _get(
        client, f"{GITHUB_API}/repos/{repo}/commits?path={slug}&per_page=100", token
    )
    commits = response.json()
    if not commits:
        return None

    # GitHub returns newest first, so the oldest commit is the original solve.
    stamp = commits[-1]["commit"]["author"]["date"]
    return datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ")
