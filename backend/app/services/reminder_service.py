"""Spaced-repetition revision reminders.

Two kinds, from the same data the rest of Solvix already ingests:

- **problem** — you solved something a few days ago, and the spacing effect says
  now is when revisiting it pays. Time-sensitive, so these win the cap.
- **topic** — a tag that is both weak and stale. Not urgent on any given day,
  so problems lead — but a share of the cap is held back for them, because a
  reminder that can be crowded out every single day does not exist.

Generation is deliberately separate from delivery. Today the dashboard reads
these rows; an email sender later is another reader, not a rewrite.
"""

from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.clients.codeforces_client import CodeforcesError
from app.clients.leetcode_client import LeetCodeError
from app.db.models import Reminder, Revision, Submission
from app.services import problem_service, revision_schedule, topic_service

ACCEPTED = "OK"
PLATFORMS = ("codeforces", "leetcode")

# Revisit intervals live in revision_schedule; the first one is 3 days.
# A topic must be untouched this long before it is worth nagging about.
STALE_THRESHOLD_DAYS = 14
# And weak enough to be worth the slot.
WEAK_THRESHOLD = 0.35
# Cap per run, so a long-inactive account is not flooded at once.
#
# Three rather than five, set against what this user actually does: about 2.4
# problems a day, on top of a plan that already asks for 120 minutes. Five
# revisions was asking for close to two and a half hours combined, and the
# failure mode of an over-long list is not doing less of it — it is skipping
# the whole thing on sight.
#
# Nothing is lost by showing fewer: anything due that does not fit keeps its
# date and returns tomorrow. The cap governs presentation, not the schedule.
MAX_PER_RUN = 3
# ...of which this many are held for topics, so a steady stream of due problems
# cannot crowd them out entirely. One, because a stale tag is equally stale
# tomorrow — one a day still surfaces every one of them within a week.
TOPIC_SLOTS = 1

# Problems offered under a stale topic. Two, because each one costs the email
# two lines — a name and a link — and the point is to remove the excuse not to
# start, not to hand over a reading list.
SUGGESTIONS_PER_TOPIC = 2


def describe_problem(name: str, days: int) -> str:
    if days == 1:
        return "solved yesterday"
    if days < 14:
        return f"solved {days} days ago"
    if days < 60:
        return f"solved {round(days / 7)} weeks ago"
    return f"solved {round(days / 30)} months ago"


def describe_topic(days_since: int | None, accuracy: float | None) -> str:
    if days_since is None:
        staleness = "never solved"
    elif days_since >= 365:
        staleness = "not practised in over a year"
    elif days_since >= 60:
        staleness = f"not practised in {round(days_since / 30)} months"
    else:
        staleness = f"not practised in {round(days_since / 7)} weeks"

    if accuracy is not None and accuracy < 0.5:
        return f"{staleness}, and only {round(accuracy * 100)}% of attempts pass"
    return staleness


def select_reminders(
    problems: list[dict], topics: list[dict], cap: int = MAX_PER_RUN
) -> list[dict]:
    """Merge both kinds into one capped list, with a slot reserved for topics.

    Problems still come first — their window is a specific few days, while a
    stale topic is equally stale tomorrow. But once the spacing ladder matured,
    enough problems fell due every morning to fill the cap outright, so topics
    silently stopped appearing at all. A reminder that can be crowded out
    permanently is a reminder that does not exist.

    So each kind is guaranteed a share, and whatever the other kind cannot fill
    is given back rather than wasted: a day with nothing stale shows problems
    in every slot, and a day with one problem due fills the rest with topics.
    """
    topic_slots = min(len(topics), max(cap - len(problems), TOPIC_SLOTS))
    problem_slots = cap - min(topic_slots, TOPIC_SLOTS if topics else 0)
    return problems[:problem_slots] + topics[:topic_slots]


def topic_is_due(topic: dict) -> bool:
    """Weak *and* stale — either alone is not a reminder.

    When a platform records no failed attempts there is no pass rate, so the
    weakness score is recency restated. Applying the weakness bar on top of the
    staleness bar would then just be the staleness test twice, at a stricter
    cutoff than the configured one — a LeetCode topic untouched for three weeks
    would score 0.23 and never fire. For those topics staleness alone decides.
    """
    days = topic["days_since_last_solve"]
    stale = days is None or days >= STALE_THRESHOLD_DAYS
    if not stale:
        return False
    if topic["accuracy"] is None:
        return True
    return topic["weakness"] >= WEAK_THRESHOLD


async def _record_new_solves(db: AsyncSession, user_id: int, today: date) -> None:
    """Give every solved problem a schedule, once.

    Problems solved before this feature existed slot in at the first interval
    still ahead of them, and anything past the whole ladder is retired rather
    than dumped into today's queue.
    """
    first_solves = (
        select(
            Submission.external_problem_id.label("pid"),
            Submission.platform.label("platform"),
            func.min(Submission.problem_name).label("problem_name"),
            func.min(Submission.solved_at).label("first_solved_at"),
        )
        .where(Submission.user_id == user_id, Submission.verdict == ACCEPTED)
        .group_by(Submission.external_problem_id, Submission.platform)
        .subquery()
    )

    known = select(Revision.platform, Revision.external_problem_id).where(
        Revision.user_id == user_id
    )
    known_pairs = {(r.platform, r.external_problem_id) for r in (await db.execute(known)).all()}

    rows = (await db.execute(select(first_solves))).all()
    for row in rows:
        if (row.platform, row.pid) in known_pairs or row.first_solved_at is None:
            continue
        placed = revision_schedule.schedule_for_existing(
            row.first_solved_at.date(), today
        )
        step, due = placed if placed else (len(revision_schedule.INTERVALS) - 1, None)
        db.add(
            Revision(
                user_id=user_id,
                platform=row.platform,
                external_problem_id=row.pid,
                problem_name=row.problem_name,
                first_solved_at=row.first_solved_at,
                step=step,
                due_on=due,
            )
        )
    await db.flush()


async def _revisit_outcome(
    db: AsyncSession, user_id: int, revision: Revision, today: date
) -> str:
    """How the last revisit went, according to the platform's own record.

    Only asked about problems the app can actually see failures for. Anywhere
    else the answer would be "clean" by construction, which is a guess wearing
    a fact's clothes.
    """
    if revision.platform not in topic_service.PLATFORMS_WITH_FAILURES:
        return revision_schedule.CLEAN

    since = revision.last_reminded_on or revision.first_solved_at.date()
    attempts = (
        await db.execute(
            select(Submission.verdict)
            .where(
                Submission.user_id == user_id,
                Submission.platform == revision.platform,
                Submission.external_problem_id == revision.external_problem_id,
                Submission.solved_at >= datetime.combine(since, datetime.min.time()),
            )
            .order_by(Submission.solved_at)
        )
    ).scalars().all()

    return revision_schedule.outcome_for_platform(
        revision.platform, list(attempts), can_see_failures=True
    )


async def _problems_to_revisit(
    db: AsyncSession, user_id: int, today: date
) -> tuple[list[dict], list[Revision]]:
    """Problems whose revision is due, oldest first."""
    await _record_new_solves(db, user_id, today)

    due = (
        await db.execute(
            select(Revision)
            .where(
                Revision.user_id == user_id,
                Revision.due_on.isnot(None),
                Revision.due_on <= today,
            )
            .order_by(Revision.due_on, Revision.id)
            .limit(MAX_PER_RUN)
        )
    ).scalars().all()

    items = [
        {
            "kind": "problem",
            "platform": r.platform,
            "subject": f"{r.platform}:{r.external_problem_id}",
            "title": r.problem_name or r.external_problem_id,
            "reason": describe_problem(
                r.problem_name or r.external_problem_id,
                (today - r.first_solved_at.date()).days,
            ),
            # Telling someone to revisit a problem without linking to it leaves
            # them to go and find it themselves, which is the moment a reminder
            # gets ignored.
            "url": problem_service.problem_url(r.platform, r.external_problem_id),
        }
        for r in due
    ]
    return items, list(due)


async def _attach_suggestions(
    db: AsyncSession, user_id: int, selected: list[dict]
) -> None:
    """Give each stale-topic reminder something to actually click.

    Naming a gap without offering a way in leaves the reader to go hunting,
    which is friction at exactly the moment they were already reluctant.

    Attached after the cap rather than before it, so this costs one catalogue
    lookup for the topic that is being sent rather than one for every topic
    that happened to be due.

    Only the returned list is enriched, not the stored rows: a suggestion is
    the freshest thing in the message and there is no reason to freeze today's
    catalogue into the database. And it is best-effort — the catalogue is a
    third-party call, and a stale topic is still worth naming without it.
    """
    for item in selected:
        if item["kind"] != "topic":
            continue
        try:
            found = await problem_service.unsolved_in_topic(
                db,
                user_id,
                item["subject"],
                item["platform"],
                limit=SUGGESTIONS_PER_TOPIC,
            )
        except (CodeforcesError, LeetCodeError):
            continue
        if found["problems"]:
            item["suggestions"] = found["problems"]


async def run_reminders(db: AsyncSession, user_id: int) -> dict:
    """Generate today's reminders and persist them."""
    today = clock.today()

    problems, due_revisions = await _problems_to_revisit(db, user_id, today)

    # Scored per platform rather than pooled, so every reminder knows which
    # platform it came from. Without that, a dashboard filtered to Codeforces
    # would still be shown LeetCode topics.
    topics = []
    for platform in PLATFORMS:
        scored = (
            await topic_service.get_weak_topics(db, user_id, platform=platform)
        )["topics"]
        topics.extend(
            {
                "kind": "topic",
                "platform": platform,
                "subject": t["tag"],
                "title": t["tag"],
                "reason": describe_topic(t["days_since_last_solve"], t["accuracy"]),
            }
            for t in scored
            if topic_is_due(t)
        )

    selected = select_reminders(problems, topics)
    await _attach_suggestions(db, user_id, selected)

    for item in selected:
        stmt = insert(Reminder).values(
            user_id=user_id,
            run_date=today,
            kind=item["kind"],
            platform=item["platform"],
            subject=item["subject"],
            title=item["title"],
            reason=item["reason"],
        )
        # Re-running on the same day refreshes nothing and duplicates nothing.
        await db.execute(
            stmt.on_conflict_do_nothing(
                index_elements=["user_id", "run_date", "kind", "platform", "subject"]
            )
        )

    # Advance only what actually made it past the cap. A problem that was due
    # but dropped keeps its date and comes back tomorrow, rather than silently
    # sliding to the next interval without ever being shown.
    shown = {item["subject"] for item in selected if item["kind"] == "problem"}
    for revision in due_revisions:
        if f"{revision.platform}:{revision.external_problem_id}" not in shown:
            continue
        outcome = await _revisit_outcome(db, user_id, revision, today)
        nxt = revision_schedule.next_schedule(revision.step, outcome, today)
        revision.last_reminded_on = today
        if nxt is None:
            # Recalled through the whole ladder; stop scheduling it.
            revision.due_on = None
        else:
            revision.step, revision.due_on = nxt

    await db.commit()

    return {
        "run_date": today,
        "generated": len(selected),
        "reminders": selected,
    }


def _reminder_url(kind: str, platform: str, subject: str) -> str | None:
    """The problem a stored reminder points at, from its "platform:id" subject."""
    if kind != "problem":
        return None
    _, _, external_id = subject.partition(":")
    return problem_service.problem_url(platform, external_id) if external_id else None


async def list_reminders(
    db: AsyncSession, user_id: int, platform: str | None = None
) -> dict:
    """Today's stored reminders, generating them on first read of the day."""
    today = clock.today()

    stored = (
        await db.execute(
            select(Reminder)
            .where(Reminder.user_id == user_id, Reminder.run_date == today)
            .order_by(Reminder.id)
        )
    ).scalars().all()

    if not stored:
        generated = await run_reminders(db, user_id)
        items = generated["reminders"]
    else:
        items = [
            {
                "kind": r.kind,
                "platform": r.platform,
                "subject": r.subject,
                "title": r.title,
                "reason": r.reason,
                # Rebuilt from the subject rather than stored: the link is
                # derived from the id, so a second copy could only ever drift.
                "url": _reminder_url(r.kind, r.platform, r.subject),
            }
            for r in stored
        ]

    # Filtering happens on read, not on generation: the run stays a single
    # capped batch, and switching the dashboard filter never regenerates it.
    if platform:
        items = [i for i in items if i["platform"] == platform]

    return {"run_date": today, "generated": len(items), "reminders": items}
