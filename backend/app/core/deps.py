from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.database import get_db
from app.db.models import User

# HTTPBearer rather than OAuth2PasswordBearer: /auth/login takes a JSON body,
# not the form-encoded username/password the OAuth2 flow assumes, so the Swagger
# Authorize button would post the wrong shape and always fail.
bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        user_id = int(decode_access_token(credentials.credentials))
    except (JWTError, TypeError, ValueError):
        raise credentials_error

    user = await db.get(User, user_id)
    if user is None:
        raise credentials_error
    return user
