from pydantic import BaseModel


class ErrorField(BaseModel):
    path: str
    message: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    fields: list[ErrorField]


class ErrorResponse(BaseModel):
    error: ErrorDetail
    request_id: str
