"""Pure IANA calendar calculations: no database or HTTP dependencies."""

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

MINUTE = timedelta(minutes=1)


def working_minutes(day: date, windows: list[tuple[time, time]], zone: ZoneInfo) -> set[datetime]:
    result: set[datetime] = set()
    for starts, ends in windows:
        point = datetime.combine(day, starts)
        stop = datetime.combine(day, ends)
        while point < stop:
            for fold in (0, 1):
                utc = point.replace(tzinfo=zone, fold=fold).astimezone(UTC)
                # Nonexistent local times do not survive the UTC round-trip.
                if utc.astimezone(zone).replace(tzinfo=None) == point:
                    result.add(utc)
            point += MINUTE
    return result


def interval_fits(starts: datetime, duration: int, working: set[datetime]) -> bool:
    return all(starts + MINUTE * index in working for index in range(duration))


def available_starts(
    working: set[datetime], duration: int, busy, zone: ZoneInfo, now: datetime
) -> list[datetime]:
    result = []
    for starts in sorted(working):
        local = starts.astimezone(zone)
        if local.minute % 15 or starts <= now:
            continue
        ends = starts + MINUTE * duration
        if interval_fits(starts, duration, working) and not any(
            starts < stop and ends > begin for begin, stop in busy
        ):
            result.append(starts)
    return result
