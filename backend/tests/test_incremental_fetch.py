import httpx

from app.clients import codeforces_client
from app.clients.codeforces_client import PAGE_SIZE, fetch_submissions_since


def submission(epoch: int) -> dict:
    return {"id": epoch, "creationTimeSeconds": epoch}


def serve(monkeypatch, all_submissions: list[dict], calls: list[dict]):
    """Serve `all_submissions` newest-first, honouring from/count like Codeforces."""
    real_client = httpx.AsyncClient

    def handler(request: httpx.Request) -> httpx.Response:
        params = request.url.params
        start = int(params["from"]) - 1
        count = int(params.get("count", len(all_submissions)))
        calls.append({"from": start + 1, "count": count})
        return httpx.Response(
            200, json={"status": "OK", "result": all_submissions[start : start + count]}
        )

    def build(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(codeforces_client.httpx, "AsyncClient", build)


async def test_stops_at_the_first_already_stored_submission(monkeypatch):
    newest_first = [submission(e) for e in (500, 400, 300, 200, 100)]
    calls: list[dict] = []
    serve(monkeypatch, newest_first, calls)

    result = await fetch_submissions_since("tourist", since_epoch=300)

    assert [r["creationTimeSeconds"] for r in result] == [500, 400]
    assert len(calls) == 1


async def test_boundary_submission_is_excluded(monkeypatch):
    serve(monkeypatch, [submission(300), submission(200)], [])
    assert await fetch_submissions_since("tourist", since_epoch=300) == []


async def test_returns_everything_when_all_are_new(monkeypatch):
    newest_first = [submission(e) for e in (300, 200, 100)]
    serve(monkeypatch, newest_first, [])

    result = await fetch_submissions_since("tourist", since_epoch=50)
    assert len(result) == 3


async def test_paginates_past_the_page_size(monkeypatch):
    # 1500 submissions, all newer than the cutoff, forces a second page.
    newest_first = [submission(10_000 - i) for i in range(PAGE_SIZE + 500)]
    calls: list[dict] = []
    serve(monkeypatch, newest_first, calls)

    result = await fetch_submissions_since("tourist", since_epoch=0)

    assert len(result) == PAGE_SIZE + 500
    assert [c["from"] for c in calls] == [1, PAGE_SIZE + 1]


async def test_empty_history(monkeypatch):
    serve(monkeypatch, [], [])
    assert await fetch_submissions_since("newbie", since_epoch=0) == []


# --- repeat solves of known problems ---------------------------------------

from datetime import datetime

from app.services.leetcode_ingestion_service import rows_for_resolves


def known_row(pid="0876-middle-of-the-linked-list"):
    return {"external_problem_id": pid, "problem_name": "Middle", "tags": ["Linked List"],
            "difficulty_label": "Easy", "verdict": "OK"}


def test_a_repeat_copies_the_stored_problem_and_takes_the_new_date():
    known = {"middle-of-the-linked-list": known_row()}
    at = datetime(2026, 8, 19, 6, 23)
    (row,) = rows_for_resolves([("0876-middle-of-the-linked-list", at)], known)
    assert row["solved_at"] == at
    assert row["tags"] == ["Linked List"]
    # Keeps the id the problem was stored under, so both solves share one
    # identity — the bug that once put "Reverse Bits" in the reminders twice.
    assert row["external_problem_id"] == "0876-middle-of-the-linked-list"


def test_a_folder_stored_without_its_number_still_matches():
    # The two import paths name problems differently; the canonical slug
    # reconciles them.
    known = {"merge-intervals": known_row("merge-intervals")}
    rows = rows_for_resolves([("0056-merge-intervals", datetime(2026, 8, 20))], known)
    assert rows and rows[0]["external_problem_id"] == "merge-intervals"


def test_an_unknown_folder_is_left_for_the_new_problem_path():
    assert rows_for_resolves([("0999-brand-new", datetime(2026, 8, 20))], {}) == []
