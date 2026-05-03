from fastapi import APIRouter, HTTPException
from google.cloud import firestore
from ..firebase_config import db

router = APIRouter(prefix="/treasury", tags=["treasury"])


# -------------------------------------------------
# GET TREASURY BALANCE
# -------------------------------------------------
@router.get("/balance")
async def treasury_balance():

    doc = db.collection("treasury").document("platform_wallet").get()

    if not doc.exists:
        raise HTTPException(404, "Treasury wallet not found")

    return doc.to_dict()


# -------------------------------------------------
# FUND TREASURY (ADMIN)
# -------------------------------------------------
@router.post("/fund")
async def fund_treasury(amount: float):

    db.collection("treasury").document("platform_wallet").update({
        "wallet_balance": firestore.Increment(amount)
    })

    return {"message": "Treasury funded successfully"}