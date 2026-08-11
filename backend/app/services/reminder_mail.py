"""Turning a day's reminders into an email.

Composing the message is a pure function over the reminder rows, so what lands
in someone's inbox can be asserted in a test rather than checked by sending
mail to yourself.
"""

from __future__ import annotations

from datetime import date

MAX_LISTED = 5


def subject_line(reminders: list[dict], today: date) -> str:
    """Says what is inside, because that is what decides whether it is opened.

    "Your Solvix reminders" tells the reader nothing they cannot guess, and a
    daily email that reveals nothing in the subject gets filtered within a
    week.
    """
    problems = sum(1 for r in reminders if r["kind"] == "problem")
    topics = len(reminders) - problems

    parts = []
    if problems:
        parts.append(f"{problems} problem{'s' if problems > 1 else ''} to revisit")
    if topics:
        parts.append(f"{topics} topic{'s' if topics > 1 else ''} going stale")
    return f"Solvix — {' and '.join(parts)}" if parts else "Solvix — nothing due today"


def body(reminders: list[dict], today: date, app_url: str) -> str:
    """Plain text, not HTML.

    The content is a short list with links; HTML would add a second version of
    every message to keep in step for no gain, and plain text renders the same
    everywhere.
    """
    problems = [r for r in reminders if r["kind"] == "problem"]
    topics = [r for r in reminders if r["kind"] == "topic"]

    lines = [f"Your practice for {today:%A %-d %B}.", ""]

    if problems:
        # Headed by count, because five problems arriving at once looks
        # arbitrary until you know they are spaced revisits rather than a
        # backlog.
        lines.append(f"Revisit ({len(problems)}) — spaced from when you solved them:")
        for r in problems:
            # The link matters more than the name: a reminder you have to go
            # and search for is a reminder you skip.
            suffix = f"\n    {r['url']}" if r.get("url") else ""
            lines.append(f"  - {r['title']} — {r['reason']}{suffix}")
        lines.append("")

    if topics:
        lines.append(f"Going stale ({len(topics)}) — no practice in a while:")
        for r in topics:
            lines.append(f"  - {r['title']} — {r['reason']}")
        lines.append("")

    lines.append(f"Open Solvix: {app_url}")
    return "\n".join(lines)
