from app.services.reminder_service import (
    MAX_PER_RUN,
    _reminder_url,
    STALE_THRESHOLD_DAYS,
    WEAK_THRESHOLD,
    describe_problem,
    describe_topic,
    select_reminders,
    topic_is_due,
)


def topic(days=30, weakness=0.7, accuracy=0.8):
    return {
        "tag": "dp",
        "days_since_last_solve": days,
        "weakness": weakness,
        "accuracy": accuracy,
    }


def item(kind="problem", n=0, platform="codeforces"):
    return {
        "kind": kind,
        "platform": platform,
        "subject": f"{kind}{n}",
        "title": f"{kind}{n}",
        "reason": "",
    }


def test_weak_and_stale_topic_is_due():
    assert topic_is_due(topic(days=STALE_THRESHOLD_DAYS, weakness=WEAK_THRESHOLD))


def test_stale_but_strong_topic_is_not_due():
    # Untouched for a month, but you are good at it — not worth a slot.
    assert not topic_is_due(topic(days=90, weakness=WEAK_THRESHOLD - 0.01))


def test_weak_but_fresh_topic_is_not_due():
    # Practised yesterday; nagging about it today is noise.
    assert not topic_is_due(topic(days=1, weakness=0.9))


def test_never_solved_topic_counts_as_stale():
    assert topic_is_due(topic(days=None, weakness=0.9))


def test_just_inside_the_threshold_is_not_due():
    assert not topic_is_due(topic(days=STALE_THRESHOLD_DAYS - 1, weakness=0.9))


def test_reminders_are_capped():
    problems = [item("problem", i) for i in range(10)]
    topics = [item("topic", i) for i in range(10)]
    assert len(select_reminders(problems, topics)) == MAX_PER_RUN


def test_problems_win_the_cap_over_topics():
    # A problem's revisit window is a specific few days; a stale topic is
    # equally stale tomorrow, so problems come first.
    problems = [item("problem", i) for i in range(MAX_PER_RUN)]
    topics = [item("topic", i) for i in range(5)]
    selected = select_reminders(problems, topics)
    assert all(r["kind"] == "problem" for r in selected)


def test_topics_fill_the_remaining_slots():
    selected = select_reminders([item("problem", 0)], [item("topic", i) for i in range(9)])
    assert len(selected) == MAX_PER_RUN
    assert selected[0]["kind"] == "problem"
    assert selected[1]["kind"] == "topic"


def test_no_data_yields_no_reminders():
    assert select_reminders([], []) == []


def test_problem_reason_reads_naturally_at_one_day():
    assert describe_problem("Two Sum", 1) == "solved yesterday"


def test_problem_reason_pluralises():
    assert describe_problem("Two Sum", 3) == "solved 3 days ago"


def test_topic_reason_mentions_a_bad_pass_rate():
    assert "30% of attempts pass" in describe_topic(30, 0.3)


def test_topic_reason_omits_pass_rate_when_it_is_healthy():
    assert "attempts pass" not in describe_topic(30, 0.9)


def test_topic_reason_handles_never_solved():
    assert describe_topic(None, None).startswith("never solved")


def test_topic_reason_scales_units_with_age():
    assert "weeks" in describe_topic(21, 0.9)
    assert "months" in describe_topic(120, 0.9)
    assert "over a year" in describe_topic(400, 0.9)


def test_stale_topic_without_a_pass_rate_is_due_on_staleness_alone():
    # LeetCode records no failures, so weakness is recency restated. Requiring
    # the weakness bar too would silently raise the 14-day threshold to ~32.
    no_accuracy = topic(days=STALE_THRESHOLD_DAYS, weakness=0.15, accuracy=None)
    assert topic_is_due(no_accuracy)


def test_fresh_topic_without_a_pass_rate_is_still_not_due():
    assert not topic_is_due(topic(days=2, weakness=0.9, accuracy=None))



def test_every_reminder_carries_the_platform_it_came_from():
    # Without this the dashboard cannot filter: a Codeforces-only view would
    # still be shown LeetCode topics.
    selected = select_reminders(
        [item("problem", 0, "leetcode")], [item("topic", 0, "codeforces")]
    )
    assert [r["platform"] for r in selected] == ["leetcode", "codeforces"]


def test_problem_reminder_links_to_leetcode():
    # The subject carries "platform:id", so the link is derived rather than
    # stored — a second copy could only drift from the id it came from.
    assert (
        _reminder_url("problem", "leetcode", "leetcode:0162-find-peak-element")
        == "https://leetcode.com/problems/find-peak-element/"
    )


def test_problem_reminder_links_to_codeforces():
    assert (
        _reminder_url("problem", "codeforces", "codeforces:2238A")
        == "https://codeforces.com/problemset/problem/2238/A"
    )


def test_topic_reminders_have_no_link():
    # A tag is not a page anywhere.
    assert _reminder_url("topic", "leetcode", "Math") is None


def test_a_subject_without_an_id_has_no_link():
    assert _reminder_url("problem", "leetcode", "leetcode:") is None
