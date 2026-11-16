from datetime import date, datetime, time
from decimal import Decimal
from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.auth import StrictSchema


class ReadModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    page_size: int


class Patch(StrictSchema):
    @model_validator(mode="after")
    def provided_values(self):
        if not self.model_fields_set:
            raise ValueError("Укажите хотя бы одно изменение")
        if any(
            getattr(self, name) is None for name in self.model_fields_set if name != "avatar_url"
        ):
            raise ValueError("Значение не может быть null")
        return self


class CategoryCreate(StrictSchema):
    slug: str = Field(min_length=1, max_length=60, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    name: str = Field(min_length=1, max_length=100)
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        if not value.strip():
            raise ValueError("Введите название")
        return value.strip()


class CategoryUpdate(Patch):
    slug: str | None = Field(
        default=None, min_length=1, max_length=60, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
    )
    name: str | None = Field(default=None, min_length=1, max_length=100)
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        return CategoryCreate.clean_name(value) if value is not None else value


class CategoryRead(ReadModel):
    id: UUID
    slug: str
    name: str
    is_active: bool


class ServiceCreate(StrictSchema):
    category_id: UUID
    name: str = Field(min_length=1, max_length=150)
    description: str = Field(default="", max_length=3000)
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        return CategoryCreate.clean_name(value)


class ServiceUpdate(Patch):
    category_id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=3000)
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        return CategoryCreate.clean_name(value) if value is not None else value


class ServiceRead(ReadModel):
    id: UUID
    category_id: UUID
    name: str
    description: str
    is_active: bool


def image_url(value):
    if value is None:
        return value
    parsed = urlsplit(value)
    if not (
        (parsed.scheme in {"http", "https"} and parsed.hostname and parsed.username is None)
        or (value.startswith("/images/") and not parsed.scheme and not parsed.netloc)
    ):
        raise ValueError("Используйте HTTP(S) URL изображения")
    return value


class MasterUpdate(Patch):
    bio: str | None = Field(default=None, max_length=3000)
    timezone: str | None = Field(default=None, max_length=64)
    address: str | None = Field(default=None, max_length=300)
    avatar_url: str | None = Field(default=None, max_length=1000)
    is_published: bool | None = None

    @field_validator("timezone")
    @classmethod
    def timezone_exists(cls, value):
        if value is not None:
            try:
                ZoneInfo(value)
            except (ZoneInfoNotFoundError, ValueError) as exc:
                raise ValueError("Неизвестный часовой пояс IANA") from exc
        return value

    @field_validator("avatar_url")
    @classmethod
    def safe_image(cls, value):
        return image_url(value)


class MasterRead(ReadModel):
    id: UUID
    display_name: str
    bio: str
    timezone: str
    address: str
    avatar_url: str | None
    is_demo: bool
    price_from: Decimal | None = None
    rating: float | None = None
    review_count: int = 0


class OfferCreate(StrictSchema):
    service_id: UUID
    price: Decimal = Field(
        ge=0, le=9999999999, max_digits=12, decimal_places=2, allow_inf_nan=False
    )
    duration_minutes: int = Field(ge=15, le=720, multiple_of=15)
    is_active: bool = True


class OfferUpdate(Patch):
    price: Decimal | None = Field(
        default=None, ge=0, le=9999999999, max_digits=12, decimal_places=2, allow_inf_nan=False
    )
    duration_minutes: int | None = Field(default=None, ge=15, le=720, multiple_of=15)
    is_active: bool | None = None


class OfferRead(ReadModel):
    id: UUID
    master_id: UUID
    service_id: UUID
    name: str
    description: str
    category_id: UUID
    price: Decimal
    duration_minutes: int
    is_active: bool


def local_time(value: time) -> time:
    if value.tzinfo is not None or value.second or value.microsecond or value.minute % 15:
        raise ValueError("Местное время должно быть кратно 15 минутам, без timezone")
    return value


class ScheduleCreate(StrictSchema):
    weekday: int = Field(ge=0, le=6)
    starts_local: time
    ends_local: time

    @field_validator("starts_local", "ends_local")
    @classmethod
    def validate_time(cls, value):
        return local_time(value)

    @model_validator(mode="after")
    def interval(self):
        if self.starts_local >= self.ends_local:
            raise ValueError(
                "Начало должно быть раньше окончания; ночные интервалы пока не поддерживаются"
            )
        return self


class ScheduleUpdate(Patch):
    weekday: int | None = Field(default=None, ge=0, le=6)
    starts_local: time | None = None
    ends_local: time | None = None

    @field_validator("starts_local", "ends_local")
    @classmethod
    def validate_time(cls, value):
        return local_time(value) if value is not None else value


class ScheduleRead(ReadModel):
    id: UUID
    weekday: int
    starts_local: time
    ends_local: time


class ExceptionCreate(StrictSchema):
    local_date: date
    is_closed: bool
    starts_local: time | None = None
    ends_local: time | None = None

    @field_validator("starts_local", "ends_local")
    @classmethod
    def validate_time(cls, value):
        return local_time(value) if value is not None else value

    @model_validator(mode="after")
    def interval(self):
        if self.is_closed:
            if self.starts_local is not None or self.ends_local is not None:
                raise ValueError("Для выходного не указываются часы")
        elif (
            self.starts_local is None
            or self.ends_local is None
            or self.starts_local >= self.ends_local
        ):
            raise ValueError("Укажите корректный рабочий интервал")
        return self


class ExceptionUpdate(StrictSchema):
    local_date: date | None = None
    is_closed: bool | None = None
    starts_local: time | None = None
    ends_local: time | None = None

    @field_validator("starts_local", "ends_local")
    @classmethod
    def validate_time(cls, value):
        return local_time(value) if value is not None else value

    @model_validator(mode="after")
    def supplied(self):
        if not self.model_fields_set or any(
            getattr(self, key) is None
            for key in self.model_fields_set & {"local_date", "is_closed"}
        ):
            raise ValueError("Укажите корректные изменения")
        return self


class ExceptionRead(ReadModel):
    id: UUID
    local_date: date
    is_closed: bool
    starts_local: time | None
    ends_local: time | None


class Slot(BaseModel):
    starts_at: datetime
    ends_at: datetime


class AvailabilityRead(BaseModel):
    date: date
    timezone: str
    master_service_id: UUID
    duration_minutes: int
    slots: list[Slot]


class BookingCreate(StrictSchema):
    master_service_id: UUID
    starts_at: AwareDatetime


class BookingUpdate(StrictSchema):
    status: Literal["CANCELLED", "COMPLETED"]
    cancellation_reason: str | None = Field(default=None, min_length=1, max_length=500)

    @field_validator("cancellation_reason")
    @classmethod
    def clean_reason(cls, value):
        if value is not None:
            if not value.strip():
                raise ValueError("Укажите причину отмены")
            return value.strip()
        return value


class BookingRead(ReadModel):
    id: UUID
    client_id: UUID
    master_id: UUID
    master_service_id: UUID
    client_name: str
    master_name: str
    service_name: str
    starts_at: datetime
    ends_at: datetime
    timezone: str
    price: Decimal
    currency: str
    duration_minutes: int
    status: str
    cancellation_reason: str | None


class PortfolioCreate(StrictSchema):
    url: str = Field(max_length=1000)
    alt_text: str = Field(min_length=1, max_length=300)
    source_url: str | None = Field(default=None, max_length=1000)
    license: str = Field(min_length=1, max_length=150)
    position: int = Field(default=0, ge=0)

    @field_validator("url", "source_url")
    @classmethod
    def safe_url(cls, value):
        return image_url(value)


class PortfolioUpdate(Patch):
    alt_text: str | None = Field(default=None, min_length=1, max_length=300)
    position: int | None = Field(default=None, ge=0)


class PortfolioRead(ReadModel):
    id: UUID
    url: str
    alt_text: str
    source_url: str | None
    license: str
    position: int


class ReviewCreate(StrictSchema):
    booking_id: UUID
    rating: int = Field(ge=1, le=5)
    text: str = Field(min_length=1, max_length=3000)


class ReviewUpdate(Patch):
    rating: int | None = Field(default=None, ge=1, le=5)
    text: str | None = Field(default=None, min_length=1, max_length=3000)


class ReviewRead(ReadModel):
    id: UUID
    rating: int
    text: str
    author_name: str
    created_at: datetime


class OwnReviewRead(ReviewRead):
    booking_id: UUID


class AdminUserRead(ReadModel):
    id: UUID
    email: str
    display_name: str
    role: str
    is_active: bool


class UserStatusUpdate(StrictSchema):
    is_active: bool


class VisibilityUpdate(StrictSchema):
    is_published: bool
