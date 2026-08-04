from datetime import datetime, timezone

import httpx

CF_API_BASE = "https://codeforces.com/api"


class CodeforcesError(Exception):
    """Codeforces was reachable but the request failed, or it was unreachable."""


class CodeforcesHandleError(CodeforcesError):
    """The handle itself is rejected — the caller's mistake, not an outage."""


async def fetch_user_submissions(handle: str) -> list[dict]:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{CF_API_BASE}/user.status", params={"handle": handle})
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
