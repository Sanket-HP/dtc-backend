"""Authentication routes – register and login."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.user import User
from ..utils.auth import hash_password, verify_password, create_access_token
from .schemas import RegisterRequest, LoginRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


# -------------------------------
# REGISTER USER
# -------------------------------
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):

    # Check existing username or email
    result = await db.execute(
        select(User).where(
            or_(User.username == body.username, User.email == body.email)
        )
    )
    existing_user = result.scalars().first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already taken"
        )

    # Create new user
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


# -------------------------------
# LOGIN USER
# -------------------------------
@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):

    # Allow login using username OR email
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

    # Verify password
    if not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    # Create JWT token
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