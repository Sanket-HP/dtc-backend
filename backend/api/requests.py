"""Dataset request marketplace routes."""

from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone, timedelta

from ..firebase_config import db
from .deps import get_current_user_id

router = APIRouter(prefix="/requests", tags=["dataset_requests"])


# -------------------------------------------------
# CREATE DATASET REQUEST (COMPANIES)
# -------------------------------------------------
@router.post("/create")
async def create_request(
    title: str,
    description: str,
    reward: float,
    category: str = "general",
    deadline_days: int = 7,
    user_id: str = Depends(get_current_user_id)
):

    if reward <= 0:
        raise HTTPException(400, "Reward must be greater than 0")

    deadline = datetime.now(timezone.utc) + timedelta(days=deadline_days)

    request_data = {
        "title": title,
        "description": description,
        "category": category,
        "reward": reward,
        "created_by": user_id,
        "status": "open",
        "deadline": deadline,
        "created_at": datetime.now(timezone.utc),
        "submission_count": 0,
        "winner_dataset": None
    }

    ref = db.collection("dataset_requests").add(request_data)

    request_data["id"] = ref[1].id

    return request_data


# -------------------------------------------------
# LIST ALL DATASET REQUESTS
# -------------------------------------------------
@router.get("/")
async def list_requests():

    docs = (
        db.collection("dataset_requests")
        .order_by("created_at", direction="DESCENDING")
        .stream()
    )

    results = []

    for d in docs:
        data = d.to_dict()
        data["id"] = d.id
        results.append(data)

    return results


# -------------------------------------------------
# REQUEST DETAILS
# -------------------------------------------------
@router.get("/{request_id}")
async def request_details(request_id: str):

    doc = db.collection("dataset_requests").document(request_id).get()

    if not doc.exists:
        raise HTTPException(404, "Request not found")

    data = doc.to_dict()
    data["id"] = request_id

    return data


# -------------------------------------------------
# SUBMIT DATASET FOR REQUEST
# -------------------------------------------------
@router.post("/{request_id}/submit")
async def submit_dataset_for_request(
    request_id: str,
    dataset_id: str,
    user_id: str = Depends(get_current_user_id)
):

    req_ref = db.collection("dataset_requests").document(request_id)
    req_doc = req_ref.get()

    if not req_doc.exists:
        raise HTTPException(404, "Request not found")

    req_data = req_doc.to_dict()

    # deadline check
    if datetime.now(timezone.utc) > req_data.get("deadline"):
        raise HTTPException(400, "Submission deadline passed")

    dataset_doc = db.collection("datasets").document(dataset_id).get()

    if not dataset_doc.exists:
        raise HTTPException(404, "Dataset not found")

    # prevent duplicate submission
    existing = (
        db.collection("request_submissions")
        .where("request_id", "==", request_id)
        .where("dataset_id", "==", dataset_id)
        .stream()
    )

    if list(existing):
        raise HTTPException(400, "Dataset already submitted")

    submission = {
        "request_id": request_id,
        "dataset_id": dataset_id,
        "submitted_by": user_id,
        "status": "pending",
        "submitted_at": datetime.now(timezone.utc)
    }

    db.collection("request_submissions").add(submission)

    req_ref.update({
        "submission_count": req_data.get("submission_count", 0) + 1
    })

    return {"message": "Dataset submitted for review"}


# -------------------------------------------------
# LIST SUBMISSIONS FOR REQUEST
# -------------------------------------------------
@router.get("/{request_id}/submissions")
async def list_submissions(request_id: str):

    docs = (
        db.collection("request_submissions")
        .where("request_id", "==", request_id)
        .stream()
    )

    results = []

    for d in docs:
        data = d.to_dict()
        data["id"] = d.id
        results.append(data)

    return results


# -------------------------------------------------
# ACCEPT DATASET SUBMISSION (COMPANY PICKS WINNER)
# -------------------------------------------------
@router.post("/{request_id}/accept")
async def accept_submission(
    request_id: str,
    dataset_id: str,
    user_id: str = Depends(get_current_user_id)
):

    req_ref = db.collection("dataset_requests").document(request_id)
    req_doc = req_ref.get()

    if not req_doc.exists:
        raise HTTPException(404, "Request not found")

    req_data = req_doc.to_dict()

    if req_data["created_by"] != user_id:
        raise HTTPException(403, "Only request creator can accept submission")

    dataset_doc = db.collection("datasets").document(dataset_id).get()

    if not dataset_doc.exists:
        raise HTTPException(404, "Dataset not found")

    dataset = dataset_doc.to_dict()

    reward = req_data.get("reward", 0)

    # pay dataset creator
    owner_ref = db.collection("users").document(dataset["owner_id"])
    owner_doc = owner_ref.get()

    if owner_doc.exists:

        owner = owner_doc.to_dict()

        owner_ref.update({
            "token_balance": owner.get("token_balance", 0) + reward
        })

    # mark request completed
    req_ref.update({
        "status": "completed",
        "winner_dataset": dataset_id
    })

    db.collection("transactions").add({
        "user_id": dataset["owner_id"],
        "dataset_id": dataset_id,
        "amount": reward,
        "type": "request_reward",
        "created_at": datetime.now(timezone.utc)
    })

    return {
        "message": "Dataset accepted and reward paid",
        "dataset_id": dataset_id,
        "reward": reward
    }