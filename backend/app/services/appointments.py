from datetime import UTC, date, datetime, timedelta
from hashlib import sha256
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models import Booking, Schedule, ScheduleException
from app.repositories.business import BusinessRepository
from app.schemas.business import AvailabilityRead, ExceptionCreate, ScheduleCreate, Slot
from app.services.calendar import MINUTE, available_starts, interval_fits, working_minutes
from app.services.catalog import CatalogService
from app.services.common import apply_patch, change, found


def now_utc():
    return datetime.now(UTC)


class AppointmentService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = BusinessRepository(db)
        self.catalog = CatalogService(db)

    def check_day(self, master, day: date):
        today = now_utc().astimezone(ZoneInfo(master.timezone)).date()
        if not today <= day <= today + timedelta(days=90):
            raise AppError(422, "DATE_OUT_OF_RANGE", "Выберите дату в ближайшие 90 дней.")

    def slots(self, master, offer, day):
        self.check_day(master, day)
        zone = ZoneInfo(master.timezone)
        work = working_minutes(day, self.repo.windows(master.id, day), zone)
        if not work:
            return []
        busy = self.repo.busy(master.id, min(work), max(work) + MINUTE)
        return available_starts(work, offer.duration_minutes, busy, zone, now_utc())

    def public_offer(self, master_id, identifier):
        offer = found(self.repo.offer(identifier))
        if offer.master_id != master_id or not offer.is_active:
            raise AppError(404, "NOT_FOUND", "Услуга мастера не найдена.")
        self.catalog.service(offer.service_id)
        return offer

    def availability(self, master_id, offer_id, day):
        self.catalog.public_master(master_id)
        master = found(self.repo.master(master_id))
        offer = self.public_offer(master_id, offer_id)
        slots = self.slots(master, offer, day)
        return AvailabilityRead(
            date=day,
            timezone=master.timezone,
            master_service_id=offer.id,
            duration_minutes=offer.duration_minutes,
            slots=[
                Slot(starts_at=value, ends_at=value + MINUTE * offer.duration_minutes)
                for value in slots
            ],
        )

    def protect_existing(self, master):
        cache = {}
        zone = ZoneInfo(master.timezone)
        for booking in self.repo.future_bookings(master.id, now_utc()):
            day = booking.starts_at.astimezone(zone).date()
            if day not in cache:
                cache[day] = working_minutes(day, self.repo.windows(master.id, day), zone)
            if not interval_fits(booking.starts_at, booking.duration_snapshot, cache[day]):
                raise AppError(
                    409,
                    "SCHEDULE_CONFLICT",
                    "Этот график затрагивает действующую запись. Сначала отмените ее.",
                )

    def schedules(self, actor, page, size):
        master = self.catalog.own_master(actor)
        return self.repo.schedules(master.id, page, size)

    def create_schedule(self, actor, data):
        with change(self.db, "SCHEDULE_CONFLICT", "Рабочие интервалы пересекаются."):
            master = self.catalog.own_master(actor, lock=True)
            item = Schedule(master_id=master.id, **data.model_dump())
            self.db.add(item)
            self.db.flush()
            self.protect_existing(master)
        return item

    def edit_schedule(self, actor, identifier, data=None, *, delete=False):
        with change(self.db, "SCHEDULE_CONFLICT", "График конфликтует с существующими данными."):
            master = self.catalog.own_master(actor, lock=True)
            item = found(self.repo.get(Schedule, identifier))
            if item.master_id != master.id:
                raise AppError(404, "NOT_FOUND", "Интервал не найден.")
            if delete:
                self.db.delete(item)
            else:
                values = {
                    "weekday": item.weekday,
                    "starts_local": item.starts_local,
                    "ends_local": item.ends_local,
                }
                values.update(data.model_dump(exclude_unset=True))
                apply_patch(item, ScheduleCreate(**values).model_dump())
            self.db.flush()
            self.protect_existing(master)
        return item

    def exceptions(self, actor, page, size, from_date, to_date):
        master = self.catalog.own_master(actor)
        from_date = from_date or now_utc().astimezone(ZoneInfo(master.timezone)).date()
        to_date = to_date or from_date + timedelta(days=90)
        if from_date > to_date or (to_date - from_date).days > 366:
            raise AppError(422, "INVALID_DATE_RANGE", "Укажите диапазон не более года.")
        return self.repo.exceptions(master.id, page, size, from_date, to_date)

    def create_exception(self, actor, data):
        with change(
            self.db, "SCHEDULE_CONFLICT", "Исключение конфликтует с существующими данными."
        ):
            master = self.catalog.own_master(actor, lock=True)
            item = ScheduleException(master_id=master.id, **data.model_dump())
            self.db.add(item)
            self.db.flush()
            self.protect_existing(master)
        return item

    def edit_exception(self, actor, identifier, data=None, *, delete=False):
        with change(
            self.db, "SCHEDULE_CONFLICT", "Исключение конфликтует с действующими записями."
        ):
            master = self.catalog.own_master(actor, lock=True)
            item = found(self.repo.get(ScheduleException, identifier))
            if item.master_id != master.id:
                raise AppError(404, "NOT_FOUND", "Исключение не найдено.")
            if delete:
                self.db.delete(item)
            else:
                values = {
                    name: getattr(item, name)
                    for name in ["local_date", "is_closed", "starts_local", "ends_local"]
                }
                values.update(data.model_dump(exclude_unset=True))
                apply_patch(item, ExceptionCreate(**values).model_dump())
            self.db.flush()
            self.protect_existing(master)
        return item

    def create_booking(self, actor, data, key):
        starts = data.starts_at.astimezone(UTC)
        digest = sha256(f"{data.master_service_id}|{starts.isoformat()}".encode()).hexdigest()
        with change(
            self.db, "SLOT_UNAVAILABLE", "Выбранное время уже недоступно. Выберите другое."
        ):
            client = found(self.repo.lock_user(actor.id))
            if not client.is_active or client.role != "CLIENT":
                raise AppError(403, "FORBIDDEN", "Запись доступна только активному клиенту.")
            existing = self.repo.idempotent_booking(actor.id, key)
            if existing:
                if existing.request_hash != digest:
                    raise AppError(
                        409, "IDEMPOTENCY_CONFLICT", "Этот ключ уже использован для другой записи."
                    )
                identifier, created = existing.id, False
            else:
                initial = found(self.repo.offer(data.master_service_id))
                master = found(self.repo.master(initial.master_id, lock=True))
                self.catalog.public_master(master.id)
                offer = self.public_offer(
                    master.id, initial.id
                )  # Refresh after waiting for the lock.
                day = starts.astimezone(ZoneInfo(master.timezone)).date()
                if starts not in self.slots(master, offer, day):
                    raise AppError(
                        409,
                        "SLOT_UNAVAILABLE",
                        "Выбранное время недоступно: проверьте график и свободные слоты.",
                    )
                service = self.catalog.service(offer.service_id)
                item = Booking(
                    client_id=actor.id,
                    master_id=master.id,
                    master_service_id=offer.id,
                    starts_at=starts,
                    ends_at=starts + MINUTE * offer.duration_minutes,
                    status="CONFIRMED",
                    price_snapshot=offer.price,
                    duration_snapshot=offer.duration_minutes,
                    service_name_snapshot=service.name,
                    timezone_snapshot=master.timezone,
                    currency="KZT",
                    idempotency_key=key,
                    request_hash=digest,
                )
                self.db.add(item)
                self.db.flush()
                identifier, created = item.id, True
        return self.repo.booking_read(identifier), created

    def owned_booking(self, actor, identifier):
        item = found(self.repo.booking(identifier))
        master = found(self.repo.master(item.master_id))
        if actor.role != "ADMIN" and item.client_id != actor.id and master.user_id != actor.id:
            raise AppError(404, "NOT_FOUND", "Запись не найдена.")
        return item

    def booking(self, actor, identifier):
        self.owned_booking(actor, identifier)
        return self.repo.booking_read(identifier)

    def update_booking(self, actor, identifier, data):
        initial = self.owned_booking(actor, identifier)
        with change(self.db):
            found(self.repo.master(initial.master_id, lock=True))
            item = self.owned_booking(actor, identifier)  # Re-read after acquiring lock.
            if data.status == "COMPLETED" and actor.role not in {"MASTER", "ADMIN"}:
                raise AppError(403, "FORBIDDEN", "Посещение завершает мастер.")
            if item.status == data.status:
                return self.repo.booking_read(identifier)
            if item.status != "CONFIRMED":
                raise AppError(409, "INVALID_TRANSITION", "Статус этой записи уже изменен.")
            now = now_utc()
            if data.status == "CANCELLED":
                if item.starts_at <= now:
                    raise AppError(
                        409, "VISIT_STARTED", "Нельзя отменить уже начавшееся посещение."
                    )
                if actor.role == "ADMIN" and not data.cancellation_reason:
                    raise AppError(422, "REASON_REQUIRED", "Укажите причину отмены.")
                item.cancelled_by = actor.id
                item.cancellation_reason = data.cancellation_reason
            elif item.ends_at > now:
                raise AppError(409, "VISIT_NOT_ENDED", "Посещение еще не закончилось.")
            item.status = data.status
        return self.repo.booking_read(identifier)

    def client_bookings(self, actor, page, size, status):
        return self.repo.bookings(page, size, client_id=actor.id, status=status)

    def master_bookings(self, actor, page, size, status):
        master = self.catalog.own_master(actor)
        return self.repo.bookings(page, size, master_id=master.id, status=status)

    def admin_bookings(self, page, size, status, master_id, client_id):
        return self.repo.bookings(
            page, size, status=status, master_id=master_id, client_id=client_id
        )
