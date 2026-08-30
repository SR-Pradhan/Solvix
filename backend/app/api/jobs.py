"""Endpoints a scheduler calls, not a person.

Solvix has no in-process scheduler on purpose: the API sleeps when idle, so
anything that must happen at a fixed time has to be started from outside. A
GitHub Actions workflow holds the clock and calls this; the decisions stay
here, so swapping the scheduler changes nothing about what a reminder is.
"""

import logging
from datetime import date

import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.clients.email_client import MailError, send_mail
from app.core.config import settings
from app.db.database import get_db
from app.db.models import User
from app.services import (
    leetcode_profile_service,
    problem_service,
    reminder_mail,
    reminder_service,
)
from app.services.ingestion_service import ingest_codeforces_submissions
from app.services.leetcode_ingestion_service import ingest_leetcode_submissions

# Two per topic. The email is a nudge, not a curriculum: a list long enough to
# scroll is a list you postpone.
SUGGESTIONS_PER_TOPIC = 2

log = logging.getLogger("solvix.jobs")

router = APIRouter(prefix="/jobs", tags=["jobs"])


async def require_cron_key(x_cron_key: str | None = Header(default=None)) -> None:
    """A shared secret, because there is no user to authenticate.

    Refusing when unset is deliberate: a misconfigured deploy should fail
    closed, not quietly expose a job that sends mail to every account.
    """
    # compare_digest rather than ==, which returns as soon as two characters
    # differ and so leaks the key's prefix through timing. The endpoint is
    # unauthenticated and reachable by anyone, which is exactly the setting
    # where that is worth caring about.
    if not settings.cron_key or not secrets.compare_digest(
        x_cron_key or "", settings.cron_key
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid job key"
        )


async def _refresh(db: AsyncSession, user: User) -> dict:
    """Pull down whatever the user has solved since the last run.

    Reminders are only as good as the data behind them, and until this existed
    the only thing that imported anything was a button on the dashboard — so a
    week without visiting meant a week of reminders built on week-old facts,
    while the app claimed to need no manual work.

    Each source is attempted independently. One platform being down, rate
    limited or misconfigured must not cost the other, and none of them may cost
    the reminder: stale data still produces a useful email, an exception
    produces nothing.
    """
    imported: dict[str, int | str] = {}

    if user.codeforces_handle:
        try:
            imported["codeforces"] = await ingest_codeforces_submissions(
                db, user_id=user.id, handle=user.codeforces_handle
            )
        except Exception as exc:
            imported["codeforces"] = f"failed: {type(exc).__name__}"
            log.warning("codeforces sync failed for user %s", user.id)

    if user.leetcode_repo:
        try:
            imported["leetcode"] = await ingest_leetcode_submissions(
                db, user_id=user.id, repo=user.leetcode_repo
            )
        except Exception as exc:
            imported["leetcode"] = f"failed: {type(exc).__name__}"
            log.warning("leetcode sync failed for user %s", user.id)

    if user.leetcode_username:
        try:
            # Also the cheapest way to catch solves LeetHub has not pushed yet:
            # this pulls the twenty most recent accepted submissions.
            await leetcode_profile_service.sync_profile(
                db, user.id, user.leetcode_username
            )
            imported["profile"] = "synced"
        except Exception as exc:
            imported["profile"] = f"failed: {type(exc).__name__}"
            log.warning("leetcode profile sync failed for user %s", user.id)

    return imported


@router.post("/daily-reminders", dependencies=[Depends(require_cron_key)])
async def daily_reminders(
    deliver: bool = True, db: AsyncSession = Depends(get_db)
):
    """Generate today's reminders for every account, and email them.

    `deliver=false` composes the messages and hands them back instead of
    sending. That exists because the host's free tier blocks outbound SMTP
    entirely, so the scheduler — which can reach a mail provider — does the
    delivering. Composition stays here either way: the wording is the part
    worth testing, and it should not drift into a workflow tool.

    One account's failure must not end the run — a bounced address would
    otherwise silently cancel everybody else's reminders — so each is caught
    and counted.
    """
    today = clock.today()
    users = (await db.execute(select(User).order_by(User.id))).scalars().all()

    processed = 0
    emailed = 0
    failures = 0
    # Reported back to the caller, not just logged. Only the holder of the job
    # key can read this, and a scheduled job that answers "1 failure" without
    # saying why forces a log hunt for something the run already knew.
    errors: list[str] = []
    messages: list[dict] = []
    synced: dict[int, dict] = {}

    for user in users:
        try:
            # Import before deciding: a reminder built on last week's data can
            # tell you to revisit something you did yesterday.
            synced[user.id] = await _refresh(db, user)

            generated = await reminder_service.run_reminders(db, user.id)
            processed += 1

            reminders = generated["reminders"]
            # No mail when there is nothing due. A daily email that often says
            # "nothing today" trains the reader to ignore the ones that matter.
            if not reminders:
                continue

            message = {
                "to": user.email,
                "subject": reminder_mail.subject_line(reminders, today),
                "body": reminder_mail.body(reminders, today, settings.app_url),
            }

            if not deliver:
                messages.append(message)
                continue

            await send_mail(**message)
            emailed += 1
        except MailError as exc:
            # The reminders are already stored, so the dashboard still shows
            # them; only the delivery was lost. The useful part is always the
            # mail server's own complaint, which is the chained cause.
            failures += 1
            reason = str(exc.__cause__ or exc)
            errors.append(f"user {user.id}: {reason}")
            log.exception("reminder mail failed for user %s", user.id)
        except Exception as exc:
            failures += 1
            errors.append(f"user {user.id}: {type(exc).__name__}: {exc}")
            log.exception("reminder run failed for user %s", user.id)

    return {
        "run_date": today,
        "users": processed,
        "emailed": emailed,
        "failures": failures,
        # Says out loud when mail is going to the log instead of an inbox,
        # which is otherwise indistinguishable from a successful run.
        "mail_configured": settings.mail_configured,
        "synced": synced,
        "errors": errors,
        # Empty unless deliver=false. The scheduler sends these itself.
        "messages": messages,
    }
