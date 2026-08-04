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
