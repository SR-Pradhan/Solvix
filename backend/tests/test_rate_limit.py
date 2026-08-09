from datetime import datetime, timedelta

from app.services.rate_limit import RateLimiter, client_key

NOW = datetime(2026, 8, 10, 12, 0, 0)


def _limiter():
    return RateLimiter(
        max_failures=3,
        window=timedelta(minutes=5),
        block_for=timedelta(minutes=15),
    )


def test_allows_callers_under_the_limit():
    limiter = _limiter()
    limiter.record_failure("1.1.1.1", NOW)
    limiter.record_failure("1.1.1.1", NOW + timedelta(seconds=1))
    assert limiter.retry_after("1.1.1.1", NOW + timedelta(seconds=2)) is None


def test_blocks_at_the_limit():
    limiter = _limiter()
    for i in range(3):
        limiter.record_failure("1.1.1.1", NOW + timedelta(seconds=i))
    wait = limiter.retry_after("1.1.1.1", NOW + timedelta(seconds=3))
    assert wait is not None and 890 < wait <= 900


def test_failures_outside_the_window_do_not_count():
    limiter = _limiter()
    limiter.record_failure("1.1.1.1", NOW)
    limiter.record_failure("1.1.1.1", NOW + timedelta(minutes=6))
    # The first failure has aged out, so this is the second in the window,
    # not the third.
    limiter.record_failure("1.1.1.1", NOW + timedelta(minutes=7))
    assert limiter.retry_after("1.1.1.1", NOW + timedelta(minutes=7)) is None


def test_block_expires():
    limiter = _limiter()
    for i in range(3):
        limiter.record_failure("1.1.1.1", NOW + timedelta(seconds=i))
    later = NOW + timedelta(minutes=16)
    assert limiter.retry_after("1.1.1.1", later) is None
    # One failure after the block lifts must not immediately re-block: the
    # count that caused it is gone, not merely paused.
    limiter.record_failure("1.1.1.1", later)
    assert limiter.retry_after("1.1.1.1", later) is None


def test_one_caller_does_not_block_another():
    limiter = _limiter()
    for i in range(3):
        limiter.record_failure("1.1.1.1", NOW + timedelta(seconds=i))
    assert limiter.retry_after("2.2.2.2", NOW + timedelta(seconds=3)) is None


def test_success_clears_the_record():
    limiter = _limiter()
    limiter.record_failure("1.1.1.1", NOW)
    limiter.record_failure("1.1.1.1", NOW + timedelta(seconds=1))
    limiter.record_success("1.1.1.1")
    # Two fresh failures would otherwise be the third and fourth overall.
    limiter.record_failure("1.1.1.1", NOW + timedelta(seconds=2))
    limiter.record_failure("1.1.1.1", NOW + timedelta(seconds=3))
    assert limiter.retry_after("1.1.1.1", NOW + timedelta(seconds=4)) is None


def test_client_key_prefers_the_original_caller():
    # Behind a proxy every request appears to come from the proxy, which would
    # rate-limit all users as though they were one.
    assert client_key("10.0.0.1", "203.0.113.7, 10.0.0.1") == "203.0.113.7"


def test_client_key_falls_back_to_the_socket():
    assert client_key("203.0.113.7", None) == "203.0.113.7"
    assert client_key("203.0.113.7", "  ") == "203.0.113.7"


def test_client_key_never_returns_none():
    # A missing client would otherwise collapse every anonymous caller into a
    # single key by accident.
    assert client_key(None, None) == "unknown"
