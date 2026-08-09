from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.db.database import get_db
from app.db.models import User
from app.schemas.user import Token, UserLogin, UserOut, UserRegister
from app.services.rate_limit import RateLimiter, client_key

router = APIRouter(prefix="/auth", tags=["auth"])

# Guessing a password is only cheap if you get unlimited guesses. Five wrong
# answers in five minutes buys a fifteen-minute pause, which costs an honest
# typist almost nothing and makes an online dictionary attack pointless.
login_limiter = RateLimiter(max_failures=5, window=timedelta(minutes=5), block_for=timedelta(minutes=15))

# Registration is limited more loosely and on every attempt rather than on
# failures: the cost here is rows in a small free database, not guessed
# passwords.
register_limiter = RateLimiter(max_failures=10, window=timedelta(hours=1), block_for=timedelta(hours=1))


def _caller(request: Request) -> str:
    return client_key(
        request.client.host if request.client else None,
        request.headers.get("x-forwarded-for"),
    )


def _reject_if_limited(limiter: RateLimiter, key: str, now: datetime) -> None:
    wait = limiter.retry_after(key, now)
    if wait is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Try again later.",
            headers={"Retry-After": str(wait)},
        )


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister, request: Request, db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    key = _caller(request)
    _reject_if_limited(register_limiter, key, now)
    register_limiter.record_attempt(key, now)

    existing = await db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=Token)
async def login(payload: UserLogin, request: Request, db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    key = _caller(request)
    _reject_if_limited(login_limiter, key, now)

    user = await db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.password_hash):
        login_limiter.record_failure(key, now)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    login_limiter.record_success(key)
    token = create_access_token(subject=str(user.id), token_version=user.token_version)
    return Token(access_token=token)
