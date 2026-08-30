"""The one unauthenticated write path in the app.

`POST /jobs/daily-reminders` imports from both platforms and emails every
account that has something due. It has no user token because no user is
present, so a shared secret is the whole of its protection — and until these
tests it had none of its own.
"""

import pytest
from fastapi import HTTPException

from app.api.jobs import require_cron_key
from app.core.config import settings

KEY = "s3cret-key"


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setattr(settings, "cron_key", KEY)


async def refused(header):
    with pytest.raises(HTTPException) as caught:
        await require_cron_key(header)
    assert caught.value.status_code == 401
    return caught.value


async def test_the_right_key_is_accepted(configured):
    assert await require_cron_key(KEY) is None


async def test_a_wrong_key_is_refused(configured):
    await refused("wrong")


async def test_a_missing_header_is_refused(configured):
    await refused(None)


async def test_an_empty_header_is_refused(configured):
    await refused("")


async def test_a_prefix_of_the_key_is_refused(configured):
    # Guards the comparison itself: a truncated key must not pass.
    await refused(KEY[:-1])


async def test_the_key_with_extra_appended_is_refused(configured):
    await refused(KEY + "x")


async def test_an_unconfigured_deploy_fails_closed(monkeypatch):
    """The case that matters most, and the one that was never checked.

    With no key set the endpoint must refuse everything rather than becoming
    open to the internet. Fail closed, not open.
    """
    monkeypatch.setattr(settings, "cron_key", None)
    await refused(None)
    await refused("anything")
    # Notably including an empty header matching an empty key.
    await refused("")


async def test_an_empty_string_key_also_fails_closed(monkeypatch):
    """`CRON_KEY=` in an env file gives "" rather than None."""
    monkeypatch.setattr(settings, "cron_key", "")
    await refused("")
    await refused(None)
