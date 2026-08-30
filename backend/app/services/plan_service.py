"""Builds a daily practice plan.

The plan is generated once per day and stored, so revisiting the dashboard does
not spend a model call (or hand the user a different plan every refresh).

Two ways of producing it, tried in order:

1. **The agent** (`planner_agent`) — the model is given read-only tools and
   decides what to look at: which topics have decayed, what problems are left
   in them, what is already due, whether they have practised lately.
2. **The one-shot prompt** — the original: a fixed snapshot of the six weakest
   topics, pasted into a prompt.

The fallback is not ceremony. A tool-calling loop has more ways to fail than a
single completion — a model that never stops calling tools, a provider that
handles tools badly — and a plan is a daily habit, so degrading to a simpler
plan beats showing an error. Which model runs the agent is configuration, so
the loop can move to a stronger provider without touching this file.
"""

import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.clients.groq_client import GroqError, complete_json
from app.core.config import settings
from app.db.models import DailyPlan
from app.services import planner_agent, stats_service, topic_service

log = logging.getLogger("solvix.plan")

MIN_TOPICS_FOR_PLAN = 3
TOPICS_IN_PROMPT = 6
MAX_TASKS = 4
MAX_TASK_MINUTES = 180

SYSTEM_PROMPT = (
    "You are a competitive programming coach. You are given a student's weakest "
    "topics, measured by how often their attempts pass and how long since they "
    "last practised each one. Write a short practice plan for today.\n\n"
    "Reply with JSON only, in exactly this shape:\n"
    '{"focus": ["topic", "topic"], "tasks": [{"title": "...", "detail": "...", '
    '"minutes": 30}], "note": "one encouraging sentence"}\n\n'
    "Rules: at most 4 tasks. Keep each title under 60 characters and each detail "
    "under 200. Total time across tasks should be 60-120 minutes. Name specific "
    "topics from the data rather than giving generic advice. Do not invent "
    "problem names or links."
)


def build_user_prompt(stats: dict, topics: list[dict]) -> str:
    """Describe the student's state in plain text for the model."""
    lines = [
        f"Problems solved: {stats['problems_solved']}",
        f"Current streak: {stats['current_streak_days']} days",
        "",
        "Weakest topics (weakest first):",
    ]

    for topic in topics[:TOPICS_IN_PROMPT]:
        accuracy = (
            f"{round(topic['accuracy'] * 100)}% of attempts pass"
            if topic["accuracy"] is not None
            else "pass rate unknown"
        )
        days = topic["days_since_last_solve"]
        recency = "never solved" if days is None else f"last solved {days} days ago"
        lines.append(f"- {topic['tag']}: {accuracy}, {recency}, {topic['status']}")

    return "\n".join(lines)


def parse_plan(raw: dict) -> dict:
    """Coerce the model's JSON into the shape the API promises.

    A language model can return a string where a list belongs, or twelve tasks
    when asked for four. Validating here means a bad generation degrades into a
    shorter plan rather than a 500.
    """
    focus = raw.get("focus") or []
    if isinstance(focus, str):
        focus = [focus]
    focus = [str(f).strip() for f in focus if str(f).strip()][:TOPICS_IN_PROMPT]

    tasks = []
    for item in raw.get("tasks") or []:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        try:
            minutes = int(item.get("minutes") or 30)
        # OverflowError as well as the obvious two: Python's json module parses
        # a bare `Infinity` happily, and int() of it raises neither TypeError
        # nor ValueError. Without it a single odd token turns the whole plan
        # into a 500, which is the failure this function exists to prevent.
        except (TypeError, ValueError, OverflowError):
            minutes = 30
        tasks.append(
            {
                "title": title[:120],
                "detail": str(item.get("detail") or "").strip()[:400],
                "minutes": max(5, min(minutes, MAX_TASK_MINUTES)),
            }
        )
        if len(tasks) == MAX_TASKS:
            break

    return {
        "focus": focus,
        "tasks": tasks,
        "note": str(raw.get("note") or "").strip()[:300],
        # The agent explains its choice; the one-shot prompt has nothing to
        # explain, so this is empty there rather than invented.
        "reasoning": str(raw.get("reasoning") or "").strip()[:500],
    }


async def get_daily_plan(
    db: AsyncSession, user_id: int, regenerate: bool = False
) -> dict:
    today = clock.today()

    if not regenerate:
        stored = await db.scalar(
            select(DailyPlan).where(
                DailyPlan.user_id == user_id, DailyPlan.plan_date == today
            )
        )
        if stored:
            return {"date": today, "generated": False, **stored.payload}

    topics_result = await topic_service.get_weak_topics(db, user_id)
    topics = topics_result["topics"]
    if len(topics) < MIN_TOPICS_FOR_PLAN:
        return {
            "date": today,
            "generated": False,
            "focus": [],
            "tasks": [],
            "note": "",
            "unavailable": (
                f"Practise a few more problems first. Solvix needs at least "
                f"{MIN_TOPICS_FOR_PLAN} scored topics to plan a session."
            ),
        }

    trace: list[str] = []
    try:
        raw, trace = await planner_agent.run(db, user_id)
    except GroqError as exc:
        # Falling back rather than failing: a plan is a daily habit, and a
        # simpler plan beats an error where today's practice should be.
        log.warning("planner agent fell back to the one-shot prompt: %s", exc)
        stats = await stats_service.get_stats(db, user_id)
        raw = await complete_json(
            system=SYSTEM_PROMPT,
            user=build_user_prompt(stats, topics),
            api_key=settings.groq_api_key,
            model=settings.groq_model,
        )

    plan = parse_plan(raw)
    # What the agent actually looked at, shown in the UI. Without it the reader
    # has no way to tell a plan built from their data from one invented whole.
    plan["steps"] = trace

    # on_conflict_do_update so a regenerate replaces today's plan rather than
    # colliding with the row written by the first request of the day.
    stmt = insert(DailyPlan).values(
        user_id=user_id, plan_date=today, payload=plan
    )
    await db.execute(
        stmt.on_conflict_do_update(
            index_elements=["user_id", "plan_date"], set_={"payload": plan}
        )
    )
    await db.commit()

    return {"date": today, "generated": True, **plan}
