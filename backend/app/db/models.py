"""PostgreSQL models. Schema changes are applied exclusively through Alembic."""

from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy import (
    text as sqltext,
)
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "pk": "pk_%(table_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ix": "ix_%(table_name)s_%(column_0_name)s",
        }
    )


class Identity:
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Identity, Base):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(10), default="CLIENT")
    display_name: Mapped[str] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=sqltext("true"))
    __table_args__ = (
        CheckConstraint("role IN ('CLIENT','MASTER','ADMIN')", name="ck_users_role"),
        CheckConstraint("email = lower(trim(email)) AND length(email) > 3", name="ck_users_email"),
        CheckConstraint("length(trim(display_name)) > 0", name="ck_users_display_name"),
    )


class MasterProfile(Identity, Base):
    __tablename__ = "master_profiles"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), unique=True)
    bio: Mapped[str] = mapped_column(Text, default="")
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Qyzylorda")
    address: Mapped[str] = mapped_column(String(300), default="")
    avatar_url: Mapped[str | None] = mapped_column(String(1000))
    is_demo: Mapped[bool] = mapped_column(Boolean, server_default=sqltext("false"))
    is_published: Mapped[bool] = mapped_column(Boolean, server_default=sqltext("false"))
    user: Mapped[User] = relationship(lazy="raise")
    offers: Mapped[list["MasterService"]] = relationship(lazy="raise", back_populates="master")


class Category(Identity, Base):
    __tablename__ = "categories"
    slug: Mapped[str] = mapped_column(String(60), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=sqltext("true"))
    __table_args__ = (CheckConstraint("length(trim(name)) > 0", name="ck_categories_name"),)


class Service(Identity, Base):
    __tablename__ = "services"
    category_id: Mapped[UUID] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"))
    name: Mapped[str] = mapped_column(String(150))
    description: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=sqltext("true"))
    __table_args__ = (CheckConstraint("length(trim(name)) > 0", name="ck_services_name"),)


class MasterService(Identity, Base):
    __tablename__ = "master_services"
    master_id: Mapped[UUID] = mapped_column(ForeignKey("master_profiles.id", ondelete="RESTRICT"))
    service_id: Mapped[UUID] = mapped_column(ForeignKey("services.id", ondelete="RESTRICT"))
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    duration_minutes: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=sqltext("true"))
    master: Mapped[MasterProfile] = relationship(back_populates="offers", lazy="raise")
    service: Mapped[Service] = relationship(lazy="raise")
    __table_args__ = (
        UniqueConstraint("master_id", "service_id"),
        UniqueConstraint("id", "master_id", name="uq_master_services_id_master"),
        CheckConstraint("price >= 0", name="ck_master_services_price"),
        CheckConstraint(
            "duration_minutes BETWEEN 15 AND 720 AND duration_minutes % 15 = 0",
            name="ck_master_services_duration",
        ),
        Index("ix_master_services_search", "service_id", "price"),
    )


class Schedule(Identity, Base):
    __tablename__ = "schedules"
    master_id: Mapped[UUID] = mapped_column(ForeignKey("master_profiles.id", ondelete="CASCADE"))
    weekday: Mapped[int] = mapped_column(Integer)
    starts_local: Mapped[time] = mapped_column(Time)
    ends_local: Mapped[time] = mapped_column(Time)
    __table_args__ = (
        CheckConstraint("weekday BETWEEN 0 AND 6", name="ck_schedules_weekday"),
        CheckConstraint("starts_local < ends_local", name="ck_schedules_interval"),
        ExcludeConstraint(
            ("master_id", "="),
            ("weekday", "="),
            (
                sqltext(
                    "int4range(EXTRACT(EPOCH FROM starts_local)::int, EXTRACT(EPOCH FROM "
                    "ends_local)::int, '[)')"
                ),
                "&&",
            ),
            name="ex_schedules_overlap",
            using="gist",
        ),
    )


class ScheduleException(Identity, Base):
    __tablename__ = "schedule_exceptions"
    master_id: Mapped[UUID] = mapped_column(ForeignKey("master_profiles.id", ondelete="CASCADE"))
    local_date: Mapped[date] = mapped_column(Date)
    is_closed: Mapped[bool] = mapped_column(Boolean)
    starts_local: Mapped[time | None] = mapped_column(Time)
    ends_local: Mapped[time | None] = mapped_column(Time)
    __table_args__ = (
        UniqueConstraint("master_id", "local_date"),
        CheckConstraint(
            "(is_closed AND starts_local IS NULL AND ends_local IS NULL) OR (NOT "
            "is_closed AND starts_local IS NOT NULL AND ends_local IS NOT NULL AND "
            "starts_local < ends_local)",
            name="ck_schedule_exceptions_interval",
        ),
    )


class Booking(Identity, Base):
    __tablename__ = "bookings"
    client_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    master_id: Mapped[UUID] = mapped_column(ForeignKey("master_profiles.id", ondelete="RESTRICT"))
    master_service_id: Mapped[UUID] = mapped_column()
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(12), default="CONFIRMED")
    price_snapshot: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    duration_snapshot: Mapped[int] = mapped_column(Integer)
    service_name_snapshot: Mapped[str] = mapped_column(String(150))
    currency: Mapped[str] = mapped_column(String(3), default="KZT")
    timezone_snapshot: Mapped[str] = mapped_column(String(64), default="Asia/Qyzylorda")
    cancelled_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    cancellation_reason: Mapped[str | None] = mapped_column(String(500))
    idempotency_key: Mapped[UUID] = mapped_column()
    request_hash: Mapped[str] = mapped_column(String(64))
    __table_args__ = (
        ForeignKeyConstraint(
            ["master_service_id", "master_id"],
            ["master_services.id", "master_services.master_id"],
            name="fk_bookings_offer_owner",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("client_id", "idempotency_key"),
        CheckConstraint(
            "status IN ('CONFIRMED','CANCELLED','COMPLETED')", name="ck_bookings_status"
        ),
        CheckConstraint("starts_at < ends_at", name="ck_bookings_interval"),
        CheckConstraint("price_snapshot >= 0", name="ck_bookings_price"),
        CheckConstraint(
            "duration_snapshot BETWEEN 15 AND 720 AND duration_snapshot % 15 = 0",
            name="ck_bookings_duration",
        ),
        CheckConstraint(
            "ends_at = starts_at + duration_snapshot * INTERVAL '1 minute'", name="ck_bookings_end"
        ),
        CheckConstraint("currency = 'KZT'", name="ck_bookings_currency"),
        CheckConstraint(
            "(status = 'CANCELLED' AND cancelled_by IS NOT NULL) OR (status <> "
            "'CANCELLED' AND cancelled_by IS NULL AND cancellation_reason IS NULL)",
            name="ck_bookings_cancellation",
        ),
        ExcludeConstraint(
            ("master_id", "="),
            (sqltext("tstzrange(starts_at, ends_at, '[)')"), "&&"),
            where=sqltext("status = 'CONFIRMED'"),
            name="ex_bookings_overlap",
            using="gist",
        ),
        Index("ix_bookings_master_start", "master_id", "starts_at"),
        Index("ix_bookings_client_start", "client_id", sqltext("starts_at DESC")),
    )


class Review(Identity, Base):
    __tablename__ = "reviews"
    booking_id: Mapped[UUID] = mapped_column(
        ForeignKey("bookings.id", ondelete="RESTRICT"), unique=True
    )
    rating: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    is_visible: Mapped[bool] = mapped_column(Boolean, server_default=sqltext("true"))
    __table_args__ = (CheckConstraint("rating BETWEEN 1 AND 5", name="ck_reviews_rating"),)


class Favorite(Base):
    __tablename__ = "favorites"
    client_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    master_id: Mapped[UUID] = mapped_column(
        ForeignKey("master_profiles.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PortfolioItem(Identity, Base):
    __tablename__ = "portfolio_items"
    master_id: Mapped[UUID] = mapped_column(ForeignKey("master_profiles.id", ondelete="CASCADE"))
    url: Mapped[str] = mapped_column(String(1000))
    alt_text: Mapped[str] = mapped_column(String(300))
    source_url: Mapped[str | None] = mapped_column(String(1000))
    license: Mapped[str] = mapped_column(String(150))
    position: Mapped[int] = mapped_column(Integer, default=0)
    __table_args__ = (CheckConstraint("position >= 0", name="ck_portfolio_position"),)


class RefreshSession(Identity, Base):
    __tablename__ = "refresh_sessions"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    family_id: Mapped[UUID] = mapped_column(index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (CheckConstraint("expires_at > created_at", name="ck_refresh_expiry"),)
