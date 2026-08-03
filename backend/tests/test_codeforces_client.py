from datetime import datetime

import pytest

from app.clients.codeforces_client import to_submission_row


def raw(**overrides):
    payload = {
        "creationTimeSeconds": 1735689600,  # 2025-01-01 00:00:00 UTC
        "verdict": "OK",
        "problem": {
            "contestId": 1850,
            "index": "A",
            "name": "To My Critics",
            "tags": ["greedy", "math"],
            "rating": 800,
        },
    }
    payload.update(overrides)
    return payload


def test_maps_a_solved_submission():
    row = to_submission_row(raw())

    assert row["external_problem_id"] == "1850A"
    assert row["problem_name"] == "To My Critics"
    assert row["tags"] == ["greedy", "math"]
    assert row["difficulty_rating"] == 800
    assert row["verdict"] == "OK"
    assert row["solved_at"] == datetime(2025, 1, 1, 0, 0, 0)


def test_solved_at_is_naive_utc():
    # The column is a naive DateTime, so a tz-aware value would fail to insert.
    assert to_submission_row(raw())["solved_at"].tzinfo is None


def test_unrated_problem_has_no_difficulty():
    problem = dict(raw()["problem"])
    del problem["rating"]

    assert to_submission_row(raw(problem=problem))["difficulty_rating"] is None


def test_problem_without_tags_becomes_empty_list():
    problem = dict(raw()["problem"])
    del problem["tags"]

    assert to_submission_row(raw(problem=problem))["tags"] == []


def test_missing_verdict_falls_back_to_unknown():
    payload = raw()
    del payload["verdict"]

    assert to_submission_row(payload)["verdict"] == "UNKNOWN"


@pytest.mark.parametrize("verdict", ["WRONG_ANSWER", "TIME_LIMIT_EXCEEDED", "COMPILATION_ERROR"])
def test_failed_attempts_are_still_mapped(verdict):
    # Failures are stored too; the stats layer is what filters on OK.
    assert to_submission_row(raw(verdict=verdict))["verdict"] == verdict
