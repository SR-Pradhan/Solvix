import httpx
import pytest

from app.clients import codeforces_client
from app.clients.codeforces_client import (
    CodeforcesError,
    CodeforcesHandleError,
    fetch_user_submissions,
)


def mock_transport(monkeypatch, handler):
    """Route the client's requests through a stub instead of the network."""
    real_client = httpx.AsyncClient

    def build(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(codeforces_client.httpx, "AsyncClient", build)


async def test_bad_handle_raises_handle_error(monkeypatch):
    mock_transport(
        monkeypatch,
        lambda req: httpx.Response(
            400, json={"status": "FAILED", "comment": "handle: User not found"}
        ),
    )
    with pytest.raises(CodeforcesHandleError, match="User not found"):
        await fetch_user_submissions("nope")


async def test_upstream_failure_raises_generic_error(monkeypatch):
    mock_transport(
        monkeypatch,
        lambda req: httpx.Response(
            503, json={"status": "FAILED", "comment": "temporarily unavailable"}
        ),
    )
    with pytest.raises(CodeforcesError) as exc:
        await fetch_user_submissions("tourist")
    assert not isinstance(exc.value, CodeforcesHandleError)


async def test_non_json_response_raises_generic_error(monkeypatch):
    mock_transport(
        monkeypatch,
        lambda req: httpx.Response(502, text="<html>gateway error</html>"),
    )
    with pytest.raises(CodeforcesError, match="non-JSON"):
        await fetch_user_submissions("tourist")


async def test_network_failure_raises_generic_error(monkeypatch):
    def boom(req):
        raise httpx.ConnectError("no route to host")

    mock_transport(monkeypatch, boom)
    with pytest.raises(CodeforcesError, match="Could not reach Codeforces"):
        await fetch_user_submissions("tourist")


async def test_success_returns_results(monkeypatch):
    mock_transport(
        monkeypatch,
        lambda req: httpx.Response(200, json={"status": "OK", "result": [{"id": 1}]}),
    )
    assert await fetch_user_submissions("tourist") == [{"id": 1}]
