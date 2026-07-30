from datetime import datetime, timezone

import httpx

CF_API_BASE = "https://codeforces.com/api"


class CodeforcesError(Exception):
    pass


async def fetch_user_submissions(handle: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(f"{CF_API_BASE}/user.status", params={"handle": handle})

    data = response.json()
    if data.get("status") != "OK":
        raise CodeforcesError(data.get("comment", "Codeforces API request failed"))

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
