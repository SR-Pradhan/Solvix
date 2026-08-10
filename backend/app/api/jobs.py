"""Endpoints a scheduler calls, not a person.

Solvix has no in-process scheduler on purpose: the API sleeps when idle, so
anything that must happen at a fixed time has to be started from outside. n8n
holds the clock and calls this; the decisions stay here, which means swapping
the scheduler later changes nothing about what a reminder is.
"""

import logging
from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.email_client import MailError, send_mail
from app.core.config import settings
from app.db.database import get_db
from app.db.models import User
from app.services import reminder_mail, reminder_service

log = logging.getLogger("solvix.jobs")

router = APIRouter(prefix="/jobs", tags=["jobs"])


async def require_cron_key(x_cron_key: str | None = Header(default=None)) -> None:
    """A shared secret, because there is no user to authenticate.

    Refusing when unset is deliberate: a misconfigured deploy should fail
    closed, not quietly expose a job that sends mail to every account.
    """
    if not settings.cron_key or x_cron_key != settings.cron_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid job key"
        )


@router.post("/daily-reminders", dependencies=[Depends(require_cron_key)])
async def daily_reminders(db: AsyncSession = Depends(get_db)):
    """Generate today's reminders for every account and email them.

    One account's failure must not end the run — a bounced address would
    otherwise silently cancel everybody else's reminders — so each is caught
    and counted.
    """
    today = date.today()
    users = (await db.execute(select(User).order_by(User.id))).scalars().all()

    processed = 0
    emailed = 0
    failures = 0
    # Reported back to the caller, not just logged. Only the holder of the job
    # key can read this, and a scheduled job that answers "1 failure" without
    # saying why forces a log hunt for something the run already knew.
    errors: list[str] = []

    for user in users:
        try:
            generated = await reminder_service.run_reminders(db, user.id)
            processed += 1

            reminders = generated["reminders"]
            # No mail when there is nothing due. A daily email that often says
            # "nothing today" trains the reader to ignore the ones that matter.
            if not reminders:
                continue

            await send_mail(
                to=user.email,
                subject=reminder_mail.subject_line(reminders, today),
                body=reminder_mail.body(reminders, today, settings.app_url),
            )
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
        "errors": errors,
    }
