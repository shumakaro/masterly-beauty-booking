from fastapi import APIRouter
from pydantic import BaseModel

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
