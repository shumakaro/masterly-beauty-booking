from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.compatibility import SUPPORTED_REVISIONS, schema_revision
from app.db.session import get_db

router = APIRouter(tags=["Operations"])


class HealthResponse(BaseModel):
    status: str
    service: str


class ReadyResponse(HealthResponse):
    schema_revision: str
    compatible_revisions: list[str]


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
    response_model=ReadyResponse,
    summary="API database readiness",
    description="Checks DB connectivity, the supported Alembic revision and required columns. "
    "An incompatible or incomplete schema returns 503. No credentials returned.",
)
def ready(db: Annotated[Session, Depends(get_db)]) -> ReadyResponse:
    return ReadyResponse(
        status="ok",
        service="masterly-api",
        schema_revision=schema_revision(db),
        compatible_revisions=sorted(SUPPORTED_REVISIONS),
    )
