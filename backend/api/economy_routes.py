"""Token economy statistics routes."""

from fastapi import APIRouter, HTTPException
from ..firebase_config import db

router = APIRouter(prefix="/economy", tags=["economy"])


# -------------------------------------------------
# ECONOMY STATS
# -------------------------------------------------
@router.get("/stats")
async def get_economy_stats():

    token_doc = db.collection("token_stats").document("token_stats").get()

    if not token_doc.exists:
        raise HTTPException(status_code=404, detail="Token stats not found")

    token_data = token_doc.to_dict()

    treasury_doc = db.collection("treasury").document("platform_wallet").get()
    treasury_balance = 0

    if treasury_doc.exists:
        treasury_balance = treasury_doc.to_dict().get("wallet_balance", 0)

    users = list(db.collection("users").stream())
    datasets = list(db.collection("datasets").stream())
    transactions = list(db.collection("transactions").stream())

    return {
        "total_supply": token_data.get("total_supply", 0),
        "circulating_supply": token_data.get("circulating_supply", 0),
        "burned": token_data.get("burned", 0),

        "founder_reserve": token_data.get("founder_reserve", 0),
        "dataset_rewards_pool": token_data.get("dataset_rewards_pool", 0),
        "treasury_pool": token_data.get("treasury_pool", 0),
        "community_pool": token_data.get("community_pool", 0),
        "investor_pool": token_data.get("investor_pool", 0),

        "treasury_balance": treasury_balance,

        "total_users": len(users),
        "total_datasets": len(datasets),
        "total_transactions": len(transactions)
    }