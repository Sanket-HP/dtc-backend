"""DataTrust Coin – FastAPI application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from .database import init_db
from .api.auth_routes import router as auth_router
from .api.dataset_routes import router as dataset_router
from .api.marketplace_routes import router as marketplace_router


FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


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


# ── CORS configuration (important for frontend) ──────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all during development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── API Routes ───────────────────────────────────────────────────────
app.include_router(auth_router, prefix="/api")
app.include_router(dataset_router, prefix="/api")
app.include_router(marketplace_router, prefix="/api")


# ── Health check ─────────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "DataTrust Coin"}


# ── Static frontend ──────────────────────────────────────────────────
if FRONTEND_DIR.exists():
    app.mount(
        "/static",
        StaticFiles(directory=str(FRONTEND_DIR / "static")),
        name="dtc-static",
    )

    @app.get("/dtc", response_class=HTMLResponse)
    @app.get("/dtc/marketplace", response_class=HTMLResponse)
    @app.get("/dtc/upload", response_class=HTMLResponse)
    async def serve_frontend():
        return (FRONTEND_DIR / "index.html").read_text()