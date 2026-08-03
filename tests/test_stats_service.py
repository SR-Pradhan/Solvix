from datetime import date

from app.services.stats_service import compute_streaks


def d(day: int) -> date:
    return date(2026, 8, day)


def test_no_activity():
    assert compute_streaks([], d(10)) == (0, 0)


def test_single_day_today():
    assert compute_streaks([d(10)], d(10)) == (1, 1)


def test_streak_survives_until_end_of_yesterday():
    # Solved yesterday, nothing yet today: the streak is still alive.
    assert compute_streaks([d(8), d(9)], d(10)) == (2, 2)


def test_streak_breaks_after_a_full_missed_day():
    assert compute_streaks([d(7), d(8)], d(10)) == (0, 2)


def test_longest_streak_is_kept_after_current_breaks():
    days = [d(1), d(2), d(3), d(4), d(9)]
    current, longest = compute_streaks(days, d(10))
    assert current == 1
    assert longest == 4


def test_duplicate_days_count_once():
    assert compute_streaks([d(9), d(9), d(10), d(10)], d(10)) == (2, 2)


def test_unsorted_input_is_normalised():
    assert compute_streaks([d(10), d(8), d(9)], d(10)) == (3, 3)


def test_current_streak_walks_back_only_to_the_first_gap():
    days = [d(1), d(2), d(5), d(6), d(7)]
    current, longest = compute_streaks(days, d(7))
    assert current == 3
    assert longest == 3
