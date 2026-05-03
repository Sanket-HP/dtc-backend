"""Token statistics routes."""

from fastapi import APIRouter, HTTPException
from google.cloud import firestore

from ..firebase_config import db

router = APIRouter(prefix="/token", tags=["token"])


# -------------------------------------------------
# TOKEN STATS
# -------------------------------------------------
@router.get("/stats")
async def get_token_stats():

    doc = db.collection("token_stats").document("token_stats").get()

    if not doc.exists:
        raise HTTPException(status_code=404, detail="Token stats not found")

    stats = doc.to_dict()

    # additional platform stats
    users = list(db.collection("users").stream())
    datasets = list(db.collection("datasets").stream())

    return {
        "total_supply": stats.get("total_supply", 0),
        "circulating_supply": stats.get("circulating_supply", 0),
        "burned": stats.get("burned", 0),
        "total_users": len(users),
        "total_datasets": len(datasets)
    }


# -------------------------------------------------
# ADMIN: RESET TOKEN STATS (optional)
# -------------------------------------------------
@router.post("/reset")
async def reset_token_stats():

    db.collection("token_stats").document("token_stats").set({
        "total_supply": 100000000,
        "circulating_supply": 0,
        "burned": 0
    })

    return {"message": "Token stats reset successfully"}