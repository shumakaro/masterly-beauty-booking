from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db.models import RefreshSession, User


class AuthRepository:
    def __init__(self, db: Session):
        self.db = db

    def user_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email))

    def user_by_id(self, user_id: UUID) -> User | None:
        return self.db.get(User, user_id)

    def refresh_by_hash(self, digest: str) -> RefreshSession | None:
        # Lock the owner first: refresh/replay/logout of one family cannot deadlock
        # while taking different token-row locks in the opposite order.
        self.db.scalar(
            select(User)
            .join(RefreshSession, RefreshSession.user_id == User.id)
            .where(RefreshSession.token_hash == digest)
            .with_for_update(of=User)
        )
        return self.db.scalar(
            select(RefreshSession).where(RefreshSession.token_hash == digest).with_for_update()
        )

    def revoke_family(self, family_id: UUID, now) -> None:
        self.db.execute(
            update(RefreshSession)
            .where(RefreshSession.family_id == family_id, RefreshSession.revoked_at.is_(None))
            .values(revoked_at=now)
        )

    def master_profile(self, user_id: UUID):
        from app.db.models import MasterProfile

        return self.db.scalar(select(MasterProfile).where(MasterProfile.user_id == user_id))

    def overview(self):
        from sqlalchemy import func

        from app.db.models import Booking, MasterProfile

        return {
            "users": self.db.scalar(select(func.count()).select_from(User)) or 0,
            "masters": self.db.scalar(select(func.count()).select_from(MasterProfile)) or 0,
            "bookings": self.db.scalar(select(func.count()).select_from(Booking)) or 0,
        }
