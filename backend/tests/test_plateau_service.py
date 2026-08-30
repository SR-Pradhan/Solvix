from app.services.plateau_service import (
    COASTING,
    MIN_AT_LEVEL,
    MIN_RECENT,
    PLATEAUED,
    STRETCHING,
    UNKNOWN,
    assess,
    label_for,
    tier_of,
    top_tier,
    working_level,
)

LC = "leetcode"
CF = "codeforces"
EASY, MEDIUM, HARD = 0, 1, 2


def test_leetcode_tiers_are_ordered_by_difficulty():
    assert tier_of(LC, "Easy", None) < tier_of(LC, "Medium", None)
    assert tier_of(LC, "Medium", None) < tier_of(LC, "Hard", None)


def test_an_unknown_difficulty_has_no_tier():
    # Left out rather than guessed at: an unrated Codeforces problem and a
    # LeetCode row with no difficulty are both "the platform did not say".
    assert tier_of(LC, None, None) is None
    assert tier_of(LC, "Insane", None) is None
    assert tier_of(CF, None, None) is None


def test_codeforces_ratings_bucket_into_comparable_steps():
    # Two problems ten points apart are the same difficulty in practice.
    assert tier_of(CF, None, 1600) == tier_of(CF, None, 1610)
    assert tier_of(CF, None, 1600) < tier_of(CF, None, 1800)


def test_working_level_is_the_hardest_tier_with_enough_behind_it():
    counts = {EASY: 40, MEDIUM: MIN_AT_LEVEL, HARD: MIN_AT_LEVEL - 1}
    # Hard falls short, so Medium is the demonstrated level.
    assert working_level(counts) == MEDIUM


def test_one_lucky_hard_problem_does_not_become_your_level():
    assert working_level({EASY: 50, HARD: 1}) == EASY


def test_no_tier_with_enough_solves_has_no_working_level():
    assert working_level({EASY: 2, MEDIUM: 1}) is None
    assert working_level({}) is None


def test_practice_above_your_level_is_stretching():
    recent = [MEDIUM] * 8 + [HARD] * 2
    assert assess(recent, MEDIUM, LC)["status"] == STRETCHING


def test_practice_stuck_at_your_level_has_plateaued():
    """Comfortable, and going nowhere — the case this feature exists for."""
    assert assess([MEDIUM] * 20, MEDIUM, LC)["status"] == PLATEAUED


def test_mostly_practice_below_your_level_is_coasting():
    recent = [EASY] * 15 + [MEDIUM] * 5
    assert assess(recent, MEDIUM, LC)["status"] == COASTING


def test_coasting_and_plateauing_are_told_apart():
    """They need different advice, which is why they are not one label."""
    at_level = assess([MEDIUM] * 20, MEDIUM, LC)["status"]
    below_level = assess([EASY] * 20, MEDIUM, LC)["status"]
    assert at_level != below_level


def test_too_little_recent_practice_is_not_a_verdict():
    # Telling somebody who solved two problems that they have plateaued is not
    # an observation.
    assert assess([MEDIUM] * (MIN_RECENT - 1), MEDIUM, LC)["status"] == UNKNOWN


def test_the_counts_add_up_to_the_window():
    result = assess([EASY, EASY, MEDIUM, MEDIUM, MEDIUM, HARD], MEDIUM, LC)
    assert result["above"] + result["at"] + result["below"] == result["recent_solved"]
    assert (result["above"], result["at"], result["below"]) == (1, 3, 2)


def test_the_next_level_up_is_named():
    assert assess([MEDIUM] * 10, MEDIUM, LC)["next_level"] == "Hard"
    assert assess([EASY] * 10, EASY, LC)["working_level"] == "Easy"


def test_somebody_at_the_top_of_the_ladder_is_not_scolded():
    """There is nothing above Hard, so "you never go higher" is not a finding."""
    top = top_tier(LC)
    assert assess([top] * 20, top, LC)["status"] == STRETCHING
    assert assess([top] * 20, top, LC)["next_level"] is None


def test_codeforces_labels_read_as_ratings():
    assert label_for(CF, 1600 // 200) == "1600+"
    assert label_for(LC, MEDIUM) == "Medium"
