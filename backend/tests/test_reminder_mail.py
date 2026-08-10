from datetime import date

from app.services.reminder_mail import body, subject_line

TODAY = date(2026, 8, 10)
APP = "https://solvix-roan.vercel.app"


def problem(title="Find Peak Element", url="https://leetcode.com/problems/find-peak-element/"):
    return {
        "kind": "problem",
        "platform": "leetcode",
        "subject": "leetcode:0162-find-peak-element",
        "title": title,
        "reason": "solved 3 days ago",
        "url": url,
    }


def topic(title="Sliding Window"):
    return {
        "kind": "topic",
        "platform": "leetcode",
        "subject": title,
        "title": title,
        "reason": "not practised in 4 weeks",
        "url": None,
    }


def test_subject_says_what_is_inside():
    # A subject that reveals nothing gets filtered within a week.
    line = subject_line([problem(), topic(), topic("Math")], TODAY)
    assert line == "Solvix — 1 problem to revisit and 2 topics going stale"


def test_subject_with_only_problems():
    assert subject_line([problem(), problem("Two Sum")], TODAY) == (
        "Solvix — 2 problems to revisit"
    )


def test_subject_with_only_topics():
    assert subject_line([topic()], TODAY) == "Solvix — 1 topic going stale"


def test_subject_when_nothing_is_due():
    assert subject_line([], TODAY) == "Solvix — nothing due today"


def test_body_links_every_problem():
    text = body([problem()], TODAY, APP)
    assert "https://leetcode.com/problems/find-peak-element/" in text
    assert "solved 3 days ago" in text


def test_body_separates_the_two_kinds():
    text = body([problem(), topic()], TODAY, APP)
    assert text.index("Revisit:") < text.index("Going stale:")


def test_body_omits_an_empty_section():
    text = body([topic()], TODAY, APP)
    assert "Revisit:" not in text
    assert "Going stale:" in text


def test_body_survives_a_problem_with_no_link():
    # LeetHub folder names that do not parse leave the URL null; the line still
    # has to render rather than printing "None".
    text = body([problem(url=None)], TODAY, APP)
    assert "None" not in text
    assert "Find Peak Element" in text


def test_body_always_points_home():
    assert APP in body([topic()], TODAY, APP)
