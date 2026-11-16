import logging
from collections import defaultdict, deque
from threading import Lock
from time import monotonic
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.auth import clear_refresh
from app.api.v1.auth import router as auth_router
from app.api.v1.business import router as business_router
from app.api.v1.health import router
from app.core.config import get_settings
from app.core.errors import AppError

logger = logging.getLogger("masterly.requests")


def error_response(request: Request, status: int, code: str, message: str, fields=None):
    request_id = getattr(request.state, "request_id", str(uuid4()))
    response = JSONResponse(
        status_code=status,
        content={
            "error": {"code": code, "message": message, "fields": fields or []},
            "request_id": request_id,
        },
    )
    if status == 401:
        response.headers["WWW-Authenticate"] = "Bearer"
        if request.url.path == "/api/v1/auth/refresh":
            clear_refresh(response)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Request-ID"] = request_id
    return response


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.2.0")
    attempts = defaultdict(deque)
    limiter_lock = Lock()

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request.state.request_id = str(uuid4())
        limited = request.method == "POST" and request.url.path in {
            "/api/v1/auth/token",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
        }
        blocked = False
        if limited:
            now = monotonic()
            host = request.client.host if request.client else "unknown"
            with limiter_lock:
                for key in list(attempts):
                    while attempts[key] and attempts[key][0] < now - 60:
                        attempts[key].popleft()
                    if not attempts[key]:
                        del attempts[key]
                if host not in attempts and len(attempts) >= 4096:
                    blocked = True
                else:
                    blocked = len(attempts[host]) >= settings.auth_rate_limit
                    if not blocked:
                        attempts[host].append(now)
        if blocked:
            response = error_response(
                request, 429, "RATE_LIMITED", "Слишком много попыток. Подождите минуту."
            )
            response.headers["Retry-After"] = "60"
        else:
            response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        if request.url.path.startswith("/api/v1/"):
            response.headers["Cache-Control"] = "no-store"
        logger.info(
            "%s %s %s request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            request.state.request_id,
        )
        return response

    @app.exception_handler(AppError)
    async def domain_error(request: Request, exc: AppError):
        return error_response(request, exc.status, exc.code, exc.message, exc.fields)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        if any(item["type"] == "json_invalid" for item in exc.errors()):
            return error_response(request, 400, "JSON_INVALID", "Некорректный JSON.")
        # Do not echo Pydantic input/ctx: they may contain a plaintext password.
        fields = [
            {
                "path": ".".join(str(part) for part in item["loc"] if part != "body"),
                "message": "Проверьте значение поля.",
            }
            for item in exc.errors()
        ]
        return error_response(
            request, 422, "VALIDATION_ERROR", "Проверьте заполнение формы.", fields
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException):
        return error_response(
            request, exc.status_code, "HTTP_ERROR", "Запрос не может быть выполнен."
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, exc: SQLAlchemyError):
        return error_response(
            request, 503, "DATABASE_UNAVAILABLE", "Сервис временно недоступен. Попробуйте позже."
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        logger.error(
            "Unhandled request failure request_id=%s",
            getattr(request.state, "request_id", "unknown"),
        )
        return error_response(
            request, 500, "INTERNAL_ERROR", "Не удалось выполнить запрос. Попробуйте позже."
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "Authorization", "X-CSRF-Protection", "Idempotency-Key"],
    )
    app.include_router(router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(business_router, prefix="/api/v1")
    return app


app = create_app()
