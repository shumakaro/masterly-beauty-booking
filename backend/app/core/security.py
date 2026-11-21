from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import UUID

import bcrypt
import jwt

from app.core.config import get_settings
from app.core.errors import AppError


def signing_key() -> str:
    secret = get_settings().jwt_secret
    if secret is None or len(secret.get_secret_value().encode()) < 32:
        raise AppError(503, "AUTH_NOT_CONFIGURED", "Сервис входа временно недоступен.")
    return secret.get_secret_value()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("ascii")


# Same work factor for unknown and known users; not a credential.
DUMMY_HASH = bcrypt.hashpw(b"dummy-never-used-to-sign-in", bcrypt.gensalt(rounds=12))


def verify_password(password: str, encoded: str | None) -> bool:
    raw = password.encode("utf-8")
    if len(raw) > 72:
        return False
    try:
        return bcrypt.checkpw(raw, encoded.encode("ascii") if encoded else DUMMY_HASH)
    except (ValueError, UnicodeError):
        bcrypt.checkpw(raw, DUMMY_HASH)
        return False


def token_hash(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


# Подписанный JWT имеет короткий срок; фактические права дополнительно проверяются по БД.
def access_token(user_id: UUID, role: str) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user_id),
            "role": role,
            "iat": now,
            "exp": now + timedelta(minutes=15),
            "type": "access",
        },
        signing_key(),
        algorithm="HS256",
    )


def decode_access(token: str) -> UUID:
    try:
        data = jwt.decode(
            token,
            signing_key(),
            algorithms=["HS256"],
            options={"require": ["sub", "role", "iat", "exp", "type"]},
        )
        if data["type"] != "access" or data["role"] not in {"CLIENT", "MASTER", "ADMIN"}:
            raise ValueError("Invalid token type")
        return UUID(data["sub"])
    except (jwt.InvalidTokenError, ValueError, TypeError, AttributeError) as exc:
        raise AppError(401, "UNAUTHENTICATED", "Войдите в аккаунт заново.") from exc
