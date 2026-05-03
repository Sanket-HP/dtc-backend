"""Authentication routes – Firebase version."""

import secrets
import requests
from datetime import datetime, timedelta, timezone
import os

from fastapi import APIRouter, HTTPException, status, Depends

from firebase_admin import auth
from ..firebase_config import db

from .schemas import RegisterRequest, LoginRequest, TokenResponse, UserResponse
from .deps import get_current_user_id


router = APIRouter(prefix="/auth", tags=["auth"])

# Firebase Web API key
FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY")


# -------------------------------------------------
# REGISTER USER
# -------------------------------------------------
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest):

    try:
        user_record = auth.create_user(
            email=body.email,
            password=body.password,
            display_name=body.username
        )

        user_data = {
            "username": body.username,
            "email": body.email,
            "full_name": body.full_name,
            "is_company": body.is_company,
            "token_balance": 0,
            "status": "active",  # NEW
            "created_at": datetime.now(timezone.utc)
        }

        db.collection("users").document(user_record.uid).set(user_data)

        user_data["id"] = user_record.uid

        return user_data

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

        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"

        payload = {
            "email": body.email,
            "password": body.password,
            "returnSecureToken": True
        }

        r = requests.post(url, json=payload)

        if r.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

        data = r.json()

        return {
            "access_token": data["idToken"],
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
async def get_current_user(
    user_id: str = Depends(get_current_user_id)
):

    doc = db.collection("users").document(user_id).get()

    if not doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    data = doc.to_dict()

    # prevent deleted users login
    if data.get("status") == "deleted":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account deleted"
        )

    data["id"] = user_id

    return data


# -------------------------------------------------
# DELETE ACCOUNT (NEW)
# -------------------------------------------------
@router.delete("/delete-account")
async def delete_account(
    user_id: str = Depends(get_current_user_id)
):

    try:

        # delete user datasets
        datasets = (
            db.collection("datasets")
            .where("owner_id", "==", user_id)
            .stream()
        )

        for d in datasets:
            db.collection("datasets").document(d.id).delete()

        # delete transactions
        txs = (
            db.collection("transactions")
            .where("user_id", "==", user_id)
            .stream()
        )

        for t in txs:
            db.collection("transactions").document(t.id).delete()

        # mark user as deleted (better than full deletion)
        db.collection("users").document(user_id).update({
            "status": "deleted",
            "deleted_at": datetime.now(timezone.utc)
        })

        # remove firebase auth user
        auth.delete_user(user_id)

        return {"message": "Account deleted successfully"}

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )


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