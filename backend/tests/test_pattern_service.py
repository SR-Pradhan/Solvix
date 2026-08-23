from app.services.pattern_service import (
    MIN_DROP,
    MIN_PAIR_ATTEMPTS,
    find_patterns,
    interaction_drop,
    severity_for,
)


def solo(**tags):
    """Standalone figures for each tag, at a volume that clears the baseline."""
    return {
        tag: {"attempts": 40, "accuracy": accuracy} for tag, accuracy in tags.items()
    }


def pair(a, b, accuracy, attempts=MIN_PAIR_ATTEMPTS, solved=5):
    return {
        "tags": [a, b],
        "attempts": attempts,
        "solved": solved,
        "accuracy": accuracy,
    }


def test_drop_is_measured_against_the_weaker_half():
    # 0.55 is the weaker parent, so a pair at 0.13 has dropped 0.42 — not the
    # 0.66 that comparing against the stronger parent would report.
    assert interaction_drop(0.13, 0.79, 0.55) == 0.42


def test_a_pair_matching_its_weaker_half_has_not_dropped():
    assert interaction_drop(0.55, 0.79, 0.55) == 0.0


def test_a_pair_better_than_its_parts_drops_negatively():
    assert interaction_drop(0.90, 0.70, 0.80) < 0


def test_inherited_weakness_is_not_reported():
    """The case the whole feature exists to exclude.

    `dp` is bad on its own, and the pair is exactly as bad. Ranking by raw
    accuracy would put this at the top of the list; it belongs nowhere on it,
    because it says nothing that the weak-topics card did not already say.
    """
    found = find_patterns(
        [pair("dp", "trees", 0.30)], solo(dp=0.30, trees=0.85)
    )
    assert found["patterns"] == []


def test_a_genuine_interaction_is_reported():
    found = find_patterns(
        [pair("bitmasks", "implementation", 0.34)],
        solo(bitmasks=0.69, implementation=0.79),
    )
    (pattern,) = found["patterns"]
    assert pattern["tags"] == ["bitmasks", "implementation"]
    assert pattern["drop"] == 0.35
    assert pattern["expected"] == 0.69


def test_a_pair_that_outperforms_its_parts_is_not_reported():
    found = find_patterns(
        [pair("math", "number theory", 0.95)],
        solo(**{"math": 0.70, "number theory": 0.75}),
    )
    assert found["patterns"] == []


def test_a_small_gap_is_treated_as_noise():
    found = find_patterns(
        [pair("greedy", "sortings", 0.70 - (MIN_DROP / 2))],
        solo(greedy=0.70, sortings=0.80),
    )
    assert found["patterns"] == []


def test_thin_pairs_are_not_judged():
    found = find_patterns(
        [pair("dp", "games", 0.10, attempts=MIN_PAIR_ATTEMPTS - 1)],
        solo(dp=0.80, games=0.80),
    )
    assert found["patterns"] == []
    # Not merely excluded from the list — never considered, so it cannot be
    # reported as a pair that was weighed and passed.
    assert found["pairs_considered"] == 0


def test_a_pair_whose_parent_has_no_baseline_is_skipped():
    found = find_patterns([pair("dp", "flows", 0.10)], solo(dp=0.80))
    assert found["patterns"] == []
    assert found["pairs_considered"] == 0


def test_biggest_drop_leads():
    found = find_patterns(
        [
            pair("a", "b", 0.50),  # drop 0.20
            pair("c", "d", 0.20),  # drop 0.50
        ],
        solo(a=0.70, b=0.90, c=0.70, d=0.90),
    )
    assert [p["tags"] for p in found["patterns"]] == [["c", "d"], ["a", "b"]]


def test_equal_drops_break_on_evidence():
    found = find_patterns(
        [
            pair("a", "b", 0.50, attempts=20),
            pair("c", "d", 0.50, attempts=90),
        ],
        solo(a=0.70, b=0.90, c=0.70, d=0.90),
    )
    assert [p["attempts"] for p in found["patterns"]] == [90, 20]


def test_limit_shortens_the_list_without_changing_the_total():
    pairs = [pair(tag, "x", 0.20) for tag in ("a", "b", "c")]
    found = find_patterns(pairs, solo(a=0.80, b=0.80, c=0.80, x=0.80), limit=2)
    assert len(found["patterns"]) == 2
    # The count is over everything found, so it does not move when the caller
    # asks for a shorter list.
    assert found["total_found"] == 3


def test_no_baselines_at_all_returns_an_empty_result():
    """An account with only LeetCode data, which records no failures."""
    found = find_patterns([], {})
    assert found["patterns"] == []
    assert found["total_found"] == 0


def test_severity_bands_are_ordered():
    assert severity_for(0.45) == "Breaks down"
    assert severity_for(0.25) == "Struggles"
    assert severity_for(0.16) == "Slips"


def test_a_band_edge_is_judged_on_the_figure_shown():
    # Renders as 30%, so it should read as the 0.30 band rather than the one
    # below it.
    assert severity_for(0.2996) == "Breaks down"
