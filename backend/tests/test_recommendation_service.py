from collections import Counter

from app.services.recommendation_service import (
    MIN_PROBLEMS_PER_TAG,
    MIN_SOLVED_FOR_SIGNAL,
    build_shortfall_note,
    _target_rating,
    _weak_tags,
)


def problemset(**tag_counts: int) -> list[dict]:
    """Build a fake problemset where each tag appears the requested number of times."""
    problems = []
    for tag, count in tag_counts.items():
        problems.extend({"tags": [tag]} for _ in range(count))
    return problems


def test_untouched_common_tag_ranks_above_a_practised_one():
    ps = problemset(dp=200, greedy=200)
    weak = _weak_tags(Counter({"greedy": 100}), total_solved=100, problemset=ps, top_n=5)

    assert [t["tag"] for t in weak] == ["dp"]
    assert weak[0]["solved_count"] == 0


def test_rare_tags_are_ignored():
    ps = problemset(dp=200, chinese_remainder_theorem=MIN_PROBLEMS_PER_TAG - 1)
    weak = _weak_tags(Counter(), total_solved=50, problemset=ps, top_n=5)

    assert [t["tag"] for t in weak] == ["dp"]


def test_over_practised_tags_are_excluded():
    # 100% of solves are dp, but dp is only half the problemset — no deficit.
    ps = problemset(dp=100, math=100)
    weak = _weak_tags(Counter({"dp": 40}), total_solved=40, problemset=ps, top_n=5)

    assert "dp" not in [t["tag"] for t in weak]
    assert "math" in [t["tag"] for t in weak]


def test_ordering_is_by_deficit_then_name():
    ps = problemset(dp=500, math=100, greedy=100)
    weak = _weak_tags(Counter(), total_solved=10, problemset=ps, top_n=5)

    assert weak[0]["tag"] == "dp"
    assert [t["tag"] for t in weak[1:]] == ["greedy", "math"]


def test_top_n_is_respected():
    ps = problemset(a=100, b=100, c=100, d=100)
    assert len(_weak_tags(Counter(), 10, ps, top_n=2)) == 2


def test_target_rating_defaults_without_history():
    assert _target_rating([]) == 1200


def test_target_rating_follows_the_stretch_not_the_average():
    # Mostly easy problems with a few hard ones: the target should sit near the
    # hard end, not be dragged down to the average.
    ratings = [800] * 30 + [1900, 2000, 2100, 2200]
    assert _target_rating(ratings) >= 1900


def test_target_rating_rounds_to_hundreds():
    assert _target_rating([1437, 1462, 1488]) % 100 == 0


def test_shortfall_note_names_codeforces_not_problems_in_general():
    note = build_shortfall_note(1)
    assert "Codeforces" in note
    assert str(MIN_SOLVED_FOR_SIGNAL) in note


def test_shortfall_note_reports_the_actual_count():
    assert "solved 1 so far" in build_shortfall_note(1)
    assert "solved 7 so far" in build_shortfall_note(7)


def test_shortfall_note_reads_naturally_at_zero():
    note = build_shortfall_note(0)
    assert "have not solved any yet" in note
    assert "solved 0" not in note
