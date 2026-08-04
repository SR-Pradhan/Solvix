"""Rules for moving an account to a new email address.

The flow is deliberately three-legged:

1. the current password proves the person at the keyboard owns the account,
2. a code sent to the new address proves they can read mail there,
3. a notice to the old address means a silent takeover is impossible.

Everything below is pure. The endpoint owns the database and the mail client;
this module only decides what is allowed, generates the code and writes the
message text, which is what lets the whole flow be tested without either.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta

CODE_LENGTH = 6
CODE_TTL_MINUTES = 10
# Five guesses against a six-digit code leaves a 1-in-200,000 chance, and the
# code dies in ten minutes regardless.
MAX_ATTEMPTS = 5
# Long enough to stop a request loop being used to spam an address, short
# enough that a code lost to a spam folder is not a five-minute wait.
RESEND_COOLDOWN_SECONDS = 60


class EmailChangeError(ValueError):
    """A rule the user broke, phrased for them rather than for a log."""


def normalise_email(value: str) -> str:
    """Lowercase and trim, so Foo@Example.com and foo@example.com are one address."""
    cleaned = value.strip().lower()
    if not cleaned:
        raise EmailChangeError("Enter an email address")
    return cleaned


def validate_target(new_email: str, current_email: str, taken: bool) -> str:
    """Check the destination address before anything is sent to it."""
    target = normalise_email(new_email)

    if target == normalise_email(current_email):
        raise EmailChangeError("That is already your email address")
    if taken:
        # Deliberately the same wording registration uses. Saying "that
        # account exists" here would let a logged-in user probe for members.
        raise EmailChangeError("That email address cannot be used")
    return target


def generate_code() -> str:
    """A six-digit code, zero-padded so every code is the same length.

    `secrets` rather than `random`: this is a credential, and the difference
    is whether the sequence is predictable from earlier codes.
    """
    return f"{secrets.randbelow(10**CODE_LENGTH):0{CODE_LENGTH}d}"


def expiry_for(now: datetime) -> datetime:
    return now + timedelta(minutes=CODE_TTL_MINUTES)


def check_usable(
    expires_at: datetime,
    attempts: int,
    consumed_at: datetime | None,
    now: datetime,
) -> None:
    """Decide whether a stored request may still be verified against.

    Raises rather than returning a flag so no caller can forget to look.
    """
    if consumed_at is not None:
        raise EmailChangeError("That code has already been used")
    if attempts >= MAX_ATTEMPTS:
        raise EmailChangeError("Too many incorrect codes. Start again.")
    if now >= expires_at:
        raise EmailChangeError("That code has expired. Start again.")


def seconds_until_resend(last_sent_at: datetime, now: datetime) -> int:
    """Zero when a new code may be sent, otherwise the wait in seconds."""
    elapsed = (now - last_sent_at).total_seconds()
    return max(0, int(RESEND_COOLDOWN_SECONDS - elapsed))


def verification_message(code: str, display_name: str | None) -> tuple[str, str]:
    """Subject and body for the code sent to the new address."""
    greeting = f"Hi {display_name}," if display_name else "Hi,"

    body = (
        f"{greeting}\n\n"
        f"Your Solvix verification code is {code}\n\n"
        f"Enter it in Solvix to finish moving your account to this address. "
        f"It expires in {CODE_TTL_MINUTES} minutes.\n\n"
        "If you did not ask to change your email address, you can ignore this "
        "message. Nothing has changed yet.\n"
    )
    return "Your Solvix verification code", body


def notice_message(new_email: str, display_name: str | None) -> tuple[str, str]:
    """Subject and body for the warning sent to the address being left.

    This is the part that makes a stolen session survivable: the real owner
    hears about the change at an address the attacker does not control.
    """
    greeting = f"Hi {display_name}," if display_name else "Hi,"

    body = (
        f"{greeting}\n\n"
        f"Someone asked to move your Solvix account to {new_email}.\n\n"
        "If that was you, no action is needed. If it was not, change your "
        "Solvix password now, because whoever asked is signed in to your "
        "account.\n"
    )
    return "A change was requested on your Solvix account", body
