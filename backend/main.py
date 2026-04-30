"""DataTrust Coin – FastAPI application entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .api.auth_routes import router as auth_router
from .api.dataset_routes import router as dataset_router
from .api.marketplace_routes import router as marketplace_router


# ── App lifecycle ────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="DataTrust Coin (DTC)",
    description="Secure dataset marketplace powered by blockchain-style token rewards.",
    version="1.0.0",
    lifespan=lifespan,
)


# ── Allowed Frontend Origins ─────────────────────────────────────────
ALLOWED_ORIGINS = [
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "https://dtc-frontend-tau.vercel.app",
    "https://dtc-frontend-30p1bhi52-sanket-patils-projects-4418dbe1.vercel.app"
]


# ── CORS Middleware ──────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── API Routes ───────────────────────────────────────────────────────
app.include_router(auth_router, prefix="/api")
app.include_router(dataset_router, prefix="/api")
app.include_router(marketplace_router, prefix="/api")


# ── Root Endpoint ────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "service": "DataTrust Coin API",
        "status": "running",
        "docs": "/docs"
    }


# ── Health Check (used by Render) ────────────────────────────────────
@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "service": "DataTrust Coin"
    }