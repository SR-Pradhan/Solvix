from datetime import date

from app.services.report_service import (
    HIGHLIGHT_COUNT,
    MIN_SOLVED_FOR_STRENGTH,
    pick_highlights,
    week_start_for,
)


def topic(tag, solved=10, accuracy=0.8):
    return {"tag": tag, "solved": solved, "accuracy": accuracy}


def test_week_start_of_a_monday_is_itself():
    monday = date(2026, 8, 3)
    assert week_start_for(monday) == monday


def test_week_start_walks_back_to_monday():
    assert week_start_for(date(2026, 8, 6)) == date(2026, 8, 3)


def test_sunday_belongs_to_the_week_that_started_six_days_earlier():
    # Sunday is the end of its week, not the start of the next one.
    assert week_start_for(date(2026, 8, 9)) == date(2026, 8, 3)


def test_week_start_crosses_a_month_boundary():
    assert week_start_for(date(2026, 9, 2)) == date(2026, 8, 31)


def test_weakest_comes_from_the_front_of_the_list():
    topics = [topic(f"tag{i}") for i in range(10)]
    weakest, _ = pick_highlights(topics)
    assert [t["tag"] for t in weakest] == ["tag0", "tag1", "tag2"]


def test_strongest_comes_from_the_back_strongest_first():
    topics = [topic(f"tag{i}") for i in range(10)]
    _, strongest = pick_highlights(topics)
    assert [t["tag"] for t in strongest] == ["tag9", "tag8", "tag7"]


def test_low_volume_topics_cannot_be_strengths():
    # One lucky solve should not qualify as a strength.
    topics = [topic("dp", solved=20), topic("fluke", solved=MIN_SOLVED_FOR_STRENGTH - 1)]
    _, strongest = pick_highlights(topics)
    assert "fluke" not in [t["tag"] for t in strongest]


def test_a_topic_is_never_both_weakest_and_strongest():
    topics = [topic("only"), topic("second")]
    weakest, strongest = pick_highlights(topics)
    assert not set(t["tag"] for t in weakest) & set(t["tag"] for t in strongest)


def test_empty_topic_list_yields_no_highlights():
    assert pick_highlights([]) == ([], [])


def test_highlights_are_capped():
    topics = [topic(f"tag{i}") for i in range(50)]
    weakest, strongest = pick_highlights(topics)
    assert len(weakest) == HIGHLIGHT_COUNT
    assert len(strongest) <= HIGHLIGHT_COUNT
