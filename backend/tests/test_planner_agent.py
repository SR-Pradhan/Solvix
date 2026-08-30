import json

import pytest

from app.clients.groq_client import GroqError
from app.services import planner_agent
from app.services.planner_agent import (
    MAX_PROBLEMS,
    MAX_TOPICS,
    clamp_limit,
    describe_call,
    extract_json,
    parse_arguments,
)

PLAN = {
    "focus": ["dp"],
    "tasks": [{"title": "Two DP problems", "detail": "", "minutes": 60}],
    "note": "Keep going.",
    "reasoning": "DP has the lowest pass rate and has not been touched in a month.",
}


# --- arguments arrive from a language model, so they are not trusted ---


def test_limits_are_clamped_to_what_the_app_will_serve():
    assert clamp_limit(500, default=6, maximum=MAX_TOPICS) == MAX_TOPICS
    assert clamp_limit(0, default=6, maximum=MAX_TOPICS) == 1


def test_a_nonsense_limit_falls_back_to_the_default():
    # The model can send a string, a null, or a sentence where a number goes.
    assert clamp_limit("lots", default=6, maximum=MAX_TOPICS) == 6
    assert clamp_limit(None, default=6, maximum=MAX_TOPICS) == 6
    assert clamp_limit({"n": 3}, default=6, maximum=MAX_TOPICS) == 6


def test_arguments_parse_from_the_json_string_the_api_sends():
    assert parse_arguments('{"topic": "dp"}') == {"topic": "dp"}


def test_malformed_arguments_become_empty_rather_than_raising():
    assert parse_arguments("{not json") == {}
    assert parse_arguments("[1, 2]") == {}
    assert parse_arguments(None) == {}


# --- the final answer ---


def test_json_is_extracted_even_when_wrapped_in_prose():
    content = 'Here is the plan:\n```json\n{"focus": ["dp"]}\n```\nHope that helps.'
    assert extract_json(content) == {"focus": ["dp"]}


def test_unusable_content_yields_nothing():
    assert extract_json("I could not decide.") is None
    assert extract_json("") is None
    assert extract_json(None) is None


# --- the trace shown to the reader ---


def test_the_trace_names_the_topic_that_was_investigated():
    line = describe_call("get_unsolved_problems", {"topic": "graphs"})
    assert "graphs" in line


def test_every_tool_has_a_readable_description():
    for tool in planner_agent.TOOLS:
        name = tool["function"]["name"]
        assert not describe_call(name, {}).startswith("Called ")


# --- the loop ---


class FakeModel:
    """Replays scripted assistant turns, and records what it was sent."""

    def __init__(self, turns):
        self.turns = list(turns)
        self.sent = []

    async def __call__(self, messages, tools, api_key, model, timeout=60.0):
        self.sent.append(list(messages))
        return self.turns.pop(0)


def tool_turn(name, arguments=None, call_id="call_1"):
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": call_id,
                "type": "function",
                "function": {
                    "name": name,
                    "arguments": json.dumps(arguments or {}),
                },
            }
        ],
    }


def answer_turn(plan=None):
    return {"role": "assistant", "content": json.dumps(plan or PLAN)}


@pytest.fixture
def no_network(monkeypatch):
    async def fake_tool(db, user_id, name, arguments):
        return {"ok": name}

    monkeypatch.setattr(planner_agent, "run_tool", fake_tool)


async def test_a_plan_is_returned_with_the_steps_it_took(monkeypatch, no_network):
    model = FakeModel([tool_turn("get_weak_topics"), answer_turn()])
    monkeypatch.setattr(planner_agent, "complete_with_tools", model)

    plan, trace = await planner_agent.run(db=None, user_id=1)

    assert plan == PLAN
    assert trace == ["Checked which topics have decayed"]


async def test_tool_results_are_fed_back_to_the_model(monkeypatch, no_network):
    model = FakeModel([tool_turn("get_recent_activity"), answer_turn()])
    monkeypatch.setattr(planner_agent, "complete_with_tools", model)

    await planner_agent.run(db=None, user_id=1)

    # The second turn must carry the tool's answer, or the model is deciding
    # with nothing more than it had before.
    second_turn = model.sent[1]
    assert any(m.get("role") == "tool" for m in second_turn)


async def test_a_failing_tool_does_not_end_the_run(monkeypatch):
    async def exploding_tool(db, user_id, name, arguments):
        raise RuntimeError("Codeforces is down")

    monkeypatch.setattr(planner_agent, "run_tool", exploding_tool)
    model = FakeModel([tool_turn("get_weak_topics"), answer_turn()])
    monkeypatch.setattr(planner_agent, "complete_with_tools", model)

    plan, _ = await planner_agent.run(db=None, user_id=1)

    assert plan == PLAN
    # The failure is handed back as data so the model can work around it.
    assert "unavailable" in json.dumps(model.sent[1])


async def test_prose_instead_of_json_is_nudged_once(monkeypatch, no_network):
    model = FakeModel(
        [{"role": "assistant", "content": "Practise more DP!"}, answer_turn()]
    )
    monkeypatch.setattr(planner_agent, "complete_with_tools", model)

    plan, _ = await planner_agent.run(db=None, user_id=1)
    assert plan == PLAN


async def test_a_model_that_never_finishes_gives_up(monkeypatch, no_network):
    # Every turn asks for another tool. Without a budget this runs forever, at
    # a cost per turn.
    model = FakeModel([tool_turn("get_weak_topics") for _ in range(planner_agent.MAX_STEPS)])
    monkeypatch.setattr(planner_agent, "complete_with_tools", model)

    with pytest.raises(GroqError):
        await planner_agent.run(db=None, user_id=1)


async def test_an_unknown_tool_is_reported_rather_than_raised():
    # The model inventing a tool name is its mistake to correct, and telling it
    # so is more useful than crashing the run.
    result = await planner_agent.run_tool(None, 1, "get_the_answer", {})
    assert "no such tool" in result["error"]


async def test_unsolved_problems_requires_a_real_platform():
    result = await planner_agent.run_tool(None, 1, "get_unsolved_problems", {"topic": "dp"})
    assert "error" in result

    result = await planner_agent.run_tool(
        None, 1, "get_unsolved_problems", {"topic": "dp", "platform": "atcoder"}
    )
    assert "error" in result


def test_the_problem_limit_is_small_enough_to_read():
    # The plan names problems; a tool that returns fifty makes the model choose
    # badly and the prompt expensive.
    assert MAX_PROBLEMS <= 5


def test_an_infinite_limit_falls_back_to_the_default():
    """Same overflow as the plan parser: json accepts a bare `Infinity`."""
    assert clamp_limit(float("inf"), default=5, maximum=20) == 5
