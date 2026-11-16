"""Batched calendar search; reuses the booking calendar before SQL pagination."""

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.errors import AppError
from app.repositories.business import BusinessRepository
from app.services.calendar import iter_available_starts, working_minutes


def now_utc():
    return datetime.now(UTC)


class AvailabilitySearch:
    def __init__(self, repo: BusinessRepository):
        self.repo = repo

    def offer_ids(self, day: date, **filters):
        now = now_utc()
        # Each master's local calendar is checked below, including dates near UTC midnight.
        if not now.date() - timedelta(days=1) <= day <= now.date() + timedelta(days=91):
            raise AppError(422, "DATE_OUT_OF_RANGE", "Выберите дату в ближайшие 90 дней.")
        offers = self.repo.calendar_candidates(**filters)
        if not offers:
            return []
        identifiers = list({item.master_id for item in offers})
        schedules, exceptions, busy = self.repo.calendar_batch(identifiers, day)
        work_cache, available = {}, {}
        result = []
        for offer in offers:
            zone = ZoneInfo(offer.timezone)
            today = now.astimezone(zone).date()
            if not today <= day <= today + timedelta(days=90):
                continue
            override = exceptions.get(offer.master_id)
            windows = (
                ([] if override.is_closed else [(override.starts_local, override.ends_local)])
                if override
                else schedules.get(offer.master_id, [])
            )
            pattern = (offer.timezone, tuple(windows))
            if pattern not in work_cache:
                work_cache[pattern] = working_minutes(day, windows, zone)
            key = (offer.master_id, offer.duration_minutes)
            if key not in available:
                available[key] = (
                    next(
                        iter_available_starts(
                            work_cache[pattern],
                            offer.duration_minutes,
                            busy.get(offer.master_id, []),
                            zone,
                            now,
                        ),
                        None,
                    )
                    is not None
                )
            if available[key]:
                result.append(offer.id)
        return result
