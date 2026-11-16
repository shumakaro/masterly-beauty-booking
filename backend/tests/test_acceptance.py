from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import event

from app.db.models import MasterProfile, MasterService, Schedule, Service, User
from app.services import appointments, availability_search

pytest_plugins = ["test_business"]


def test_date_search_filters_matching_offers_and_releases_cancelled_time(world, db):
    world.schedule.ends_local = time(9, 30)
    service = Service(category_id=world.category.id, name="Short care")
    db.add(service)
    db.flush()
    offer = MasterService(
        master_id=world.master.id, service_id=service.id, price=20000, duration_minutes=30
    )
    db.add(offer)
    db.commit()
    api = world.as_actor("client")
    result = api.request("GET", "/masters", params={"available_on": world.day}).json()
    assert result["total"] == 1 and Decimal(result["items"][0]["price_from"]) == 20000
    assert (
        api.request(
            "GET", "/masters", params={"available_on": world.day, "max_price": "15000"}
        ).json()["total"]
        == 0
    )
    created = api.request(
        "POST",
        "/bookings",
        headers={"Idempotency-Key": str(uuid4())},
        json={"master_service_id": str(offer.id), "starts_at": "2030-01-08T04:00:00Z"},
    )
    assert created.status_code == 201, created.text
    assert api.request("GET", "/masters", params={"available_on": world.day}).json()["total"] == 0
    assert (
        api.request(
            "PATCH", f"/bookings/{created.json()['id']}", json={"status": "CANCELLED"}
        ).status_code
        == 200
    )
    assert api.request("GET", "/masters", params={"available_on": world.day}).json()["total"] == 1
    assert api.request("GET", "/masters", params={"available_on": "invalid"}).status_code == 422
    assert api.request("GET", "/masters", params={"available_on": "2031-01-01"}).status_code == 422


def test_date_search_is_batched_and_pagination_counts_all_results(world, db, pg_engine):
    for index in range(25):
        user = User(
            email=f"dated-{index}@example.test",
            display_name=f"Dated {index:02d}",
            role="MASTER",
            password_hash="!test",
        )
        db.add(user)
        db.flush()
        master = MasterProfile(user_id=user.id, is_published=True)
        db.add(master)
        db.flush()
        db.add_all(
            [
                MasterService(
                    master_id=master.id,
                    service_id=world.service.id,
                    price=1000 + index,
                    duration_minutes=60,
                ),
                Schedule(master_id=master.id, weekday=1, starts_local=time(9), ends_local=time(18)),
            ]
        )
    db.commit()
    queries = []

    def record(_conn, _cursor, statement, _params, _context, _many):
        if statement.lstrip().upper().startswith("SELECT"):
            queries.append(statement)

    event.listen(pg_engine, "before_cursor_execute", record)
    try:
        result = world.as_actor("client").request(
            "GET",
            "/masters",
            params={"available_on": world.day, "page_size": 10, "page": 2, "sort": "price_asc"},
        )
        assert result.status_code == 200, result.text
        # Public catalog performs 6 SELECTs, independent of number of masters/offers.
        assert len(queries) == 6
    finally:
        event.remove(pg_engine, "before_cursor_execute", record)
    data = result.json()
    assert data["total"] == 26 and len(data["items"]) == 10
    assert Decimal(data["items"][0]["price_from"]) == 1010


@pytest.mark.parametrize(
    ("day", "starts", "ends", "duration", "has_time"),
    [
        (date(2026, 3, 8), time(2), time(3), 30, False),
        (date(2026, 3, 8), time(1, 30), time(3, 30), 60, True),
        (date(2026, 3, 8), time(1, 30), time(3, 30), 90, False),
        (date(2026, 11, 1), time(1), time(2), 90, True),
    ],
)
def test_date_search_and_booking_calendar_agree_across_dst(
    world, db, monkeypatch, day, starts, ends, duration, has_time
):
    now = datetime.combine(day - timedelta(days=7), time(), tzinfo=UTC)
    monkeypatch.setattr(appointments, "now_utc", lambda: now)
    monkeypatch.setattr(availability_search, "now_utc", lambda: now)
    world.master.timezone = "America/New_York"
    world.schedule.weekday = day.weekday()
    world.schedule.starts_local, world.schedule.ends_local = starts, ends
    world.offer.duration_minutes = duration
    db.commit()
    api = world.as_actor("client")
    slots = api.request(
        "GET",
        f"/masters/{world.master.id}/availability",
        params={"master_service_id": str(world.offer.id), "date": day.isoformat()},
    )
    found = api.request("GET", "/masters", params={"available_on": day.isoformat()})
    assert slots.status_code == found.status_code == 200
    assert bool(slots.json()["slots"]) == bool(found.json()["items"]) == has_time


def test_date_search_uses_each_masters_local_date_and_exceptions(world, db, monkeypatch):
    now = datetime(2030, 1, 8, 2, tzinfo=UTC)
    monkeypatch.setattr(appointments, "now_utc", lambda: now)
    monkeypatch.setattr(availability_search, "now_utc", lambda: now)
    world.master.timezone = "Pacific/Honolulu"
    world.schedule.weekday = 0
    world.schedule.starts_local, world.schedule.ends_local = time(17), time(19)
    db.commit()
    api = world.as_actor("client")
    params = {"available_on": "2030-01-07"}
    assert api.request("GET", "/masters", params=params).json()["total"] == 1
    world.as_actor("master")
    assert (
        api.request(
            "POST",
            "/master/schedule-exceptions",
            json={"local_date": "2030-01-07", "is_closed": True},
        ).status_code
        == 201
    )
    assert api.request("GET", "/masters", params=params).json()["total"] == 0


def test_overview_is_scoped_and_uses_completed_price_snapshot(world, monkeypatch):
    booking = world.book().json()
    api = world.as_actor("client")
    own = api.request("GET", "/overview").json()
    assert own["total"] == own["confirmed"] == own["upcoming"] == 1
    assert own["completed"] == 0 and Decimal(own["completed_value"]) == 0
    assert world.as_actor("other_client").request("GET", "/overview").json()["total"] == 0
    assert world.as_actor("other_master").request("GET", "/overview").json()["total"] == 0
    assert world.as_actor("master").request("GET", "/overview").json()["total"] == 1
    end = datetime.fromisoformat(booking["ends_at"].replace("Z", "+00:00"))
    monkeypatch.setattr(appointments, "now_utc", lambda: end + timedelta(minutes=1))
    assert (
        api.request("PATCH", f"/bookings/{booking['id']}", json={"status": "COMPLETED"}).status_code
        == 200
    )
    assert (
        api.request(
            "PATCH", f"/master/services/{world.offer.id}", json={"price": "9999"}
        ).status_code
        == 200
    )
    value = api.request("GET", "/overview").json()
    assert value["completed"] == 1 and value["upcoming"] == 0
    assert Decimal(value["completed_value"]) == 10000
    assert world.as_actor("admin").request("GET", "/overview").status_code == 403
    assert api.request("GET", "/admin/overview").json()["bookings"] == 1


def test_private_lists_details_and_errors_are_never_cached(world):
    api = world.as_actor("client")
    for path in ["/bookings", "/favorites", "/reviews", "/overview", f"/bookings/{uuid4()}"]:
        response = api.request("GET", path)
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["x-request-id"]
    response = api.request("GET", "/masters", params={"available_on": "invalid"})
    assert response.status_code == 422 and response.headers["cache-control"] == "no-store"
