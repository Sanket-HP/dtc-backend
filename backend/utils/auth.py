"""Password hashing and JWT token utilities for DataTrust Coin."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from passlib.context import CryptContext
from jose import JWTError, jwt

from ..config import SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES


# ---------------------------------------------------------
# PASSWORD HASHING
# ---------------------------------------------------------

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Hash plain password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against stored hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ---------------------------------------------------------
# CREATE JWT TOKEN
# ---------------------------------------------------------

def create_access_token(
    user_id: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT access token containing user_id.
    """

    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    payload = {
        "sub": user_id,   # subject = user id
        "exp": expire
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# ---------------------------------------------------------
# DECODE JWT TOKEN
# ---------------------------------------------------------

def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode JWT token safely.
    """

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        user_id = payload.get("sub")

        if user_id is None:
            return None

        return payload

    except JWTError:
        return None