from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.modules.auth.router import router as auth_router
from app.modules.operations.router import router as operations_router
from app.modules.operations.brand_portal_router import router as brand_portal_router
from app.modules.roster.router import router as roster_router
from app.modules.workforce.router import router as workforce_router

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="RosterIQ API: workforce, brands, processes, operating rules, deterministic roster generation and validation.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_error_handlers(app)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(workforce_router, prefix="/api/v1")
app.include_router(operations_router, prefix="/api/v1")
app.include_router(brand_portal_router, prefix="/api/v1")
app.include_router(roster_router, prefix="/api/v1")


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}
