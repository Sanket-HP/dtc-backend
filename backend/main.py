"""DataTrust Coin – FastAPI application entry point."""

import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse


# -------------------------------------------------
# Optional database initialization
# -------------------------------------------------
try:
    from .database import init_db
except Exception:
    init_db = None


# -------------------------------------------------
# API ROUTES
# -------------------------------------------------
from .api.auth_routes import router as auth_router
from .api.dataset_routes import router as dataset_router
from .api.marketplace_routes import router as marketplace_router
from .api.economy_routes import router as economy_router
from .api.users import router as users_router
from .api.leaderboard import router as leaderboard_router
from .api.requests import router as requests_router
from .api.recommendations import router as recommendations_router

# Token + Treasury routers
from .api.token_routes import router as token_router
from .api.treasury_routes import router as treasury_router


# -------------------------------------------------
# SIMPLE API ANALYTICS
# -------------------------------------------------
REQUEST_COUNTER = 0


# -------------------------------------------------
# App lifecycle
# -------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):

    print("🚀 Starting DataTrust Coin backend")

    if init_db:
        try:
            await init_db()
            print("✅ Database initialized")
        except Exception as e:
            print("⚠ Database init skipped:", e)

    yield

    print("🛑 Shutting down DataTrust Coin backend")


# -------------------------------------------------
# FastAPI app
# -------------------------------------------------
app = FastAPI(
    title="DataTrust Coin (DTC)",
    description="Secure dataset marketplace powered by token rewards.",
    version="1.4.0",
    lifespan=lifespan,
)


# -------------------------------------------------
# Allowed frontend origins
# -------------------------------------------------
DEFAULT_ORIGINS = [
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "https://dtc-frontend-tau.vercel.app",
    "https://dtc-frontend-30p1bhi52-sanket-patils-projects-4418dbe1.vercel.app",
]

extra_origins = os.getenv("CORS_ORIGINS")

if extra_origins:
    DEFAULT_ORIGINS.extend(extra_origins.split(","))


# -------------------------------------------------
# CORS middleware
# -------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=DEFAULT_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------
# REQUEST LOGGER
# -------------------------------------------------
@app.middleware("http")
async def request_logger(request: Request, call_next):

    global REQUEST_COUNTER
    REQUEST_COUNTER += 1

    start = time.time()

    response = await call_next(request)

    duration = round((time.time() - start) * 1000, 2)

    print(
        f"[API] {request.method} {request.url.path} "
        f"{response.status_code} {duration}ms "
        f"requests={REQUEST_COUNTER}"
    )

    return response


# -------------------------------------------------
# SIMPLE RATE LIMIT PROTECTION
# -------------------------------------------------
REQUEST_TIMES = {}

@app.middleware("http")
async def rate_limit(request: Request, call_next):

    ip = request.client.host
    now = time.time()

    if ip not in REQUEST_TIMES:
        REQUEST_TIMES[ip] = []

    REQUEST_TIMES[ip] = [
        t for t in REQUEST_TIMES[ip] if now - t < 60
    ]

    if len(REQUEST_TIMES[ip]) > 120:
        return JSONResponse(
            {"error": "Rate limit exceeded"},
            status_code=429
        )

    REQUEST_TIMES[ip].append(now)

    return await call_next(request)


# -------------------------------------------------
# API Routes
# -------------------------------------------------
app.include_router(auth_router, prefix="/api")
app.include_router(dataset_router, prefix="/api")
app.include_router(marketplace_router, prefix="/api")
app.include_router(economy_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(leaderboard_router, prefix="/api")
app.include_router(requests_router, prefix="/api")
app.include_router(recommendations_router, prefix="/api")

# Token economy routes
app.include_router(token_router, prefix="/api")
app.include_router(treasury_router, prefix="/api")


# -------------------------------------------------
# Root Endpoint
# -------------------------------------------------
@app.get("/")
async def root():
    return {
        "service": "DataTrust Coin API",
        "status": "running",
        "version": "1.4.0",
        "docs": "/docs"
    }


# -------------------------------------------------
# Health Check
# -------------------------------------------------
@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "service": "DataTrust Coin",
        "requests_served": REQUEST_COUNTER
    }


# -------------------------------------------------
# Run locally
# -------------------------------------------------
if __name__ == "__main__":

    import uvicorn

    port = int(os.environ.get("PORT", 8080))

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )