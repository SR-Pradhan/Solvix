import pytest
from jose import jwt

from app.core.config import settings
from app.core.security import create_access_token, decode_access_token


def test_token_carries_its_version():
    token = create_access_token(subject="7", token_version=3)
    subject, version = decode_access_token(token)
    assert (subject, version) == ("7", 3)


def test_token_without_a_version_reads_as_zero():
    # Tokens minted before the claim existed must not lock their owner out;
    # every user row starts at 0, so they still match.
    legacy = jwt.encode(
        {"sub": "7", "exp": 99999999999},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    assert decode_access_token(legacy) == ("7", 0)


def test_a_tampered_token_is_rejected():
    token = create_access_token(subject="7", token_version=0)
    forged = token[:-3] + ("aaa" if not token.endswith("aaa") else "bbb")
    with pytest.raises(Exception):
        decode_access_token(forged)
