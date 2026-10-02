"""FastAPI application for Weather-Advisory Support Bot (Phase 3).

Exposes:
- Authentication (/auth/register, /auth/login, /auth/me)
- Conversations (/conversations)
- Weather Advisory (/advisory, /api/advisory)
- Health check (/health)
"""

from contextlib import asynccontextmanager
from typing import Any, Dict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import FRONTEND_URL
from backend.app.db.base import init_db
from backend.app.routers.advisory import router as advisory_router
from backend.app.routers.auth import router as auth_router
from backend.app.routers.conversations import router as conversations_router
from backend.app.schemas.advisory import AdvisoryRequest, QueryResponse

# For backwards compatibility with test imports
QueryRequest = AdvisoryRequest


from backend.app.services.llm_service import validate_llm_configuration


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown hooks."""
    # Ensure database schema is initialized on startup
    init_db()
    # Validate LLM API key status and log clear guidance without leaking secrets
    validate_llm_configuration()
    yield


app = FastAPI(
    title="Weather-Advisory Support Bot API",
    version="3.0.0 (Phase 3)",
    description=(
        "Production backend for outdoor activity weather advisories "
        "powered by LangGraph, Open-Meteo, and a deterministic SOP engine."
    ),
    lifespan=lifespan,
)

# Configure CORS origins
allowed_origins = [
    FRONTEND_URL,
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router)
app.include_router(conversations_router)
app.include_router(advisory_router)


@app.get("/health", tags=["Health"])
def health_check() -> Dict[str, str]:
    """Health check endpoint confirming backend and policy operational status."""
    return {"status": "healthy", "phase": "3"}
