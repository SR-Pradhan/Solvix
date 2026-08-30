"""What day it is, and which day a submission belongs to.

Every calendar day in Solvix — a streak, "this week", whether a revision is
due — has to be measured in the timezone the practising actually happened in.
The platforms report timestamps in UTC and the database stores them that way,
which is right for storage and wrong for asking "did I practise today".

**The bug this exists to prevent.** Computing days in UTC puts the boundary at
05:30 IST. Anything solved between midnight and half past five in the morning
is filed under the previous day, which silently breaks a streak that was never
broken and moves problems in and out of "this week". `date.today()` is worse
still: it follows the *server's* zone, so the same code gave different answers
on a laptop in India and on a server in Oregon.

Both halves have to move together. A correct "today" over UTC-bucketed
submissions is still wrong — the comparison is just wrong in a new place.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func

from app.core.config import settings

ZONE = ZoneInfo(settings.timezone)


def day_of(moment: datetime) -> date:
    """The local calendar day a UTC instant falls on.

    Split out from `today` so the boundary is a pure function over an instant
    and can be tested at exactly the hours that used to be wrong, rather than
    only when the suite happens to run at the right time of night.

    A naive instant is taken to be UTC, which is how every timestamp column in
    the database is stored.
    """
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(ZONE).date()


def today() -> date:
    """The current date where the user is, not where the server is."""
    return day_of(datetime.now(timezone.utc))


def now() -> datetime:
    """The current local wall-clock time, without a timezone attached.

    Naive to match the columns, which store naive UTC. Only use this for
    comparing against a local calendar day — anything being *stored* should
    stay in UTC.
    """
    return datetime.now(ZONE).replace(tzinfo=None)


def utc_start_of(day: date) -> datetime:
    """The instant a local calendar day begins, as naive UTC.

    The mirror of `day_of`, and needed wherever a local date is compared
    against a stored timestamp. `datetime.combine(day, min.time())` looks like
    the obvious thing and is wrong: it produces midnight *UTC*, which in this
    zone is 05:30 in the morning, so a window meant to start at midnight
    silently skips the first five and a half hours of the day — exactly the
    late-night practice the timezone fix was about.
    """
    local_midnight = datetime.combine(day, datetime.min.time(), tzinfo=ZONE)
    return local_midnight.astimezone(timezone.utc).replace(tzinfo=None)


def local_day(column):
    """SQL for the calendar day a stored timestamp falls on, locally.

    `solved_at` is naive UTC, so it is first labelled as UTC and then read in
    the app's zone. Going through the zone database rather than adding a fixed
    offset means a zone with daylight saving stays correct; India has none, but
    the offset would be the only thing to fix if this ever moved.
    """
    return func.date(func.timezone(settings.timezone, func.timezone("UTC", column)))
