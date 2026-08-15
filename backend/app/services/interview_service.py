"""Session handling for mock interviews: start, reply, finish, list.

The agent decides what to say; this decides what is allowed. Keeping them
apart means the rules — who owns an interview, when it is closed, how long it
may run — are plain code that can be read and tested without a model.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Interview
from app.services import interview_agent

OPEN = "open"
FINISHED = "finished"


class InterviewError(Exception):
    """The request cannot be honoured; the API layer maps this to a 400."""


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def as_dict(interview: Interview) -> dict:
    return {
        "id": interview.id,
        "topic": interview.topic,
        "platform": interview.platform,
        "problem_name": interview.problem_name,
        "problem_url": interview.problem_url,
        "status": interview.status,
        "turns": interview_agent.visible_turns(interview.transcript or []),
        "findings": interview.findings,
        "created_at": interview.created_at,
    }


async def _owned(db: AsyncSession, user_id: int, interview_id: int) -> Interview:
    """Load an interview, or refuse. Ownership is checked here, once.

    Scoping the query by user rather than fetching and comparing afterwards
    means a forgotten comparison cannot leak somebody else's transcript.
    """
    interview = await db.scalar(
        select(Interview).where(
            Interview.id == interview_id, Interview.user_id == user_id
        )
    )
    if interview is None:
        raise InterviewError("No such interview")
    return interview


async def start(db: AsyncSession, user_id: int) -> dict:
    problem = await interview_agent.pick_problem(db, user_id)
    if problem is None:
        raise InterviewError(
            "Solvix needs a few more solved problems before it can pick "
            "something to interview you on."
        )

    opening = interview_agent.opening_message(problem["name"], problem["topic"])

    interview = Interview(
        user_id=user_id,
        topic=problem["topic"],
        platform=problem["platform"],
        problem_name=problem["name"],
        problem_url=problem.get("url"),
        status=OPEN,
        # The opening question is written in code, not generated: it is the
        # same every time, and spending a model call to say hello would make
        # starting an interview slower for no gain.
        transcript=[{"role": "assistant", "content": opening}],
    )
    db.add(interview)
    await db.commit()
    await db.refresh(interview)
    return as_dict(interview)


async def reply(db: AsyncSession, user_id: int, interview_id: int, answer: str) -> dict:
    interview = await _owned(db, user_id, interview_id)

    if interview.status != OPEN:
        raise InterviewError("This interview has already finished")

    answer = (answer or "").strip()
    if not answer:
        raise InterviewError("Say something first")

    transcript = list(interview.transcript or [])
    transcript.append({"role": "user", "content": answer[:4000]})

    problem = {
        "name": interview.problem_name,
        "topic": interview.topic,
        "url": interview.problem_url,
    }
    question = await interview_agent.next_question(problem, transcript)
    transcript.append({"role": "assistant", "content": question})

    interview.transcript = transcript

    # Closed on length rather than left to run: past this the transcript stops
    # fitting in a prompt, and an interview with no end never gets its
    # assessment written.
    if interview_agent.is_over(transcript):
        interview.status = FINISHED
        interview.ended_at = _now()
        interview.findings = await interview_agent.summarise(problem, transcript)

    await db.commit()
    await db.refresh(interview)
    return as_dict(interview)


async def finish(db: AsyncSession, user_id: int, interview_id: int) -> dict:
    """End it early and write the assessment."""
    interview = await _owned(db, user_id, interview_id)

    if interview.status == FINISHED:
        return as_dict(interview)

    problem = {
        "name": interview.problem_name,
        "topic": interview.topic,
        "url": interview.problem_url,
    }
    interview.findings = await interview_agent.summarise(
        problem, list(interview.transcript or [])
    )
    interview.status = FINISHED
    interview.ended_at = _now()

    await db.commit()
    await db.refresh(interview)
    return as_dict(interview)


async def get(db: AsyncSession, user_id: int, interview_id: int) -> dict:
    return as_dict(await _owned(db, user_id, interview_id))


async def recent(db: AsyncSession, user_id: int, limit: int = 10) -> dict:
    rows = (
        await db.execute(
            select(Interview)
            .where(Interview.user_id == user_id)
            .order_by(Interview.id.desc())
            .limit(limit)
        )
    ).scalars().all()
    return {"interviews": [as_dict(r) for r in rows]}
