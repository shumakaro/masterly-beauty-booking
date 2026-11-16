from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel

from app.api.dependencies import AdminUser, CurrentUser, Db, MasterUser
from app.core.config import get_settings
from app.core.errors import AppError
from app.schemas.auth import Login, Registration, TokenRead, UserRead, UserUpdate
from app.schemas.auth import MasterProfileRead as MasterRead
from app.schemas.errors import ErrorResponse
from app.services.auth import AuthService


def errors(*statuses: int):
    codes = set(statuses) | ({400} if 422 in statuses else set())
    return {status: {"model": ErrorResponse} for status in codes}


router = APIRouter(tags=["Authentication"])
COOKIE_NAME = "masterly_refresh"
COOKIE_PATH = "/api/v1/auth"


def require_browser_origin(request: Request) -> None:
    settings = get_settings()
    if (
        request.headers.get("origin") not in settings.cors_origins
        or request.headers.get("x-csrf-protection") != "1"
    ):
        raise AppError(403, "CSRF_REJECTED", "Обновите страницу и повторите действие.")


def set_refresh(response: Response, raw: str, max_age: int) -> None:
    response.set_cookie(
        COOKIE_NAME,
        raw,
        max_age=max_age,
        httponly=True,
        secure=get_settings().cookie_secure,
        samesite="lax",
        path=COOKIE_PATH,
    )
    response.headers["Cache-Control"] = "no-store"


def clear_refresh(response: Response) -> None:
    response.delete_cookie(
        COOKIE_NAME,
        path=COOKIE_PATH,
        secure=get_settings().cookie_secure,
        httponly=True,
        samesite="lax",
    )


@router.post(
    "/auth/register",
    responses=errors(403, 409, 422, 429, 503),
    response_model=UserRead,
    status_code=201,
    dependencies=[Depends(require_browser_origin)],
    summary="Register a client or master; ADMIN is never self-assigned",
)
def register(data: Registration, db: Db):
    return AuthService(db).register(data)


@router.post(
    "/auth/token",
    responses=errors(401, 403, 422, 429, 503),
    response_model=TokenRead,
    dependencies=[Depends(require_browser_origin)],
    summary="Authenticate with JSON credentials and issue a refresh cookie",
)
def login(data: Login, response: Response, db: Db):
    result, raw, seconds = AuthService(db).login(data)
    set_refresh(response, raw, seconds)
    return result


@router.post(
    "/auth/refresh",
    responses=errors(401, 403, 429, 503),
    response_model=TokenRead,
    dependencies=[Depends(require_browser_origin)],
    summary="Rotate the refresh cookie; replays revoke its entire family",
)
def refresh(request: Request, response: Response, db: Db):
    raw = request.cookies.get(COOKIE_NAME)
    if not raw or len(raw) > 256:
        raise AppError(401, "INVALID_SESSION", "Войдите в аккаунт заново.")
    result, next_raw, seconds = AuthService(db).refresh(raw)
    set_refresh(response, next_raw, seconds)
    return result


@router.delete(
    "/auth/session",
    responses=errors(403, 503),
    status_code=204,
    dependencies=[Depends(require_browser_origin)],
    summary="Revoke refresh session",
)
def logout(request: Request, db: Db):
    AuthService(db).logout(request.cookies.get(COOKIE_NAME))
    response = Response(status_code=204)
    clear_refresh(response)
    return response


@router.get(
    "/users/me",
    responses=errors(401, 503),
    response_model=UserRead,
    tags=["Users"],
    summary="Current private profile",
)
def me(user: CurrentUser):
    return user


@router.patch(
    "/users/me",
    responses=errors(401, 422, 503),
    response_model=UserRead,
    tags=["Users"],
    summary="Update own display name",
)
def update_me(data: UserUpdate, user: CurrentUser, db: Db):
    return AuthService(db).update_user(user, data.display_name)


@router.get(
    "/master/profile",
    responses=errors(401, 403, 404, 503),
    response_model=MasterRead,
    tags=["Master"],
    summary="Read only the authenticated master's profile",
)
def master_profile(user: MasterUser, db: Db):
    return AuthService(db).master_profile(user.id)


class AdminOverview(BaseModel):
    users: int
    masters: int
    bookings: int


@router.get(
    "/admin/overview",
    responses=errors(401, 403, 503),
    response_model=AdminOverview,
    tags=["Administration"],
    summary="Real system totals, restricted to ADMIN",
)
def admin_overview(user: AdminUser, db: Db):
    return AdminOverview(**AuthService(db).overview())
