from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def create_access_token(subject: str, token_version: int = 0) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    # `tv` travels with the token so it can be checked against the user row.
    # A JWT cannot be withdrawn once issued; comparing a counter is the
    # cheapest way to make one stop being accepted early.
    payload = {"sub": subject, "exp": expire, "tv": token_version}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> tuple[str, int]:
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    # Tokens minted before `tv` existed have no claim; treat them as version 0,
    # which is the value every existing user row starts at.
    return payload["sub"], int(payload.get("tv", 0))
