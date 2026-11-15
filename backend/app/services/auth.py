from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import access_token, hash_password, signing_key, token_hash, verify_password
from app.db.models import MasterProfile, RefreshSession, User
from app.repositories.auth import AuthRepository
from app.schemas.auth import Login, Registration, TokenRead, UserRead


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AuthRepository(db)

    def register(self, data: Registration) -> User:
        signing_key()  # Fail before creating unusable accounts if deployment is incomplete.
        user = User(email=str(data.email).strip().lower(), display_name=data.display_name,
                    password_hash=hash_password(data.password.get_secret_value()), role=data.role)
        try:
            self.db.add(user)
            self.db.flush()
            if user.role == "MASTER":
                self.db.add(MasterProfile(user_id=user.id))
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise AppError(409, "EMAIL_UNAVAILABLE", "Этот email уже используется.",
                           [{"path": "email", "message": "Этот email уже используется."}]) from exc
        return user

    def login(self, data: Login) -> tuple[TokenRead, str, int]:
        signing_key()
        user = self.repo.user_by_email(data.email.strip().lower())
        valid = verify_password(data.password.get_secret_value(), user.password_hash if user else None)
        if not valid or not user or not user.is_active:
            raise AppError(401, "INVALID_CREDENTIALS", "Неверный email или пароль.")
        return self.issue(user)

    def issue(self, user: User, family_id=None, expires_at=None) -> tuple[TokenRead, str, int]:
        now = datetime.now(UTC)
        deadline = expires_at or now + timedelta(days=7)
        raw = token_urlsafe(48)
        token = access_token(user.id, user.role)
        self.db.add(RefreshSession(user_id=user.id, token_hash=token_hash(raw),
                                   family_id=family_id or uuid4(), expires_at=deadline))
        self.db.commit()
        return TokenRead(access_token=token, user=UserRead.model_validate(user)), raw, max(0, int((deadline-now).total_seconds()))

    def refresh(self, raw: str) -> tuple[TokenRead, str, int]:
        signing_key()
        session = self.repo.refresh_by_hash(token_hash(raw))
        now = datetime.now(UTC)
        if session is None:
            raise AppError(401, "INVALID_SESSION", "Войдите в аккаунт заново.")
        if session.revoked_at is not None:
            self.repo.revoke_family(session.family_id, now)
            self.db.commit()  # Persist replay response before raising.
            raise AppError(401, "SESSION_REUSED", "Сессия завершена. Войдите заново.")
        user = self.repo.user_by_id(session.user_id)
        if session.expires_at <= now or not user or not user.is_active:
            self.repo.revoke_family(session.family_id, now)
            self.db.commit()
            raise AppError(401, "SESSION_EXPIRED", "Войдите в аккаунт заново.")
        session.revoked_at = now
        return self.issue(user, session.family_id, session.expires_at)

    def logout(self, raw: str | None) -> None:
        if raw:
            session = self.repo.refresh_by_hash(token_hash(raw))
            if session:
                self.repo.revoke_family(session.family_id, datetime.now(UTC))
                self.db.commit()
