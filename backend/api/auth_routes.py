"""Authentication routes – register, login, password reset."""

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.user import User
from ..utils.auth import hash_password, verify_password, create_access_token
from .schemas import RegisterRequest, LoginRequest, TokenResponse, UserResponse
from .deps import get_current_user_id


router = APIRouter(prefix="/auth", tags=["auth"])


# -------------------------------------------------
# REGISTER
# -------------------------------------------------
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):

    result = await db.execute(
        select(User).where(
            or_(User.username == body.username, User.email == body.email)
        )
    )

    existing = result.scalars().first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already taken"
        )

    user = User(
        username=body.username,
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        is_company=body.is_company
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


# -------------------------------------------------
# LOGIN
# -------------------------------------------------
@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):

    result = await db.execute(
        select(User).where(
            or_(User.username == body.username, User.email == body.username)
        )
    )

    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    if not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    token = create_access_token(
        {
            "sub": str(user.id),
            "username": user.username,
            "is_company": user.is_company
        }
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer"
    )


# -------------------------------------------------
# CURRENT USER
# -------------------------------------------------
@router.get("/me", response_model=UserResponse)
async def get_current_user(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):

    user = await db.get(User, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user


# -------------------------------------------------
# FORGOT PASSWORD
# -------------------------------------------------
@router.post("/forgot-password")
async def forgot_password(email: str, db: AsyncSession = Depends(get_db)):

    result = await db.execute(
        select(User).where(User.email == email)
    )

    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not registered"
        )

    reset_token = secrets.token_urlsafe(32)

    expiry = datetime.now(timezone.utc) + timedelta(minutes=30)

    user.reset_token = reset_token
    user.reset_token_expiry = expiry

    await db.commit()

    return {
        "message": "Reset token generated",
        "reset_token": reset_token
    }


# -------------------------------------------------
# RESET PASSWORD
# -------------------------------------------------
@router.post("/reset-password")
async def reset_password(token: str, new_password: str, db: AsyncSession = Depends(get_db)):

    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )

    result = await db.execute(
        select(User).where(User.reset_token == token)
    )

    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token"
        )

    if not user.reset_token_expiry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token invalid"
        )

    if user.reset_token_expiry < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token expired"
        )

    user.hashed_password = hash_password(new_password)

    user.reset_token = None
    user.reset_token_expiry = None

    await db.commit()

    return {"message": "Password updated successfully"}