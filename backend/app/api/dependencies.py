from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import decode_access
from app.db.models import User
from app.db.session import get_db

Db = Annotated[Session, Depends(get_db)]
bearer = HTTPBearer(auto_error=False)


def current_user(
    db: Db, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppError(401, "UNAUTHENTICATED", "Войдите в аккаунт.")
    user = db.get(User, decode_access(credentials.credentials))
    if user is None or not user.is_active:
        raise AppError(401, "UNAUTHENTICATED", "Войдите в аккаунт заново.")
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def master_user(user: CurrentUser) -> User:
    if user.role != "MASTER":
        raise AppError(403, "FORBIDDEN", "Доступ разрешен только мастеру.")
    return user


def admin_user(user: CurrentUser) -> User:
    if user.role != "ADMIN":
        raise AppError(403, "FORBIDDEN", "Недостаточно прав.")
    return user


MasterUser = Annotated[User, Depends(master_user)]
AdminUser = Annotated[User, Depends(admin_user)]


def client_user(user: CurrentUser) -> User:
    if user.role != "CLIENT":
        raise AppError(403, "FORBIDDEN", "Доступ разрешен только клиенту.")
    return user


ClientUser = Annotated[User, Depends(client_user)]
