from app.services.plan_service import MAX_TASKS, MAX_TASK_MINUTES, build_user_prompt, parse_plan


def topic(tag, accuracy=0.4, days=10, status="Needs work"):
    return {
        "tag": tag,
        "accuracy": accuracy,
        "days_since_last_solve": days,
        "status": status,
    }


STATS = {"problems_solved": 120, "current_streak_days": 3}


def test_prompt_includes_stats_and_topics():
    prompt = build_user_prompt(STATS, [topic("binary search"), topic("dp")])
    assert "120" in prompt
    assert "binary search" in prompt
    assert "dp" in prompt


def test_prompt_describes_missing_accuracy_without_crashing():
    prompt = build_user_prompt(STATS, [topic("dp", accuracy=None)])
    assert "pass rate unknown" in prompt


def test_prompt_describes_never_solved_topics():
    prompt = build_user_prompt(STATS, [topic("flows", days=None)])
    assert "never solved" in prompt


def test_prompt_caps_the_number_of_topics():
    prompt = build_user_prompt(STATS, [topic(f"tag{i}") for i in range(20)])
    assert prompt.count("- tag") <= 6


def test_parse_keeps_a_well_formed_plan():
    plan = parse_plan(
        {
            "focus": ["dp", "greedy"],
            "tasks": [{"title": "Solve 3 dp problems", "detail": "Start easy", "minutes": 45}],
            "note": "Good luck",
        }
    )
    assert plan["focus"] == ["dp", "greedy"]
    assert plan["tasks"][0]["minutes"] == 45
    assert plan["note"] == "Good luck"


def test_parse_accepts_focus_returned_as_a_string():
    assert parse_plan({"focus": "dp"})["focus"] == ["dp"]


def test_parse_caps_task_count():
    raw = {"tasks": [{"title": f"Task {i}", "minutes": 20} for i in range(12)]}
    assert len(parse_plan(raw)["tasks"]) == MAX_TASKS


def test_parse_clamps_absurd_durations():
    raw = {"tasks": [{"title": "Marathon", "minutes": 100000}]}
    assert parse_plan(raw)["tasks"][0]["minutes"] == MAX_TASK_MINUTES


def test_parse_defaults_unparseable_minutes():
    raw = {"tasks": [{"title": "Practice", "minutes": "about an hour"}]}
    assert parse_plan(raw)["tasks"][0]["minutes"] == 30


def test_parse_drops_tasks_without_a_title():
    raw = {"tasks": [{"detail": "no title"}, {"title": "  ", "minutes": 10}]}
    assert parse_plan(raw)["tasks"] == []


def test_parse_ignores_non_object_tasks():
    raw = {"tasks": ["just a string", {"title": "Real task", "minutes": 15}]}
    tasks = parse_plan(raw)["tasks"]
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Real task"


def test_parse_survives_a_completely_empty_response():
    assert parse_plan({}) == {
        "focus": [],
        "tasks": [],
        "note": "",
        # Empty rather than absent: the one-shot prompt has no reasoning to
        # give, and inventing one would be the model's words put in its mouth.
        "reasoning": "",
    }


def test_parse_truncates_runaway_text():
    raw = {"tasks": [{"title": "x" * 500, "detail": "y" * 2000, "minutes": 30}]}
    task = parse_plan(raw)["tasks"][0]
    assert len(task["title"]) <= 120
    assert len(task["detail"]) <= 400
