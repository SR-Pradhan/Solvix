from datetime import date, datetime, timedelta, timezone

from app.core.clock import ZONE, day_of, local_day, today


def utc(y, m, d, hh, mm=0):
    return datetime(y, m, d, hh, mm, tzinfo=timezone.utc)


def test_the_zone_is_the_one_the_practising_happens_in():
    assert str(ZONE) == "Asia/Kolkata"


def test_an_evening_solve_stays_on_its_own_day():
    # 23:00 IST on the 24th is 17:30 UTC the same day — both agree.
    assert day_of(utc(2026, 8, 24, 17, 30)) == date(2026, 8, 24)


def test_a_late_night_solve_belongs_to_the_day_it_felt_like():
    """The bug, stated as a test.

    02:00 IST on the 25th is 20:30 UTC on the 24th. Measuring in UTC filed it
    under the 24th — breaking a streak that was never broken.
    """
    assert day_of(utc(2026, 8, 24, 20, 30)) == date(2026, 8, 25)


def test_the_boundary_sits_at_midnight_local_not_midnight_utc():
    # 18:29 UTC is 23:59 IST — still the 24th.
    assert day_of(utc(2026, 8, 24, 18, 29)) == date(2026, 8, 24)
    # One minute later is 00:00 IST — the 25th.
    assert day_of(utc(2026, 8, 24, 18, 30)) == date(2026, 8, 25)


def test_the_old_utc_boundary_is_no_longer_a_boundary():
    # Midnight UTC falls at 05:30 IST, mid-morning. Nothing should change here.
    before = day_of(utc(2026, 8, 24, 23, 59))
    after = day_of(utc(2026, 8, 25, 0, 1))
    assert before == after == date(2026, 8, 25)


def test_a_naive_instant_is_read_as_utc():
    """Every timestamp column stores naive UTC, so this is the common case."""
    assert day_of(datetime(2026, 8, 24, 20, 30)) == date(2026, 8, 25)


def test_today_is_a_real_date():
    assert isinstance(today(), date)


def test_the_sql_labels_the_column_utc_before_reading_it_locally():
    """The SQL half has to agree with the Python half.

    Verified against a real Postgres separately; this pins the shape so the
    two conversions cannot drift apart silently.
    """
    from sqlalchemy import DateTime, column
    from sqlalchemy.dialects import postgresql

    rendered = str(
        local_day(column("solved_at", DateTime)).compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )
    assert rendered == "date(timezone('Asia/Kolkata', timezone('UTC', solved_at)))"


def test_a_local_day_starts_before_midnight_utc():
    """The mirror of day_of, and the one that is easy to get wrong.

    `datetime.combine(day, min.time())` gives midnight UTC, which is 05:30 in
    the morning locally — a window meant to cover the whole day would skip its
    first five and a half hours.
    """
    from app.core.clock import utc_start_of

    # Midnight on the 25th, IST, is 18:30 UTC on the 24th.
    assert utc_start_of(date(2026, 8, 25)) == datetime(2026, 8, 24, 18, 30)


def test_the_two_conversions_are_inverses():
    from app.core.clock import utc_start_of

    for day in (date(2026, 1, 1), date(2026, 8, 25), date(2026, 12, 31)):
        # The first instant of a local day must read back as that same day.
        assert day_of(utc_start_of(day)) == day
        # And the instant before it must belong to the day before.
        assert day_of(utc_start_of(day) - timedelta(seconds=1)) == day - timedelta(days=1)
