"""Shared FastAPI dependencies – Firebase authentication."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from firebase_admin import auth
from google.cloud.exceptions import NotFound

from ..firebase_config import db


# ---------------------------------------------------------
# HTTP Bearer Token Extractor
# ---------------------------------------------------------
security = HTTPBearer()


# ---------------------------------------------------------
# Get current authenticated user
# ---------------------------------------------------------
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization token missing"
        )

    token = credentials.credentials

    try:
        # Verify Firebase ID token
        decoded_token = auth.verify_id_token(token)

        user_id = decoded_token.get("uid")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )

        # Fetch user from Firestore
        doc = db.collection("users").document(user_id).get()

        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        user_data = doc.to_dict()
        user_data["id"] = user_id

        return user_data

    except auth.InvalidIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )

    except auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token expired"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )


# ---------------------------------------------------------
# Return only user ID
# ---------------------------------------------------------
async def get_current_user_id(
    user: dict = Depends(get_current_user)
) -> str:

    return user["id"]