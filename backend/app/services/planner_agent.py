"""The daily plan, written by an agent rather than a single prompt.

The difference is not the wording, it is who decides what to look at. The
one-shot version was handed a fixed snapshot — the six weakest topics — and had
to write a plan from that and nothing else. It could not check whether a topic
still had easy problems left, notice that nothing had been solved for four
days, or see what was already due for revision.

Here the model is given tools and chooses. That is worth the extra complexity
only because the choices are real: which topic to open, whether to look at
recent activity at all, when it has enough to write. A loop that always calls
the same tools in the same order is a function with extra steps.

Everything the agent can do is read-only and scoped to one user. A tool cannot
be talked into touching another account, because the user id is bound here and
never taken from the model.
"""

from __future__ import annotations

import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.groq_client import GroqError, complete_with_tools
from app.core.config import settings
from app.services import problem_service, reminder_service, stats_service, topic_service

log = logging.getLogger("solvix.planner")

# Enough turns to look at three or four things and then write. A model that has
# not finished by then is looping, not thinking, and every turn is a call to
# somebody else's service.
MAX_STEPS = 6

# Guardrails on what a tool may be asked for, so a confused model cannot make
# an expensive request.
MAX_TOPICS = 8
MAX_PROBLEMS = 5

SYSTEM_PROMPT = (
    "You are a competitive programming coach planning today's practice for one "
    "student. You have tools that read their real practice history.\n\n"
    "Work like a coach, not a search engine: look at their weak topics first, "
    "then investigate the one or two that matter most before deciding. Check "
    "what is already due for revision so you do not duplicate it, and look at "
    "recent activity if the plan depends on whether they have been practising.\n\n"
    "Do not call more tools than you need, and do not call the same tool twice "
    "with the same arguments.\n\n"
    "When you have enough, reply with JSON only, in exactly this shape:\n"
    '{"focus": ["topic"], "tasks": [{"title": "...", "detail": "...", '
    '"minutes": 30}], "note": "one encouraging sentence", '
    '"reasoning": "two sentences on why you chose these"}\n\n'
    "Rules: at most 4 tasks, 60-120 minutes in total. Name only problems the "
    "tools actually returned — never invent a problem or a link. Name specific "
    "topics from the data rather than giving generic advice."
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weak_topics",
            "description": (
                "The student's weakest topics, weakest first, scored by how "
                "often their attempts pass and how long since they practised. "
                "Start here."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": f"How many topics to return, up to {MAX_TOPICS}.",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_unsolved_problems",
            "description": (
                "Problems in one topic the student has never solved, easiest "
                "first. Use this before recommending practice in a topic, so "
                "the plan names real problems."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "The tag, exactly as returned by get_weak_topics."},
                    "platform": {
                        "type": "string",
                        "enum": ["codeforces", "leetcode"],
                        "description": "Which platform to search.",
                    },
                },
                "required": ["topic", "platform"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_due_revisions",
            "description": (
                "What the spaced-repetition schedule already says is due "
                "today. Check this so the plan does not duplicate it."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_activity",
            "description": (
                "Totals and streaks: how much they have solved and whether "
                "they have practised recently."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


def clamp_limit(raw, default: int, maximum: int) -> int:
    """Whatever the model asked for, kept inside what the app will serve.

    Arguments arrive as free-form JSON from a language model, so they are
    treated as user input from a stranger: coerced, bounded, never trusted to
    be the right type.
    """
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return max(1, min(value, maximum))


async def run_tool(
    db: AsyncSession, user_id: int, name: str, arguments: dict
) -> dict:
    """Execute one tool call. The user id comes from the session, never the model."""
    if name == "get_weak_topics":
        limit = clamp_limit(arguments.get("limit"), default=6, maximum=MAX_TOPICS)
        result = await topic_service.get_weak_topics(db, user_id, limit=limit)
        return {
            "topics": [
                {
                    "tag": t["tag"],
                    "platform": t["platform"],
                    "status": t["status"],
                    "accuracy": t["accuracy"],
                    "days_since_last_solve": t["days_since_last_solve"],
                }
                for t in result["topics"]
            ]
        }

    if name == "get_unsolved_problems":
        topic = str(arguments.get("topic") or "").strip()
        platform = arguments.get("platform")
        if not topic or platform not in ("codeforces", "leetcode"):
            return {"error": "topic and a valid platform are required"}
        found = await problem_service.unsolved_in_topic(
            db, user_id, topic, platform, limit=MAX_PROBLEMS
        )
        return {
            "topic": topic,
            "problems": [
                {
                    "name": p["name"],
                    "difficulty": p.get("difficulty") or p.get("rating"),
                    "url": p.get("url"),
                }
                for p in found["problems"]
            ],
        }

    if name == "get_due_revisions":
        due = await reminder_service.list_reminders(db, user_id)
        return {
            "due": [
                {"kind": r["kind"], "title": r["title"], "why": r["reason"]}
                for r in due["reminders"]
            ]
        }

    if name == "get_recent_activity":
        stats = await stats_service.get_stats(db, user_id)
        return {
            "problems_solved": stats["problems_solved"],
            "current_streak_days": stats["current_streak_days"],
            "longest_streak_days": stats["longest_streak_days"],
        }

    # An unknown name is the model's mistake, and telling it so is more useful
    # than raising: it can correct itself on the next turn.
    return {"error": f"no such tool: {name}"}


def parse_arguments(raw: str | dict | None) -> dict:
    """Tool arguments arrive as a JSON string, and sometimes as nonsense."""
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except ValueError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def describe_call(name: str, arguments: dict) -> str:
    """One human-readable line per tool call, for the trace shown in the UI.

    The trace is the honest part of the feature: it lets the reader see that
    the model looked at their data rather than inventing a plan, and it is how
    a bad plan gets diagnosed.
    """
    if name == "get_unsolved_problems":
        topic = arguments.get("topic", "?")
        return f"Looked for unsolved {topic} problems"
    return {
        "get_weak_topics": "Checked which topics have decayed",
        "get_due_revisions": "Checked what is already due for revision",
        "get_recent_activity": "Checked recent activity and streaks",
    }.get(name, f"Called {name}")


def extract_json(content: str | None) -> dict | None:
    """The final answer, which is JSON in prose more often than it should be."""
    if not content:
        return None
    text = content.strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        parsed = json.loads(text[start : end + 1])
    except ValueError:
        return None
    return parsed if isinstance(parsed, dict) else None


async def run(db: AsyncSession, user_id: int) -> tuple[dict, list[str]]:
    """Run the loop until the model answers. Returns the raw plan and a trace.

    Raises GroqError if the model never produces a usable answer — the caller
    decides whether that means falling back or failing, because a missing plan
    is not the same kind of problem in every context.
    """
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "Plan my practice for today."},
    ]
    trace: list[str] = []

    for _ in range(MAX_STEPS):
        message = await complete_with_tools(
            messages=messages,
            tools=TOOLS,
            api_key=settings.groq_api_key,
            model=settings.groq_model,
        )

        calls = message.get("tool_calls") or []
        if not calls:
            plan = extract_json(message.get("content"))
            if plan is not None:
                return plan, trace
            # No tool calls and no usable JSON: nudge once rather than giving
            # up, because the loop is cheap and a reformat usually works.
            messages.append(message)
            messages.append(
                {
                    "role": "user",
                    "content": "Reply with only the JSON object described earlier.",
                }
            )
            continue

        messages.append(message)
        for call in calls:
            function = call.get("function") or {}
            name = function.get("name") or ""
            arguments = parse_arguments(function.get("arguments"))

            trace.append(describe_call(name, arguments))
            try:
                result = await run_tool(db, user_id, name, arguments)
            except Exception as exc:
                # A failing tool is information, not a crash: the model can
                # choose something else with what it already has.
                log.warning("planner tool %s failed: %s", name, exc)
                result = {"error": f"{name} is unavailable right now"}

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.get("id"),
                    "content": json.dumps(result)[:4000],
                }
            )

    raise GroqError("The planner did not finish within its step budget")
