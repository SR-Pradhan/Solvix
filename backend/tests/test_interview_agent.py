import pytest

from app.services import interview_agent
from app.services.interview_agent import (
    MAX_TURNS,
    TOPIC_POOL,
    choose_topic,
    is_over,
    opening_message,
    parse_findings,
    visible_turns,
)


def topics(n):
    return [{"tag": f"topic{i}", "platform": "leetcode"} for i in range(n)]


def turns(n):
    return [
        {"role": "assistant" if i % 2 == 0 else "user", "content": f"turn {i}"}
        for i in range(n)
    ]


# --- choosing what to ask about ---


def test_the_topic_comes_from_the_weakest_few():
    chosen = choose_topic(topics(10))
    assert chosen["tag"] in {f"topic{i}" for i in range(TOPIC_POOL)}


def test_choosing_from_a_short_list_still_works():
    assert choose_topic(topics(1))["tag"] == "topic0"


def test_no_topics_means_no_interview():
    assert choose_topic([]) is None


def test_the_choice_is_not_always_the_weakest(monkeypatch):
    # Always asking about the single weakest topic would examine the same thing
    # every day, which stops testing anything.
    seen = {choose_topic(topics(10))["tag"] for _ in range(60)}
    assert len(seen) > 1


# --- the opening ---


def test_the_opening_names_the_problem_and_forbids_code():
    message = opening_message("Two Sum", "Hash Table")
    assert "Two Sum" in message
    assert "Hash Table" in message
    assert "code" in message.lower()


# --- transcript rules ---


def test_only_the_conversation_is_shown_to_the_user():
    transcript = [
        {"role": "system", "content": "secret instructions"},
        {"role": "assistant", "content": "hello"},
        {"role": "user", "content": "hi"},
    ]
    assert [t["content"] for t in visible_turns(transcript)] == ["hello", "hi"]


def test_an_interview_ends_at_the_turn_limit():
    assert not is_over(turns(MAX_TURNS - 1))
    assert is_over(turns(MAX_TURNS))


def test_the_system_prompt_does_not_count_towards_the_limit():
    transcript = [{"role": "system", "content": "..."}] + turns(MAX_TURNS - 1)
    assert not is_over(transcript)


# --- the closing assessment ---


def test_findings_are_coerced_into_shape():
    parsed = parse_findings(
        {
            "verdict": "Solid approach, shaky on complexity.",
            "strengths": "Explained the hash map clearly",
            "gaps": ["Did not consider duplicates"],
            "complexity_handled": True,
            "advice": "Practise stating time and space before coding.",
        }
    )
    # A string where a list belongs is the model's most common misstep.
    assert parsed["strengths"] == ["Explained the hash map clearly"]
    assert parsed["complexity_handled"] is True


def test_an_empty_assessment_does_not_crash():
    parsed = parse_findings({})
    assert parsed["verdict"] == ""
    assert parsed["strengths"] == []


def test_complexity_defaults_to_not_demonstrated():
    # Absent means it never came up. Defaulting to true would let a silent
    # interview pass a check it never faced.
    assert parse_findings({}) ["complexity_handled"] is False
    assert parse_findings({"complexity_handled": "no"})["complexity_handled"] is True


def test_runaway_text_is_truncated():
    parsed = parse_findings({"verdict": "x" * 900, "gaps": ["y" * 900]})
    assert len(parsed["verdict"]) <= 300
    assert len(parsed["gaps"][0]) <= 200


def test_only_a_handful_of_points_survive():
    parsed = parse_findings({"gaps": [f"gap {i}" for i in range(20)]})
    assert len(parsed["gaps"]) <= 5


async def test_the_interviewer_is_given_no_tools(monkeypatch):
    # It has everything it needs in the conversation; offering tools it cannot
    # use only invites it to call them.
    captured = {}

    async def fake_model(messages, tools, api_key, model, timeout=60.0):
        captured["tools"] = tools
        captured["messages"] = messages
        return {"role": "assistant", "content": "What is the time complexity?"}

    monkeypatch.setattr(interview_agent, "complete_with_tools", fake_model)

    problem = {"name": "Two Sum", "topic": "Hash Table", "url": None}
    question = await interview_agent.next_question(problem, turns(2))

    assert question == "What is the time complexity?"
    assert captured["tools"] == []
    assert captured["messages"][0]["role"] == "system"


async def test_an_empty_reply_from_the_model_is_an_error(monkeypatch):
    async def silent_model(messages, tools, api_key, model, timeout=60.0):
        return {"role": "assistant", "content": "   "}

    monkeypatch.setattr(interview_agent, "complete_with_tools", silent_model)

    with pytest.raises(Exception):
        await interview_agent.next_question(
            {"name": "Two Sum", "topic": "Hash Table", "url": None}, turns(2)
        )


def test_an_unanswered_transcript_has_nothing_to_assess():
    # The guard that stops a review of silence: with only the opening question
    # there is no answer to judge, and the model will otherwise dutifully write
    # "the candidate did not provide a solution" — a verdict on a person for an
    # interview that never happened.
    opener = [{"role": "assistant", "content": "Tell me your approach."}]
    assert not any(t["role"] == "user" for t in opener)

    answered = opener + [{"role": "user", "content": "Use a prefix sum array."}]
    assert any(t["role"] == "user" for t in answered)
