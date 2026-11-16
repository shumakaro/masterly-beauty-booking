from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

from app.services.calendar import available_starts, interval_fits, working_minutes


def test_nonexistent_spring_times_are_not_slots():
    zone = ZoneInfo("America/New_York")
    work = working_minutes(date(2026, 3, 8), [(time(1), time(4))], zone)
    assert len(work) == 120
    slots = available_starts(work, 60, [], zone, datetime(2020, 1, 1, tzinfo=UTC))
    assert slots and all(value.astimezone(zone).hour != 2 for value in slots)


def test_fall_repeated_hour_has_distinct_utc_slots():
    zone = ZoneInfo("America/New_York")
    work = working_minutes(date(2026, 11, 1), [(time(0), time(3))], zone)
    assert len(work) == 240
    slots = available_starts(work, 60, [], zone, datetime(2020, 1, 1, tzinfo=UTC))
    repeated = [value for value in slots if value.astimezone(zone).time() == time(1)]
    assert len(repeated) == 2 and {value.astimezone(zone).fold for value in repeated} == {0, 1}


def test_adjacent_work_intervals_are_continuous_but_breaks_are_not():
    zone = ZoneInfo("Asia/Qyzylorda")
    day = date(2030, 1, 8)
    work = working_minutes(day, [(time(9), time(10)), (time(10), time(11))], zone)
    starts = datetime(2030, 1, 8, 4, 30, tzinfo=UTC)
    assert interval_fits(starts, 90, work)
    work_with_break = working_minutes(day, [(time(9), time(10)), (time(10, 15), time(11))], zone)
    assert not interval_fits(starts, 90, work_with_break)
