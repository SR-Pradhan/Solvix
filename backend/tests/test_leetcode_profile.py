from datetime import datetime, timedelta

import pytest

from app.clients.leetcode_client import LeetCodeUserNotFound, parse_profile
from app.services import leetcode_profile_service as profile_service
from app.services.leetcode_profile_service import coverage

NOW = datetime(2026, 8, 15, 12, 0, 0)


def profile_response(**overrides):
    body = {
        "matchedUser": {
            "submitStatsGlobal": {
                "acSubmissionNum": [
                    {"difficulty": "All", "count": 113},
                    {"difficulty": "Easy", "count": 67},
                    {"difficulty": "Medium", "count": 46},
                    {"difficulty": "Hard", "count": 0},
                ]
            },
            "tagProblemCounts": {
                "fundamental": [{"tagName": "Array", "problemsSolved": 63}],
                "intermediate": [{"tagName": "Hash Table", "problemsSolved": 26}],
                "advanced": [{"tagName": "Dynamic Programming", "problemsSolved": 6}],
            },
        }
    }
    body.update(overrides)
    return body


def test_profile_totals_are_flattened():
    parsed = parse_profile(profile_response())
    assert parsed["total_solved"] == 113
    assert parsed["easy"] == 67
    assert parsed["medium"] == 46
    assert parsed["hard"] == 0


def test_profile_merges_all_three_tag_buckets():
    tags = {t["tag"] for t in parse_profile(profile_response())["tags"]}
    assert tags == {"Array", "Hash Table", "Dynamic Programming"}


def test_profile_tags_are_sorted_by_volume():
    tags = parse_profile(profile_response())["tags"]
    assert [t["solved"] for t in tags] == [63, 26, 6]


def test_profile_drops_tags_with_no_solves():
    body = profile_response()
    body["matchedUser"]["tagProblemCounts"]["advanced"] = [
        {"tagName": "Never Touched", "problemsSolved": 0}
    ]
    tags = {t["tag"] for t in parse_profile(body)["tags"]}
    assert "Never Touched" not in tags


def test_unknown_username_raises_a_distinct_error():
    # A typo is the caller's mistake, not a LeetCode outage — the API returns
    # a 200 with a null user rather than an error status.
    with pytest.raises(LeetCodeUserNotFound):
        parse_profile({"matchedUser": None})


def test_profile_survives_missing_tag_buckets():
    body = profile_response()
    del body["matchedUser"]["tagProblemCounts"]
    assert parse_profile(body)["tags"] == []


def test_coverage_reports_how_much_history_is_visible():
    assert coverage(113, 48) == {"tracked": 48, "missing": 65, "percent": 42}


def test_coverage_is_complete_when_nothing_is_missing():
    assert coverage(48, 48) == {"tracked": 48, "missing": 0, "percent": 100}


def test_coverage_never_reports_negative_missing():
    # The repo can briefly hold more than the profile reports; that is not
    # "-3 missing".
    assert coverage(45, 48)["missing"] == 0


def test_coverage_handles_an_empty_profile():
    assert coverage(0, 0) == {"tracked": 0, "missing": 0, "percent": 0}


def test_a_missing_snapshot_is_stale():
    assert profile_service.is_stale(None, NOW)


def test_a_fresh_snapshot_is_not_refetched():
    # Every refresh is a call to somebody else's service; the number only moves
    # a few times a day.
    assert not profile_service.is_stale(NOW - timedelta(hours=1), NOW)


def test_a_snapshot_past_the_window_is_stale():
    assert profile_service.is_stale(NOW - timedelta(hours=13), NOW)


def test_the_boundary_counts_as_stale():
    assert profile_service.is_stale(NOW - profile_service.SNAPSHOT_MAX_AGE, NOW)


def test_coverage_cannot_exceed_the_whole():
    # The profile total is up to twelve hours stale, so the repo import can be
    # ahead of it. "120% of your total" undermines every other number shown.
    assert coverage(100, 120)["percent"] == 100
    assert coverage(100, 120)["missing"] == 0


def test_coverage_with_nothing_recorded():
    assert coverage(0, 0) == {"tracked": 0, "missing": 0, "percent": 0}
