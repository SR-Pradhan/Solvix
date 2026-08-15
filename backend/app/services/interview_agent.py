"""A mock interview: multi-turn, about one problem, ending in an assessment.

This is the part of Solvix that needs an agent rather than a prompt. The
planner calls tools and then writes; here the model holds a conversation whose
next question depends on the last answer, across a session that survives a
page refresh — so the state lives in the database and the model is handed it
each turn.

**The one rule it must not break.** Solvix never asks the user to record how
they are doing. An interview does not violate that: nothing here is
self-reported. The user demonstrates an approach and the agent judges it, which
is evidence rather than opinion. That is also why the findings are stored apart
from the weak-topic scores and never folded into them — a pass rate and an
interviewer's impression are different kinds of claim, and averaging them would
produce a number nobody could explain.
"""

from __future__ import annotations

import json
import logging
import random

from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.groq_client import GroqError, complete_json, complete_with_tools
from app.core.config import settings
from app.services import problem_service, topic_service

log = logging.getLogger("solvix.interview")

# A real screening round is 30-45 minutes. Past this the conversation has
# stopped being an interview and the transcript stops fitting in a prompt.
MAX_TURNS = 24

# How many of the weakest topics to choose the problem from. Always picking the
# single weakest would ask about the same topic every time, and a rotation the
# user cannot predict is closer to a real interview anyway.
TOPIC_POOL = 4

INTERVIEWER_PROMPT = (
    "You are conducting a technical screening interview. You are direct, "
    "warm, and interested in how the candidate thinks.\n\n"
    "The problem is: {problem}\n"
    "Topic: {topic}\n\n"
    "Run it the way a real interviewer does:\n"
    "- Ask them to restate the problem and talk through an approach BEFORE any "
    "code. Do not accept 'I would use a hash map' as an approach — ask what it "
    "maps to and why.\n"
    "- Probe complexity every time they propose something: time, space, and "
    "why.\n"
    "- Ask about edge cases they have not mentioned — empty input, duplicates, "
    "one element, overflow.\n"
    "- If they are stuck, give the smallest hint that unblocks them, not the "
    "answer. Being stuck is information, and rescuing them destroys it.\n"
    "- If they are wrong, do not correct them immediately. Ask a question whose "
    "answer shows them the problem.\n\n"
    "One question at a time. Two or three sentences per turn. Never write the "
    "solution for them, and never claim they said something they did not."
)

SUMMARY_PROMPT = (
    "You just interviewed a candidate. Assess them from the transcript alone.\n\n"
    "Reply with JSON only:\n"
    '{"verdict": "one sentence, honest", "strengths": ["..."], '
    '"gaps": ["..."], "complexity_handled": true, '
    '"advice": "one concrete thing to practise next"}\n\n'
    "Judge only what the transcript shows. If they never discussed complexity, "
    "complexity_handled is false and it belongs in gaps. Do not invent "
    "strengths to be kind — a review that flatters is worth nothing."
)


def choose_topic(topics: list[dict], pool: int = TOPIC_POOL) -> dict | None:
    """Pick which weak topic to examine.

    Randomised across the weakest few rather than always taking the worst: an
    interview that asks about the same topic every day stops testing anything,
    and unpredictability is part of what makes practice realistic.
    """
    if not topics:
        return None
    return random.choice(topics[:pool])


def opening_message(problem_name: str, topic: str) -> str:
    return (
        f"Let's do a {topic} problem: **{problem_name}**.\n\n"
        "Take a moment to read it, then tell me in your own words what it is "
        "asking — and your first thought on how to approach it. Don't write "
        "code yet."
    )


def visible_turns(transcript: list[dict]) -> list[dict]:
    """The conversation as the user sees it, without the system prompt."""
    return [t for t in transcript if t.get("role") in ("assistant", "user")]


def is_over(transcript: list[dict], max_turns: int = MAX_TURNS) -> bool:
    return len(visible_turns(transcript)) >= max_turns


def parse_findings(raw: dict) -> dict:
    """Coerce the closing assessment into the shape the API promises.

    Same reasoning as the daily plan: the model will eventually return a string
    where a list belongs, and a bad generation should cost detail rather than
    the whole review.
    """

    def as_list(value) -> list[str]:
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, list):
            return []
        return [str(v).strip()[:200] for v in value if str(v).strip()][:5]

    return {
        "verdict": str(raw.get("verdict") or "").strip()[:300],
        "strengths": as_list(raw.get("strengths")),
        "gaps": as_list(raw.get("gaps")),
        # Absent means it was not demonstrated. Defaulting to True would let a
        # silent interview pass a check it never faced.
        "complexity_handled": bool(raw.get("complexity_handled")),
        "advice": str(raw.get("advice") or "").strip()[:300],
    }


async def pick_problem(db: AsyncSession, user_id: int) -> dict | None:
    """A problem in a weak topic that the user has never solved.

    Never one they have already done: an interview about a problem they solved
    last week tests recall of an answer rather than how they think.
    """
    # The platform-labelled variant: a tag alone does not say where to find a
    # problem, and Codeforces and LeetCode disagree about what a topic is.
    scored = await topic_service.weak_topics_with_platform(
        db, user_id, limit=TOPIC_POOL * 2
    )
    topic = choose_topic(scored)
    if topic is None:
        return None

    found = await problem_service.unsolved_in_topic(
        db, user_id, topic["tag"], topic["platform"], limit=5
    )
    problems = found["problems"]
    if not problems:
        return None

    problem = problems[0]
    return {
        "topic": topic["tag"],
        "platform": topic["platform"],
        "name": problem["name"],
        "url": problem.get("url"),
    }


async def next_question(problem: dict, transcript: list[dict]) -> str:
    """One interviewer turn, given everything said so far."""
    system = INTERVIEWER_PROMPT.format(
        problem=f"{problem['name']} ({problem.get('url') or 'no link'})",
        topic=problem["topic"],
    )
    messages = [{"role": "system", "content": system}] + [
        {"role": t["role"], "content": t["content"]} for t in visible_turns(transcript)
    ]

    message = await complete_with_tools(
        messages=messages,
        # No tools: everything this agent needs is in the conversation. Handing
        # it tools it cannot use invites it to call them.
        tools=[],
        api_key=settings.groq_api_key,
        model=settings.groq_model,
    )
    content = (message.get("content") or "").strip()
    if not content:
        raise GroqError("The interviewer returned nothing")
    return content


async def summarise(problem: dict, transcript: list[dict]) -> dict:
    """The closing assessment, from the transcript alone."""
    conversation = "\n\n".join(
        f"{t['role'].upper()}: {t['content']}" for t in visible_turns(transcript)
    )
    raw = await complete_json(
        system=SUMMARY_PROMPT,
        user=f"Problem: {problem['name']} (topic: {problem['topic']})\n\n{conversation}",
        api_key=settings.groq_api_key,
        model=settings.groq_model,
    )
    return parse_findings(raw)
