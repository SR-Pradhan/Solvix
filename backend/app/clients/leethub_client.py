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


async def fetch_solution_source(
    client: httpx.AsyncClient, repo: str, slug: str, token: str | None
) -> tuple[str, str] | None:
    """The solution file for one problem, as (filename, source).

    LeetHub names the file after the folder, so the path is predictable and no
    directory listing is needed — one request per problem instead of two. Older
    commits sometimes drop the numeric prefix, so that spelling is tried too.

    Returns None when nothing matches rather than raising: a repo with a
    missing or unsupported file is an ordinary gap, not a broken sync.
    """
    names = [slug]
    if "-" in slug and slug.split("-", 1)[0].isdigit():
        names.append(slug.split("-", 1)[1])

    for name in names:
        for extension in (".java", ".py"):
            url = f"{GITHUB_RAW}/{repo}/HEAD/{slug}/{name}{extension}"
            try:
                response = await client.get(url, headers=_headers(token))
            except httpx.HTTPError:
                continue
            if response.status_code == 200:
                return name + extension, response.text
    return None


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


# LeetHub writes two commits per accepted submission: one for the README and
# one for the solution file, whose message reports the runtime. Only the second
# is a solve; counting both would double every day.
SOLUTION_COMMIT_PREFIX = "Time:"


def is_solution_commit(message: str) -> bool:
    return message.lstrip().startswith(SOLUTION_COMMIT_PREFIX)


def slug_from_path(path: str) -> str | None:
    """The problem folder a changed file belongs to, or None for repo files."""
    folder = path.split("/", 1)[0]
    if not folder or folder in NON_PROBLEM_PATHS or "/" not in path:
        return None
    return folder


def _stamp(commit: dict) -> datetime:
    return datetime.strptime(commit["commit"]["author"]["date"], "%Y-%m-%dT%H:%M:%SZ")


def solve_events(commits: list[dict], files_of: dict[str, list[str]]) -> list[tuple[str, datetime]]:
    """(folder, solved_at) for every solution commit, given each commit's files.

    Pure, so the rule can be tested without GitHub: a commit counts once per
    problem folder it touched, and only if its message is a LeetHub solution
    message. README-only commits and the stats file are ignored.
    """
    events: list[tuple[str, datetime]] = []
    for commit in commits:
        if not is_solution_commit(commit["commit"]["message"]):
            continue
        seen: set[str] = set()
        for path in files_of.get(commit["sha"], []):
            slug = slug_from_path(path)
            if slug and slug not in seen:
                seen.add(slug)
                events.append((slug, _stamp(commit)))
    return events


async def fetch_solve_dates(
    client: httpx.AsyncClient, repo: str, slug: str, token: str | None
) -> list[datetime]:
    """Every time the problem was solved, oldest first.

    The same request the old import always made — it fetched the whole
    history of the folder and kept only the oldest entry, so a problem
    solved again a week later left no trace. Revisiting a problem is exactly
    what the revision reminders ask for, and it was the one kind of practice
    the app could not see.
    """
    response = await _get(
        client, f"{GITHUB_API}/repos/{repo}/commits?path={slug}&per_page=100", token
    )
    dates = [
        _stamp(c) for c in response.json() if is_solution_commit(c["commit"]["message"])
    ]
    return sorted(dates)


async def fetch_solution_commits(
    client: httpx.AsyncClient, repo: str, token: str | None, since: datetime | None
) -> list[tuple[str, datetime]]:
    """Every solve in the repo after `since`, as (folder, solved_at).

    One request per page of history plus one per solution commit, instead of
    one per problem folder — so a daily sync that finds three new solves costs
    about four requests rather than a hundred and twenty.
    """
    commits: list[dict] = []
    page = 1
    while True:
        url = f"{GITHUB_API}/repos/{repo}/commits?per_page=100&page={page}"
        if since is not None:
            url += "&since=" + since.strftime("%Y-%m-%dT%H:%M:%SZ")
        batch = (await _get(client, url, token)).json()
        commits.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    files_of: dict[str, list[str]] = {}
    for commit in commits:
        if not is_solution_commit(commit["commit"]["message"]):
            continue
        detail = (await _get(client, commit["url"], token)).json()
        files_of[commit["sha"]] = [f["filename"] for f in detail.get("files", [])]

    return solve_events(commits, files_of)
