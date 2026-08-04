from datetime import date, timedelta

from app.services.topic_service import (
    ACCURACY_WEIGHT,
    RECENCY_WEIGHT,
    STALE_HORIZON_DAYS,
    score_topic,
)

TODAY = date(2026, 8, 4)


def weakness(attempts, accepted, last_solved):
    return score_topic(attempts, accepted, last_solved, TODAY)[0]


def test_perfect_and_current_is_the_strongest_possible():
    assert weakness(10, 10, TODAY) == 0.0


def test_never_solved_is_the_weakest_possible():
    # No accepted submission at all: zero accuracy and maximum staleness.
    assert weakness(10, 0, None) == round(ACCURACY_WEIGHT + RECENCY_WEIGHT, 4)


def test_accuracy_is_accepted_over_attempts():
    _, accuracy, _ = score_topic(8, 2, TODAY, TODAY)
    assert accuracy == 0.25


def test_low_accuracy_scores_weaker_than_high_accuracy():
    assert weakness(10, 2, TODAY) > weakness(10, 9, TODAY)


def test_stale_scores_weaker_than_recent_at_equal_accuracy():
    recent = weakness(10, 8, TODAY)
    stale = weakness(10, 8, date(2026, 5, 1))
    assert stale > recent


def test_staleness_stops_growing_past_the_horizon():
    horizon = TODAY - timedelta(days=STALE_HORIZON_DAYS)
    long_past = TODAY - timedelta(days=STALE_HORIZON_DAYS * 20)
    # Both saturate, so twenty times the horizon adds nothing over the horizon.
    assert weakness(10, 8, horizon) == weakness(10, 8, long_past)


def test_staleness_still_grows_inside_the_horizon():
    half = TODAY - timedelta(days=STALE_HORIZON_DAYS // 2)
    horizon = TODAY - timedelta(days=STALE_HORIZON_DAYS)
    assert weakness(10, 8, half) < weakness(10, 8, horizon)


def test_days_since_last_solve_is_reported():
    _, _, days = score_topic(5, 5, date(2026, 7, 30), TODAY)
    assert days == 5


def test_future_dates_do_not_produce_negative_staleness():
    # Clock skew between the API and the database should not invent a bonus.
    _, _, days = score_topic(5, 5, date(2026, 9, 1), TODAY)
    assert days == 0


def test_accuracy_outweighs_recency():
    # Bad at it but did it today, vs good at it but long ago.
    inaccurate_but_fresh = weakness(10, 0, TODAY)
    accurate_but_stale = weakness(10, 10, date(2020, 1, 1))
    assert inaccurate_but_fresh > accurate_but_stale


def test_zero_attempts_does_not_divide_by_zero():
    assert weakness(0, 0, None) == round(ACCURACY_WEIGHT + RECENCY_WEIGHT, 4)
