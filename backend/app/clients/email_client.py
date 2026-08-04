"""Outbound mail.

Two backends, chosen by whether SMTP is configured:

- configured   -> a real message over SMTP
- not          -> the message is written to the server log

The console fallback is not a stub. It means email verification is fully
usable in development with no account, no API key and no network, and it is
the same code path in both cases, so nothing is left untested until deploy
day. `python-jose`-style optional config, same as the Groq key.

smtplib is synchronous and would block the event loop for as long as the
handshake takes, so the send runs in a worker thread.
"""

from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

log = logging.getLogger("solvix.mail")


class MailError(RuntimeError):
    """The message could not be handed to the mail server."""


async def send_mail(to: str, subject: str, body: str) -> None:
    if not settings.mail_configured:
        _log_instead(to, subject, body)
        return

    message = EmailMessage()
    message["From"] = settings.mail_from
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    try:
        await asyncio.to_thread(_deliver, message)
    except (smtplib.SMTPException, OSError) as exc:
        # The caller decides what a failure means; a verification code that
        # never arrives has to surface, while a reminder can be dropped.
        raise MailError(f"Could not send mail to {to}") from exc


def _deliver(message: EmailMessage) -> None:
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
        if settings.smtp_starttls:
            server.starttls()
        if settings.smtp_user:
            server.login(settings.smtp_user, settings.smtp_password or "")
        server.send_message(message)


def _log_instead(to: str, subject: str, body: str) -> None:
    log.warning(
        "SMTP is not configured, so this mail was not sent:\n"
        "  To:      %s\n"
        "  Subject: %s\n"
        "%s",
        to,
        subject,
        "\n".join(f"  | {line}" for line in body.splitlines()),
    )
