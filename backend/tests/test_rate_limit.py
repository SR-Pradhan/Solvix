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


def test_client_key_reads_the_entry_our_own_proxy_wrote():
    # Behind a proxy every request appears to come from the proxy, which would
    # rate-limit all users as though they were one — so the header is used.
    # Counted from the right: with one proxy in front, the last entry is the
    # address it saw, and everything left of it came from the caller.
    assert client_key("10.0.0.1", "203.0.113.7", trusted_hops=1) == "203.0.113.7"


def test_a_forged_forwarded_header_cannot_win_a_fresh_allowance():
    """The bug this replaced.

    A caller that sends its own X-Forwarded-For controls the *left* of the
    list; the proxy appends what it actually saw. Trusting the leftmost entry
    let one attacker look like a new visitor on every request, which defeated
    the login limiter entirely.
    """
    real = "203.0.113.7"
    keys = {
        client_key("10.0.0.1", f"9.9.9.{n}, {real}", trusted_hops=1)
        for n in range(20)
    }
    assert keys == {real}


def test_two_proxies_are_counted_from_the_right_as_well():
    # Client, then a CDN, then Render: the client is two from the right.
    assert (
        client_key("10.0.0.1", "203.0.113.7, 198.51.100.1", trusted_hops=2)
        == "203.0.113.7"
    )


def test_the_table_does_not_grow_without_bound():
    """A flood of one-off addresses must not become the attack itself."""
    from app.services.rate_limit import MAX_TRACKED_KEYS

    limiter = RateLimiter()
    for n in range(MAX_TRACKED_KEYS + 500):
        limiter.record_failure(f"10.0.{n // 256}.{n % 256}", NOW)
    assert len(limiter._entries) <= MAX_TRACKED_KEYS + 1


def test_pruning_never_frees_somebody_who_is_blocked():
    """Eviction must not become a way to clear your own block."""
    from app.services.rate_limit import MAX_TRACKED_KEYS

    limiter = RateLimiter()
    for _ in range(limiter.max_failures):
        limiter.record_failure("attacker", NOW)
    assert limiter.retry_after("attacker", NOW) is not None

    for n in range(MAX_TRACKED_KEYS + 500):
        limiter.record_failure(f"10.0.{n // 256}.{n % 256}", NOW)

    assert limiter.retry_after("attacker", NOW) is not None


def test_client_key_falls_back_to_the_socket():
    assert client_key("203.0.113.7", None) == "203.0.113.7"
    assert client_key("203.0.113.7", "  ") == "203.0.113.7"


def test_client_key_never_returns_none():
    # A missing client would otherwise collapse every anonymous caller into a
    # single key by accident.
    assert client_key(None, None) == "unknown"


def test_eviction_stays_cheap_under_a_sustained_flood():
    """A guard against the fix becoming the problem.

    Trimming to exactly the cap put the table one insert over again straight
    away, so every later request paid for a full sweep and 200k addresses took
    minutes. Batching down to a lower mark makes it amortised. The threshold is
    deliberately loose — it is catching quadratic behaviour, not measuring
    performance.
    """
    import time

    from app.services.rate_limit import MAX_TRACKED_KEYS

    limiter = RateLimiter()
    started = time.monotonic()
    for n in range(MAX_TRACKED_KEYS * 5):
        limiter.record_failure(f"10.{n // 65536}.{(n // 256) % 256}.{n % 256}", NOW)
    elapsed = time.monotonic() - started

    assert len(limiter._entries) <= MAX_TRACKED_KEYS
    assert elapsed < 10, f"eviction looks quadratic again: {elapsed:.1f}s"
