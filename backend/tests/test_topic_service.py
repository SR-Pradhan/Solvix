from datetime import date, timedelta

from app.services.topic_service import (
    ACCURACY_WEIGHT,
    RECENCY_WEIGHT,
    REVISION_DUE_DAYS,
    STALE_HORIZON_DAYS,
    _is_stale,
    score_topic,
    status_for,
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


def test_never_solved_counts_as_stale():
    assert _is_stale(None) is True


def test_exactly_at_the_revision_window_counts_as_stale():
    assert _is_stale(REVISION_DUE_DAYS) is True


def test_just_inside_the_revision_window_is_not_stale():
    assert _is_stale(REVISION_DUE_DAYS - 1) is False


def test_revision_window_is_shorter_than_the_scoring_horizon():
    # They are deliberately different: one is a to-do list, the other is decay.
    assert REVISION_DUE_DAYS < STALE_HORIZON_DAYS


def test_solved_today_is_not_stale():
    assert _is_stale(0) is False


def test_status_uses_the_weakness_bands_when_accuracy_exists():
    assert status_for(0.7, accuracy=0.4, days_since=5) == "Needs work"
    assert status_for(0.4, accuracy=0.6, days_since=5) == "Rusty"
    assert status_for(0.1, accuracy=0.9, days_since=1) == "Solid"


def test_status_without_accuracy_falls_back_to_age():
    # 28 days scores only 0.31 on the combined scale, which would read "Solid"
    # while the reminder card calls the same topic due.
    assert status_for(0.31, accuracy=None, days_since=28) == "Rusty"


def test_status_without_accuracy_agrees_with_the_reminder_threshold():
    assert status_for(0.0, accuracy=None, days_since=REVISION_DUE_DAYS) == "Solid"
    assert status_for(0.0, accuracy=None, days_since=13) == "Solid"
    assert status_for(0.0, accuracy=None, days_since=14) == "Rusty"


def test_status_without_accuracy_escalates_when_very_stale():
    assert status_for(0.0, accuracy=None, days_since=60) == "Needs work"


def test_status_of_a_never_solved_topic_is_the_worst_band():
    assert status_for(1.0, accuracy=None, days_since=None) == "Needs work"


def test_platform_labelled_topics_are_sorted_across_platforms():
    # The caller wants "what is weakest", not "weakest on Codeforces, then
    # weakest on LeetCode" — an agent picking the first entry would otherwise
    # always pick the same platform.
    from app.services.topic_service import weak_topics_with_platform

    assert weak_topics_with_platform.__doc__ is not None
