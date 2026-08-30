"""In-memory rate limiting for the endpoints an attacker would hammer.

Deliberately a plain dictionary rather than Redis. The API runs as a single
instance, so a shared store would be infrastructure bought for nothing; the
trade-off is that counters reset on deploy and would not be shared if the
service is ever scaled to two instances. Both are acceptable now and both are
written down rather than discovered later.

The class holds no clock of its own — every method takes `now`. That is what
makes the whole thing testable without sleeping.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.core.config import settings

# A dictionary keyed by caller address grows with the number of distinct
# addresses seen, and an attacker chooses that number. Bounded so a flood of
# one-off addresses cannot use the limiter itself as the attack.
MAX_TRACKED_KEYS = 10_000

# Eviction drops to here rather than just under the cap. Trimming to exactly
# the limit would put the table one insert over again immediately, so every
# subsequent request would pay for a full sweep — turning the defence into the
# denial of service it was meant to prevent. Batching makes the sweep amortised
# to roughly one per thousand inserts.
PRUNE_TARGET = 9_000


@dataclass
class _Entry:
    failures: list[datetime] = field(default_factory=list)
    blocked_until: datetime | None = None


class RateLimiter:
    """Blocks a key after too many failures inside a rolling window.

    Only *failures* are counted. Counting every attempt would lock out someone
    who logs in correctly several times from the same office network, which
    punishes the wrong person.
    """

    def __init__(
        self,
        max_failures: int = 5,
        window: timedelta = timedelta(minutes=5),
        block_for: timedelta = timedelta(minutes=15),
    ) -> None:
        self.max_failures = max_failures
        self.window = window
        self.block_for = block_for
        self._entries: dict[str, _Entry] = {}

    def retry_after(self, key: str, now: datetime) -> int | None:
        """Seconds the caller must wait, or None if it may proceed."""
        entry = self._entries.get(key)
        if entry is None or entry.blocked_until is None:
            return None
        if now >= entry.blocked_until:
            # The block has expired. Clear it and the failures that caused it,
            # so an old burst cannot combine with a new one to re-trigger it.
            self._entries.pop(key, None)
            return None
        return max(1, int((entry.blocked_until - now).total_seconds()))

    def _prune(self, now: datetime) -> None:
        """Drop records that can no longer affect a decision.

        Only runs once the table is over its bound, so the usual path stays a
        dictionary write. Entries still inside their window or their block are
        kept even when over the limit — evicting those is what an attacker
        wants, because it would clear the block on somebody being throttled.
        """
        if len(self._entries) <= MAX_TRACKED_KEYS:
            return

        cutoff = now - self.window
        def blocked(entry: _Entry) -> bool:
            return entry.blocked_until is not None and entry.blocked_until > now

        # First the records that can no longer affect any decision.
        for key, entry in list(self._entries.items()):
            if not blocked(entry) and not any(at > cutoff for at in entry.failures):
                del self._entries[key]

        if len(self._entries) <= MAX_TRACKED_KEYS:
            return

        # Still over, which means a flood arriving inside the window. Give up
        # the *oldest* partial counts — a caller whose count is dropped simply
        # starts again, which is the mild failure. Blocked callers are never
        # evicted: that would turn filling this table into a way of clearing
        # your own block, which is precisely the thing being defended.
        evictable = sorted(
            (k for k, e in self._entries.items() if not blocked(e)),
            key=lambda k: max(self._entries[k].failures, default=now),
        )
        for key in evictable[: max(0, len(self._entries) - PRUNE_TARGET)]:
            del self._entries[key]

    def record_failure(self, key: str, now: datetime) -> None:
        self._prune(now)
        entry = self._entries.setdefault(key, _Entry())
        cutoff = now - self.window
        entry.failures = [at for at in entry.failures if at > cutoff]
        entry.failures.append(now)
        if len(entry.failures) >= self.max_failures:
            entry.blocked_until = now + self.block_for
            entry.failures.clear()

    # Registration has no notion of a wrong answer — every attempt is the cost
    # being limited — so it counts attempts through the same machinery.
    record_attempt = record_failure

    def record_success(self, key: str) -> None:
        """A correct password clears the record — the caller proved they own it."""
        self._entries.pop(key, None)

    def clear(self) -> None:
        self._entries.clear()


def client_key(
    client_host: str | None,
    forwarded_for: str | None,
    trusted_hops: int | None = None,
) -> str:
    """The caller's address, as seen from behind a proxy.

    Render terminates TLS in front of the app, so `request.client.host` is the
    proxy for every request and would rate-limit all users as one. The real
    address comes from X-Forwarded-For.

    **Counted from the right, which is the whole point.** Each proxy appends
    the address it received the request from, so the entries on the left are
    whatever the *client* chose to send. Trusting the leftmost meant anyone
    could defeat the login limiter completely by varying a header: fifty failed
    passwords with fifty forged values produced fifty fresh allowances and no
    block at all. The rightmost entry is the one our own proxy wrote, and it is
    the only one a caller cannot forge.

    `trusted_hops` is how many proxies are in front of us — one for Render
    alone. Set it too high and you are back to believing the client.
    """
    hops = settings.trusted_proxy_hops if trusted_hops is None else trusted_hops
    if forwarded_for:
        parts = [part.strip() for part in forwarded_for.split(",") if part.strip()]
        if parts:
            return parts[max(0, len(parts) - max(1, hops))]
    return client_host or "unknown"
