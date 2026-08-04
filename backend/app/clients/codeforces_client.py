from datetime import datetime, timezone

import httpx

CF_API_BASE = "https://codeforces.com/api"


class CodeforcesError(Exception):
    """Codeforces was reachable but the request failed, or it was unreachable."""


class CodeforcesHandleError(CodeforcesError):
    """The handle itself is rejected — the caller's mistake, not an outage."""


PAGE_SIZE = 1000


async def fetch_user_submissions(
    handle: str, from_index: int = 1, count: int | None = None
) -> list[dict]:
    """Fetch submissions newest-first. `from_index` is 1-based, as Codeforces wants."""
    params: dict[str, str | int] = {"handle": handle, "from": from_index}
    if count is not None:
        params["count"] = count

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(f"{CF_API_BASE}/user.status", params=params)
    except httpx.RequestError as e:
        raise CodeforcesError(f"Could not reach Codeforces: {e}") from e

    try:
        data = response.json()
    except ValueError as e:
        raise CodeforcesError(
            f"Codeforces returned a non-JSON response (HTTP {response.status_code})"
        ) from e

    if data.get("status") != "OK":
        comment = data.get("comment", "Codeforces API request failed")
        # Codeforces answers 400 for a malformed or unknown handle and 5xx for
        # its own problems, so the status code sorts user error from outage.
        if response.status_code == 400:
            raise CodeforcesHandleError(comment)
        raise CodeforcesError(comment)

    return data["result"]


async def fetch_problemset() -> list[dict]:
    """The full Codeforces problemset with tags and ratings."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(f"{CF_API_BASE}/problemset.problems")
    except httpx.RequestError as e:
        raise CodeforcesError(f"Could not reach Codeforces: {e}") from e

    try:
        data = response.json()
    except ValueError as e:
        raise CodeforcesError(
            f"Codeforces returned a non-JSON response (HTTP {response.status_code})"
        ) from e

    if data.get("status") != "OK":
        raise CodeforcesError(data.get("comment", "Codeforces API request failed"))

    return data["result"]["problems"]


async def fetch_submissions_since(handle: str, since_epoch: int) -> list[dict]:
    """Fetch only submissions newer than `since_epoch`.

    Codeforces returns newest first, so we walk pages and stop at the first
    submission we have already stored rather than pulling the whole history.
    """
    collected: list[dict] = []
    from_index = 1

    while True:
        page = await fetch_user_submissions(handle, from_index=from_index, count=PAGE_SIZE)
        if not page:
            return collected

        for raw in page:
            if raw["creationTimeSeconds"] <= since_epoch:
                return collected
            collected.append(raw)

        if len(page) < PAGE_SIZE:
            return collected
        from_index += PAGE_SIZE


def to_submission_row(raw: dict) -> dict:
    problem = raw["problem"]
    return {
        "external_problem_id": f"{problem.get('contestId', '')}{problem.get('index', '')}",
        "problem_name": problem.get("name"),
        "tags": problem.get("tags", []),
        "difficulty_rating": problem.get("rating"),
        "verdict": raw.get("verdict", "UNKNOWN"),
        "solved_at": datetime.fromtimestamp(raw["creationTimeSeconds"], tz=timezone.utc).replace(tzinfo=None),
    }
