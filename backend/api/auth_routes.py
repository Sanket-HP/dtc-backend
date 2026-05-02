"""Authentication routes – Firebase version."""

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status

from firebase_admin import auth
from ..firebase_config import db

from .schemas import RegisterRequest, LoginRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


# -------------------------------------------------
# REGISTER USER
# -------------------------------------------------
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest):

    try:
        # create Firebase Auth user
        user_record = auth.create_user(
            email=body.email,
            password=body.password,
            display_name=body.username
        )

        # save additional data in Firestore
        db.collection("users").document(user_record.uid).set({
            "username": body.username,
            "email": body.email,
            "full_name": body.full_name,
            "is_company": body.is_company,
            "token_balance": 0,
            "created_at": datetime.now(timezone.utc)
        })

        return {
            "id": user_record.uid,
            "username": body.username,
            "email": body.email,
            "full_name": body.full_name,
            "is_company": body.is_company,
            "token_balance": 0,
            "created_at": datetime.now(timezone.utc)
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# -------------------------------------------------
# LOGIN USER
# -------------------------------------------------
@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):

    try:
        user = auth.get_user_by_email(body.username)

        # Firebase does not verify password here
        # frontend must authenticate and send token
        custom_token = auth.create_custom_token(user.uid)

        return {
            "access_token": custom_token.decode(),
            "token_type": "bearer"
        }

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )


# -------------------------------------------------
# CURRENT USER
# -------------------------------------------------
@router.get("/me", response_model=UserResponse)
async def get_current_user(user_id: str):

    doc = db.collection("users").document(user_id).get()

    if not doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    data = doc.to_dict()
    data["id"] = user_id

    return data


# -------------------------------------------------
# FORGOT PASSWORD
# -------------------------------------------------
@router.post("/forgot-password")
async def forgot_password(email: str):

    try:
        user = auth.get_user_by_email(email)

        reset_token = secrets.token_urlsafe(32)

        db.collection("password_resets").document(reset_token).set({
            "user_id": user.uid,
            "expiry": datetime.now(timezone.utc) + timedelta(minutes=30)
        })

        return {
            "message": "Reset token generated",
            "reset_token": reset_token
        }

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not registered"
        )


# -------------------------------------------------
# RESET PASSWORD
# -------------------------------------------------
@router.post("/reset-password")
async def reset_password(token: str, new_password: str):

    doc = db.collection("password_resets").document(token).get()

    if not doc.exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token"
        )

    data = doc.to_dict()

    if data["expiry"] < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token expired"
        )

    auth.update_user(
        data["user_id"],
        password=new_password
    )

    db.collection("password_resets").document(token).delete()

    return {"message": "Password updated successfully"}