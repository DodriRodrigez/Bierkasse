"""FastAPI application entrypoint."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import (
    accounts,
    admin,
    auth,
    beverages,
    dashboard,
    deliveries,
    events,
    inventory,
    kassenbereiche,
    refunds,
    ringbrett,
    semesters,
    tags,
    transactions,
    users,
)
from app.config import settings
from app.core.errors import DomainError

app = FastAPI(title=f"{settings.app_name} API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count", "X-Page", "X-Per-Page"],
)


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "app": settings.app_name}


api = "/api/v1"
for module in (
    auth,
    users,
    semesters,
    accounts,
    kassenbereiche,
    tags,
    transactions,
    dashboard,
    beverages,
    deliveries,
    ringbrett,
    events,
    inventory,
    refunds,
    admin,
):
    app.include_router(module.router, prefix=api)
