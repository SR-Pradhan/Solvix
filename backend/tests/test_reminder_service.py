from app.clients.leetcode_client import LeetCodeError
from app.services import reminder_service
from app.services.reminder_service import (
    MAX_PER_RUN,
    TOPIC_SLOTS,
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


def test_problems_come_first_but_cannot_crowd_topics_out():
    # A problem's revisit window is a specific few days; a stale topic is
    # equally stale tomorrow, so problems lead. But once the spacing ladder
    # matured, enough problems fell due every morning to fill the cap outright
    # and topics stopped appearing at all — so a share is held back for them.
    problems = [item("problem", i) for i in range(MAX_PER_RUN)]
    topics = [item("topic", i) for i in range(5)]
    selected = select_reminders(problems, topics)

    kinds = [r["kind"] for r in selected]
    assert len(selected) == MAX_PER_RUN
    assert kinds == ["problem"] * (MAX_PER_RUN - TOPIC_SLOTS) + ["topic"] * TOPIC_SLOTS


def test_the_reserved_slots_are_not_wasted_when_no_topic_is_due():
    # Holding seats empty for a kind that has nobody waiting would shrink the
    # day's reminders for no reason.
    problems = [item("problem", i) for i in range(MAX_PER_RUN)]
    selected = select_reminders(problems, [])
    assert len(selected) == MAX_PER_RUN
    assert all(r["kind"] == "problem" for r in selected)


def test_a_single_topic_takes_only_the_seat_it_needs():
    problems = [item("problem", i) for i in range(MAX_PER_RUN)]
    selected = select_reminders(problems, [item("topic", 0)])
    assert len(selected) == MAX_PER_RUN
    assert [r["kind"] for r in selected].count("topic") == 1


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


# --- suggestions attached to stale-topic reminders -------------------------
#
# These cover the *producer*. The renderer in test_reminder_mail.py builds its
# own topic dict with suggestions already on it, so it stayed green for weeks
# while nothing in the app ever set the key and the email's "try:" lines could
# never appear.


class FakeProblems:
    """Stands in for the catalogue lookup, which is a third-party call."""

    def __init__(self, problems=None, error=None):
        self.problems = problems or []
        self.error = error
        self.calls = []

    async def unsolved_in_topic(self, db, user_id, tag, platform, limit):
        self.calls.append((tag, platform, limit))
        if self.error:
            raise self.error
        return {"tag": tag, "platform": platform, "problems": self.problems[:limit]}


def a_problem(name="Sliding Window Maximum"):
    return {"id": "239", "name": name, "difficulty": "Hard", "rating": None, "url": "u"}


async def attach(selected, fake, monkeypatch):
    monkeypatch.setattr(
        reminder_service.problem_service, "unsolved_in_topic", fake.unsolved_in_topic
    )
    await reminder_service._attach_suggestions(None, 1, selected)
    return selected


async def test_a_stale_topic_is_given_problems_to_try(monkeypatch):
    selected = [item(kind="topic")]
    fake = FakeProblems([a_problem(), a_problem("Minimum Window Substring")])
    await attach(selected, fake, monkeypatch)
    assert len(selected[0]["suggestions"]) == 2


async def test_problem_reminders_are_left_alone(monkeypatch):
    selected = [item(kind="problem")]
    fake = FakeProblems([a_problem()])
    await attach(selected, fake, monkeypatch)
    assert "suggestions" not in selected[0]
    # A problem reminder already links to itself, so looking anything up for it
    # would be a wasted third-party call.
    assert fake.calls == []


async def test_the_lookup_asks_for_the_topic_and_its_own_platform(monkeypatch):
    selected = [item(kind="topic", platform="leetcode")]
    fake = FakeProblems([a_problem()])
    await attach(selected, fake, monkeypatch)
    tag, platform, limit = fake.calls[0]
    # LeetCode topics get LeetCode problems: suggesting a Codeforces problem
    # for a LeetCode tag sends the reader to the wrong site.
    assert platform == "leetcode"
    assert limit == reminder_service.SUGGESTIONS_PER_TOPIC


async def test_a_failed_catalogue_still_sends_the_reminder(monkeypatch):
    selected = [item(kind="topic")]
    fake = FakeProblems(error=LeetCodeError("down"))
    await attach(selected, fake, monkeypatch)
    # The topic is still worth naming without them.
    assert "suggestions" not in selected[0]
    assert len(selected) == 1


async def test_a_topic_with_nothing_unsolved_gets_no_empty_list(monkeypatch):
    selected = [item(kind="topic")]
    await attach(selected, FakeProblems([]), monkeypatch)
    # Absent rather than empty, so the email renders nothing instead of a
    # heading with no problems under it.
    assert "suggestions" not in selected[0]


async def test_only_the_selected_topic_costs_a_lookup(monkeypatch):
    selected = [item(kind="problem"), item(kind="problem", n=1), item(kind="topic")]
    fake = FakeProblems([a_problem()])
    await attach(selected, fake, monkeypatch)
    assert len(fake.calls) == 1


class FakeSession:
    """Just enough session for run_reminders' writes."""

    def __init__(self):
        self.committed = False

    async def execute(self, *_):
        return None

    async def commit(self):
        self.committed = True


async def test_run_reminders_actually_attaches_suggestions(monkeypatch):
    """The wiring, not the function.

    The original bug was not a broken `_attach_suggestions` — it was that
    nothing called one. Testing the helper in isolation would have stayed green
    through the entire outage, so this asserts the suggestions survive all the
    way to what `run_reminders` returns.
    """
    monkeypatch.setattr(
        reminder_service, "_problems_to_revisit", lambda db, uid, today: _none()
    )
    monkeypatch.setattr(
        reminder_service.topic_service,
        "get_weak_topics",
        lambda db, uid, platform=None: _weak(platform),
    )
    fake = FakeProblems([a_problem()])
    monkeypatch.setattr(
        reminder_service.problem_service, "unsolved_in_topic", fake.unsolved_in_topic
    )

    result = await reminder_service.run_reminders(FakeSession(), 1)

    topics = [r for r in result["reminders"] if r["kind"] == "topic"]
    assert topics, "a stale topic should have been selected"
    assert topics[0]["suggestions"], "the email's 'try:' lines need this key"


async def _none():
    return [], []


async def _weak(platform):
    # Stale enough to be due, on whichever platform is being scored.
    if platform != "leetcode":
        return {"topics": []}
    return {"topics": [topic(days=42, accuracy=None)]}
