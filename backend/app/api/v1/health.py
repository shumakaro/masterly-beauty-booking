from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter(tags=["Operations"])


class HealthResponse(BaseModel):
    status: str
    service: str


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="API process health",
    description="Process liveness only. Does not assert database readiness.",
)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="masterly-api")


@router.get(
    "/ready",
    response_model=HealthResponse,
    summary="API database readiness",
    description="Checks a live DB connection and migration metadata. No credentials returned.",
)
def ready(db: Annotated[Session, Depends(get_db)]) -> HealthResponse:
    db.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    return HealthResponse(status="ok", service="masterly-api")
