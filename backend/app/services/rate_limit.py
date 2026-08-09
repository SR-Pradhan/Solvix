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

    def record_failure(self, key: str, now: datetime) -> None:
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


def client_key(client_host: str | None, forwarded_for: str | None) -> str:
    """The caller's address, as seen from behind a proxy.

    Render terminates TLS in front of the app, so `request.client.host` is the
    proxy for every request and would rate-limit all users as one. The real
    address is the first entry in X-Forwarded-For; later entries are the
    proxies it passed through.
    """
    if forwarded_for:
        first = forwarded_for.split(",")[0].strip()
        if first:
            return first
    return client_host or "unknown"
