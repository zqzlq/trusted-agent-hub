"""TrustedAgentHub API — FastAPI application entry point.

Mounts the consumer router (分发侧) at /api/v0 and configures CORS so
the frontend and CLI tools can call the API from any origin during
development.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .consumer_router import router as consumer_router

app = FastAPI(
    title="Trusted Agent Hub API",
    version="0.1.0",
    description="Backend API for the TrustedAgentHub package registry — Consumer endpoints (分发侧).",
)

# ---------------------------------------------------------------------------
# CORS — permissive for local development; tighten before production.
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(consumer_router, prefix="/api/v0")


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    """Health-check / welcome endpoint."""
    return {"service": "Trusted Agent Hub API", "version": "0.1.0"}
