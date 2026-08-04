import logging
import smtplib

import pytest

from app.clients import email_client
from app.core.config import settings


@pytest.fixture
def unconfigured(monkeypatch):
    monkeypatch.setattr(settings, "smtp_host", None)


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(settings, "smtp_port", 587)
    monkeypatch.setattr(settings, "smtp_user", "someone")
    monkeypatch.setattr(settings, "smtp_password", "secret")


@pytest.mark.asyncio
async def test_without_smtp_the_message_is_logged_not_sent(unconfigured, caplog):
    with caplog.at_level(logging.WARNING, logger="solvix.mail"):
        await email_client.send_mail("to@example.com", "Subject", "Body line")

    output = caplog.text
    assert "to@example.com" in output
    assert "Body line" in output
    # It has to be obvious in the log that nothing actually went out.
    assert "not sent" in output


@pytest.mark.asyncio
async def test_a_logged_message_never_touches_smtp(unconfigured, monkeypatch):
    def explode(*args, **kwargs):
        raise AssertionError("SMTP was contacted with no host configured")

    monkeypatch.setattr(smtplib, "SMTP", explode)

    await email_client.send_mail("to@example.com", "Subject", "Body")


@pytest.mark.asyncio
async def test_a_configured_host_gets_a_properly_addressed_message(
    configured, monkeypatch
):
    sent = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout=None):
            sent["host"] = host
            sent["port"] = port

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def starttls(self):
            sent["tls"] = True

        def login(self, user, password):
            sent["login"] = (user, password)

        def send_message(self, message):
            sent["to"] = message["To"]
            sent["subject"] = message["Subject"]
            sent["body"] = message.get_content()

    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)

    await email_client.send_mail("to@example.com", "Your code", "It is 123456")

    assert sent["host"] == "smtp.example.com"
    assert sent["to"] == "to@example.com"
    assert sent["subject"] == "Your code"
    assert "123456" in sent["body"]
    assert sent["tls"] is True
    assert sent["login"] == ("someone", "secret")


@pytest.mark.asyncio
async def test_an_smtp_failure_surfaces_as_a_mail_error(configured, monkeypatch):
    # The caller has to be able to tell "sent" from "not sent"; a bare
    # SMTPException leaking out would be handled as a 500 instead.
    def explode(*args, **kwargs):
        raise smtplib.SMTPConnectError(421, "nope")

    monkeypatch.setattr(smtplib, "SMTP", explode)

    with pytest.raises(email_client.MailError):
        await email_client.send_mail("to@example.com", "Subject", "Body")


@pytest.mark.asyncio
async def test_an_unreachable_host_also_surfaces_as_a_mail_error(
    configured, monkeypatch
):
    def explode(*args, **kwargs):
        raise OSError("no route to host")

    monkeypatch.setattr(smtplib, "SMTP", explode)

    with pytest.raises(email_client.MailError):
        await email_client.send_mail("to@example.com", "Subject", "Body")
