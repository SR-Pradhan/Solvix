"""When to revisit a solved problem, and what to do with what happened next.

The gaps widen because each successful recall makes the next one last longer.
A single reminder three days after solving — which is what this replaces — is a
delayed nudge, not spaced repetition.

Everything here is a pure function over dates and verdicts. The scheduling
rules are the part worth testing, and none of them need a database.
"""

from __future__ import annotations

from datetime import date, timedelta

# Days after the previous event, roughly doubling. After the last one a problem
# is considered learned and stops being scheduled: reminding someone forever
# about a problem they have recalled five times is noise, and noise is what
# makes people stop reading reminders.
INTERVALS = (3, 7, 14, 30, 60)

# Outcomes of a revisit, in the order they are worth reacting to.
CLEAN = "clean"
STRUGGLED = "struggled"
UNSEEN = "unseen"


def classify_attempts(verdicts: list[str]) -> str:
    """What the platform's own record says about a revisit.

    Nobody is asked how it went — this reads the submissions that already
    exist. It is only meaningful where failed attempts are recorded at all;
    see `outcome_for_platform`.
    """
    if not verdicts:
        return UNSEEN
    # Chronological, so the first entry is the first thing tried. Getting there
    # eventually is not the same as recalling it — what matters is whether the
    # first attempt worked.
    return CLEAN if verdicts[0] == "OK" else STRUGGLED


def outcome_for_platform(platform: str, verdicts: list[str], can_see_failures: bool) -> str:
    """Grade a revisit only where the evidence exists.

    LeetCode records passes and nothing else, so "no failures found" there
    means "no failures are recordable", not "it went well". Grading it would
    invent a signal, so those problems simply advance on schedule — the same
    rule the rest of the project follows when one platform knows less than the
    other.
    """
    if not can_see_failures:
        return CLEAN
    return classify_attempts(verdicts)


def first_due(solved_on: date) -> date:
    return solved_on + timedelta(days=INTERVALS[0])


def next_schedule(step: int, outcome: str, today: date) -> tuple[int, date] | None:
    """The step and due date after a reminder was sent. None means retired.

    - clean     → widen the gap
    - struggled → back to the first interval; pushing a failed recall out to a
                  longer gap guarantees it fails again and teaches nothing
    - unseen    → hold the step and ask again after the same gap, because
                  nothing was learned about it either way
    """
    if outcome == STRUGGLED:
        return 0, today + timedelta(days=INTERVALS[0])

    if outcome == UNSEEN:
        return step, today + timedelta(days=INTERVALS[min(step, len(INTERVALS) - 1)])

    nxt = step + 1
    if nxt >= len(INTERVALS):
        return None
    return nxt, today + timedelta(days=INTERVALS[nxt])


def schedule_for_existing(solved_on: date, today: date) -> tuple[int, date] | None:
    """Where a problem solved before this feature existed should slot in.

    Its earlier intervals have already passed unobserved, so it starts at the
    first one still in the future. A problem older than the whole ladder is
    retired rather than dumped into today's queue — it is either learned or
    long forgotten, and neither is a revision reminder's job.
    """
    for step, days in enumerate(INTERVALS):
        due = solved_on + timedelta(days=days)
        if due >= today:
            return step, due
    return None
