from datetime import date, timedelta

from app.services.revision_schedule import (
    CLEAN,
    INTERVALS,
    STRUGGLED,
    UNSEEN,
    classify_attempts,
    first_due,
    next_schedule,
    outcome_for_platform,
    schedule_for_existing,
)

TODAY = date(2026, 8, 10)


def test_first_revisit_is_three_days_after_solving():
    assert first_due(TODAY) == TODAY + timedelta(days=3)


def test_gaps_widen_after_a_clean_recall():
    step, due = 0, None
    seen = []
    for _ in range(len(INTERVALS) - 1):
        step, due = next_schedule(step, CLEAN, TODAY)
        seen.append((due - TODAY).days)
    assert seen == list(INTERVALS[1:])


def test_a_problem_retires_after_the_last_interval():
    # Recalled cleanly all the way through: it is learned, and continuing to
    # remind about it is noise.
    assert next_schedule(len(INTERVALS) - 1, CLEAN, TODAY) is None


def test_struggling_goes_back_to_the_start():
    # Pushing a failed recall out to a longer gap guarantees it fails again.
    step, due = next_schedule(3, STRUGGLED, TODAY)
    assert step == 0
    assert due == TODAY + timedelta(days=INTERVALS[0])


def test_not_revisiting_holds_the_step():
    # Nothing was learned either way, so the gap neither widens nor resets.
    step, due = next_schedule(2, UNSEEN, TODAY)
    assert step == 2
    assert due == TODAY + timedelta(days=INTERVALS[2])


def test_unseen_at_the_final_step_keeps_asking():
    # It must not fall off the end unrecalled: retirement is earned by a clean
    # recall, not by being ignored long enough.
    step, due = next_schedule(len(INTERVALS) - 1, UNSEEN, TODAY)
    assert step == len(INTERVALS) - 1
    assert due == TODAY + timedelta(days=INTERVALS[-1])


def test_no_submissions_means_unseen():
    assert classify_attempts([]) == UNSEEN


def test_passing_first_try_is_clean():
    assert classify_attempts(["OK"]) == CLEAN


def test_failing_before_passing_is_struggling():
    # Getting there eventually is not the same as recalling it.
    assert classify_attempts(["WRONG_ANSWER", "OK"]) == STRUGGLED


def test_platforms_without_failure_data_are_never_graded():
    # LeetCode records passes only, so "no failures found" there means "no
    # failures are recordable" — grading it would invent a signal.
    assert outcome_for_platform("leetcode", [], can_see_failures=False) == CLEAN
    assert (
        outcome_for_platform("leetcode", ["WRONG_ANSWER"], can_see_failures=False)
        == CLEAN
    )


def test_platforms_with_failure_data_are_graded():
    assert (
        outcome_for_platform("codeforces", ["WRONG_ANSWER", "OK"], can_see_failures=True)
        == STRUGGLED
    )


def test_older_problem_slots_in_at_the_next_future_interval():
    # Solved 10 days ago: the 3 and 7 day rungs have passed unobserved, so it
    # picks up at 14.
    solved = TODAY - timedelta(days=10)
    step, due = schedule_for_existing(solved, TODAY)
    assert INTERVALS[step] == 14
    assert due == solved + timedelta(days=14)


def test_a_brand_new_solve_starts_at_the_first_rung():
    step, due = schedule_for_existing(TODAY, TODAY)
    assert step == 0
    assert due == TODAY + timedelta(days=3)


def test_a_problem_older_than_the_whole_ladder_is_retired():
    # Either learned or long forgotten — neither is a revision reminder's job,
    # and importing years of history should not produce years of backlog.
    assert schedule_for_existing(TODAY - timedelta(days=200), TODAY) is None
