from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import secrets
from datetime import datetime

from backend.firebase_config import db
from backend.api.deps import get_current_user

router = APIRouter(prefix="/companies", tags=["Companies"])

# ==============================

# 📦 Schemas

# ==============================

class CompanyCreate(BaseModel):
name: str
email: str
industry: Optional[str] = None

class CompanyResponse(BaseModel):
id: str
name: str
email: str
api_key: str
created_at: str

# ==============================

# 🔐 Helper Functions

# ==============================

def generate_api_key():
return "dtc_" + secrets.token_hex(24)

# ==============================

# 🏢 Create Company

# ==============================

@router.post("/register", response_model=CompanyResponse)
def register_company(data: CompanyCreate, user=Depends(get_current_user)):
company_ref = db.collection("companies").document()

```
api_key = generate_api_key()

company_data = {
    "name": data.name,
    "email": data.email,
    "industry": data.industry,
    "api_key": api_key,
    "owner_id": user["uid"],
    "created_at": datetime.utcnow().isoformat(),
    "dtc_balance": 0,
    "total_spent": 0
}

company_ref.set(company_data)

return CompanyResponse(
    id=company_ref.id,
    name=data.name,
    email=data.email,
    api_key=api_key,
    created_at=company_data["created_at"]
)
```

# ==============================

# 🔍 Get Company Details

# ==============================

@router.get("/me")
def get_company(user=Depends(get_current_user)):
companies = db.collection("companies").where("owner_id", "==", user["uid"]).stream()

```
for company in companies:
    data = company.to_dict()
    data["id"] = company.id
    return data

raise HTTPException(status_code=404, detail="Company not found")
```

# ==============================

# 💰 Add DTC Balance (Manual for now)

# ==============================

@router.post("/add-balance")
def add_balance(amount: float, user=Depends(get_current_user)):
companies = db.collection("companies").where("owner_id", "==", user["uid"]).stream()

```
for company in companies:
    ref = db.collection("companies").document(company.id)
    data = company.to_dict()

    new_balance = data.get("dtc_balance", 0) + amount

    ref.update({"dtc_balance": new_balance})

    return {"message": "Balance updated", "new_balance": new_balance}

raise HTTPException(status_code=404, detail="Company not found")
```

# ==============================

# 🔑 Validate API Key (Internal Use)

# ==============================

def get_company_by_api_key(api_key: str):
companies = db.collection("companies").where("api_key", "==", api_key).stream()

```
for company in companies:
    data = company.to_dict()
    data["id"] = company.id
    return data

return None
```
