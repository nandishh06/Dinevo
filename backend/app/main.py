"""FastAPI application entry point.

Run locally with:
    uvicorn app.main:app --reload

Serves:
  /api/health             liveness probe
  /api/dashboard/...      authenticated owner dashboard (Supabase-backed)
  /api/menu/{slug}        public customer menu (Supabase-backed)
"""

from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, load_settings
from app.schemas import HealthResponse
from app.api.dashboard import router as dashboard_router
from app.api.menu import router as menu_router

app = FastAPI(title="Dscape Dine AR backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "https://192.168.1.14:3000",
    ],
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(dashboard_router, prefix="/api")
app.include_router(menu_router, prefix="/api")


def get_settings() -> Settings:
    return load_settings()


@app.get("/api/health", response_model=HealthResponse)
def health(_settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(status="ok", service="dscape-dine-ar-backend")
