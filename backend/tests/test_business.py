from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from threading import Barrier
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from auth_helpers import AuthAPI
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.core.security import access_token
from app.db.models import Category, MasterProfile, MasterService, Schedule, Service, User
from app.db.session import get_db
from app.main import create_app
from app.services import appointments


@pytest.fixture
def world(api, db, monkeypatch):
    monkeypatch.setattr(appointments, "now_utc", lambda: datetime(2030, 1, 7, tzinfo=UTC))
    actors = {}
    for name, role in [
        ("admin", "ADMIN"),
        ("master", "MASTER"),
        ("other_master", "MASTER"),
        ("client", "CLIENT"),
        ("other_client", "CLIENT"),
    ]:
        actor = User(
            email=f"{name}@example.test",
            display_name=name,
            role=role,
            password_hash="!test-disabled",
        )
        db.add(actor)
        db.flush()
        actors[name] = actor
    master = MasterProfile(user_id=actors["master"].id, is_published=True, address="Test City")
    other_master = MasterProfile(user_id=actors["other_master"].id)
    category = Category(name="Hair", slug="hair")
    db.add_all([master, other_master, category])
    db.flush()
    service = Service(name="Haircut", category_id=category.id)
    db.add(service)
    db.flush()
    offered = MasterService(
        master_id=master.id, service_id=service.id, price=Decimal("10000"), duration_minutes=60
    )
    schedule = Schedule(
        master_id=master.id,
        weekday=date(2030, 1, 8).weekday(),
        starts_local=datetime.strptime("09:00", "%H:%M").time(),
        ends_local=datetime.strptime("18:00", "%H:%M").time(),
    )
    db.add_all([offered, schedule])
    db.commit()

    class World:
        day = "2030-01-08"

        def as_actor(self, name):
            actor = actors[name]
            api.token = access_token(actor.id, actor.role)
            return api

        def slots(self):
            return api.request(
                "GET",
                f"/masters/{master.id}/availability",
                params={"master_service_id": str(offered.id), "date": self.day},
            )

        def book(self, starts=None, key=None):
            return api.request(
                "POST",
                "/bookings",
                headers={"Idempotency-Key": str(key or uuid4())},
                json={
                    "master_service_id": str(offered.id),
                    "starts_at": starts or self.slots().json()["slots"][0]["starts_at"],
                },
            )

    result = World()
    result.actors, result.master, result.other_master = actors, master, other_master
    result.category, result.service, result.offer, result.schedule = (
        category,
        service,
        offered,
        schedule,
    )
    result.as_actor("client")
    return result


def test_booking_full_api_flow_and_slot_release(world):
    api = world.as_actor("client")
    available = world.slots()
    assert available.status_code == 200 and len(available.json()["slots"]) == 33
    chosen = available.json()["slots"][0]["starts_at"]
    created = world.book(chosen)
    assert created.status_code == 201, created.text
    booking = created.json()
    assert Decimal(booking["price"]) == 10000 and booking["duration_minutes"] == 60
    assert booking["timezone"] == "Asia/Qyzylorda"
    assert api.request("GET", "/bookings").json()["items"][0]["id"] == booking["id"]
    assert world.book(chosen).status_code == 409
    world.as_actor("master")
    assert api.request("GET", "/master/bookings").json()["items"][0]["id"] == booking["id"]
    world.as_actor("client")
    assert (
        api.request("PATCH", f"/bookings/{booking['id']}", json={"status": "CANCELLED"}).status_code
        == 200
    )
    assert chosen in [item["starts_at"] for item in world.slots().json()["slots"]]


def test_same_key_returns_same_booking_and_changed_payload_conflicts(world):
    key = uuid4()
    first = world.book(key=key)
    original = first.json()
    replay = world.book(starts=original["starts_at"], key=key)
    assert replay.status_code == 200 and replay.json()["id"] == original["id"]
    different = world.book(starts="2030-01-08T06:00:00Z", key=key)
    assert (
        different.status_code == 409 and different.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"
    )


def test_naive_timestamp_missing_key_and_extra_price_are_rejected(world):
    api = world.as_actor("client")
    data = {"master_service_id": str(world.offer.id), "starts_at": "2030-01-08T04:00:00"}
    assert (
        api.request(
            "POST", "/bookings", headers={"Idempotency-Key": str(uuid4())}, json=data
        ).status_code
        == 422
    )
    data["starts_at"] += "Z"
    assert api.request("POST", "/bookings", json=data).status_code == 422
    data["price"] = 1
    assert (
        api.request(
            "POST", "/bookings", headers={"Idempotency-Key": str(uuid4())}, json=data
        ).status_code
        == 422
    )


def test_other_client_and_other_master_cannot_read_or_cancel(world):
    item = world.book().json()
    for name in ["other_client", "other_master"]:
        api = world.as_actor(name)
        assert api.request("GET", f"/bookings/{item['id']}").status_code == 404
        assert (
            api.request(
                "PATCH", f"/bookings/{item['id']}", json={"status": "CANCELLED"}
            ).status_code
            == 404
        )


def test_schedule_changes_cannot_displace_a_booking(world):
    world.book()
    api = world.as_actor("master")
    assert (
        api.request(
            "PATCH", f"/master/schedules/{world.schedule.id}", json={"starts_local": "10:00"}
        ).status_code
        == 409
    )
    assert api.request("DELETE", f"/master/schedules/{world.schedule.id}").status_code == 409
    closed = api.request(
        "POST", "/master/schedule-exceptions", json={"local_date": world.day, "is_closed": True}
    )
    assert closed.status_code == 409
    assert api.request("GET", "/master/schedules").json()["items"][0]["starts_local"] == "09:00:00"


def test_exception_override_and_deletion_restore_availability(world):
    api = world.as_actor("master")
    closed = api.request(
        "POST", "/master/schedule-exceptions", json={"local_date": world.day, "is_closed": True}
    )
    assert closed.status_code == 201, closed.text
    assert world.slots().json()["slots"] == []
    override = api.request(
        "PATCH",
        f"/master/schedule-exceptions/{closed.json()['id']}",
        json={"is_closed": False, "starts_local": "10:00", "ends_local": "12:00"},
    )
    assert override.status_code == 200, override.text
    assert len(world.slots().json()["slots"]) == 5
    assert (
        api.request("DELETE", f"/master/schedule-exceptions/{closed.json()['id']}").status_code
        == 204
    )
    assert len(world.slots().json()["slots"]) == 33


def test_calendar_validates_work_hours_and_horizon(world):
    api = world.as_actor("master")
    for payload in [
        {"weekday": 0, "starts_local": "18:00", "ends_local": "09:00"},
        {"weekday": 7, "starts_local": "09:00", "ends_local": "18:00"},
        {"weekday": 0, "starts_local": "09:03", "ends_local": "18:00"},
        {"weekday": 0, "starts_local": "09:00:00+05:00", "ends_local": "18:00"},
    ]:
        assert api.request("POST", "/master/schedules", json=payload).status_code == 422
    assert world.book("2030-01-08T03:00:00Z").status_code == 403  # MASTER may not book.
    world.as_actor("client")
    assert world.book("2030-01-08T03:00:00Z").status_code == 409
    assert (
        api.request(
            "GET",
            f"/masters/{world.master.id}/availability",
            params={"master_service_id": str(world.offer.id), "date": "2031-01-01"},
        ).status_code
        == 422
    )


def test_price_duration_and_timezone_snapshots_are_stable(world):
    item = world.book().json()
    api = world.as_actor("master")
    assert (
        api.request(
            "PATCH",
            f"/master/services/{world.offer.id}",
            json={"price": "20000", "duration_minutes": 90},
        ).status_code
        == 200
    )
    assert api.request("PATCH", "/master/profile", json={"timezone": "UTC"}).status_code == 409
    world.as_actor("client")
    saved = api.request("GET", f"/bookings/{item['id']}").json()
    assert Decimal(saved["price"]) == 10000 and saved["duration_minutes"] == 60
    api.request("PATCH", f"/bookings/{item['id']}", json={"status": "CANCELLED"})
    world.as_actor("master")
    assert api.request("PATCH", "/master/profile", json={"timezone": "UTC"}).status_code == 200
    assert api.request("GET", f"/bookings/{item['id']}").json()["timezone"] == "Asia/Qyzylorda"


def test_catalog_admin_crud_and_referential_integrity(world):
    api = world.as_actor("client")
    assert (
        api.request("POST", "/categories", json={"name": "Nails", "slug": "nails"}).status_code
        == 403
    )
    world.as_actor("admin")
    category = api.request("POST", "/categories", json={"name": "Nails", "slug": "nails"})
    assert category.status_code == 201
    category_id = category.json()["id"]
    service = api.request(
        "POST", "/services", json={"category_id": category_id, "name": "Manicure"}
    )
    assert service.status_code == 201
    service_id = service.json()["id"]
    assert (
        api.request("PATCH", f"/services/{service_id}", json={"description": "Care"}).status_code
        == 200
    )
    assert api.request("DELETE", f"/categories/{category_id}").status_code == 409
    assert (
        api.request("PATCH", f"/categories/{category_id}", json={"is_active": False}).status_code
        == 200
    )
    assert api.request("GET", f"/services/{service_id}").status_code == 404
    assert api.request("GET", "/admin/categories").json()["total"] == 2
    assert api.request("DELETE", f"/services/{service_id}").status_code == 204
    assert api.request("DELETE", f"/categories/{category_id}").status_code == 204


def test_master_owns_offers_and_schedule_records(world):
    api = world.as_actor("other_master")
    assert (
        api.request("PATCH", f"/master/services/{world.offer.id}", json={"price": "1"}).status_code
        == 404
    )
    assert api.request("DELETE", f"/master/schedules/{world.schedule.id}").status_code == 404
    created = api.request(
        "POST",
        "/master/services",
        json={"service_id": str(world.service.id), "price": "5000", "duration_minutes": 30},
    )
    assert created.status_code == 201
    assert api.request("GET", "/master/services").json()["total"] == 1
    assert api.request("DELETE", f"/master/services/{created.json()['id']}").status_code == 204


def test_offer_deactivation_keeps_history(world):
    item = world.book().json()
    api = world.as_actor("master")
    assert api.request("DELETE", f"/master/services/{world.offer.id}").status_code == 204
    assert api.request("GET", f"/bookings/{item['id']}").status_code == 200
    world.as_actor("client")
    assert world.book(item["starts_at"]).status_code == 404


def test_favorites_are_private_and_idempotent(world):
    api = world.as_actor("client")
    url = f"/favorites/{world.master.id}"
    assert api.request("PUT", url).status_code == 204
    assert api.request("PUT", url).status_code == 204
    listing = api.request("GET", "/favorites")
    assert listing.status_code == 200 and listing.json()["total"] == 1, listing.text
    world.as_actor("other_client")
    assert api.request("GET", "/favorites").json()["total"] == 0
    world.as_actor("client")
    assert api.request("DELETE", url).status_code == 204
    assert api.request("GET", "/favorites").json()["total"] == 0


def test_review_requires_own_completed_visit_and_updates_rating(world, monkeypatch):
    item = world.book().json()
    api = world.as_actor("client")
    body = {"booking_id": item["id"], "rating": 4, "text": "Good visit"}
    assert api.request("POST", "/reviews", json=body).status_code == 409
    world.as_actor("master")
    assert (
        api.request("PATCH", f"/bookings/{item['id']}", json={"status": "COMPLETED"}).status_code
        == 409
    )
    end = datetime.fromisoformat(item["ends_at"].replace("Z", "+00:00"))
    monkeypatch.setattr(appointments, "now_utc", lambda: end + timedelta(minutes=1))
    world.as_actor("client")
    assert (
        api.request("PATCH", f"/bookings/{item['id']}", json={"status": "COMPLETED"}).status_code
        == 403
    )
    world.as_actor("master")
    assert (
        api.request("PATCH", f"/bookings/{item['id']}", json={"status": "COMPLETED"}).status_code
        == 200
    )
    world.as_actor("client")
    review = api.request("POST", "/reviews", json=body)
    assert review.status_code == 201, review.text
    assert api.request("POST", "/reviews", json=body).status_code == 409
    profile = api.request("GET", f"/masters/{world.master.id}").json()
    assert profile["rating"] == 4 and profile["review_count"] == 1
    assert api.request("GET", f"/masters/{world.master.id}/reviews").json()["total"] == 1
    review_id = review.json()["id"]
    world.as_actor("other_client")
    assert api.request("PATCH", f"/reviews/{review_id}", json={"rating": 5}).status_code == 404
    world.as_actor("client")
    assert api.request("PATCH", f"/reviews/{review_id}", json={"rating": 5}).status_code == 200
    world.as_actor("admin")
    assert api.request("DELETE", f"/reviews/{review_id}").status_code == 204
    assert api.request("GET", f"/masters/{world.master.id}").json()["rating"] is None


def test_portfolio_crud_and_url_validation(world):
    api = world.as_actor("master")
    body = {"url": "javascript:alert(1)", "alt_text": "Work", "license": "Test"}
    assert api.request("POST", "/master/portfolio", json=body).status_code == 422
    body["url"] = "/images/beauty-editorial.jpg"
    response = api.request("POST", "/master/portfolio", json=body)
    assert response.status_code == 201, response.text
    identifier = response.json()["id"]
    assert api.request("GET", f"/masters/{world.master.id}/portfolio").json()["total"] == 1
    world.as_actor("other_master")
    assert api.request("DELETE", f"/master/portfolio/{identifier}").status_code == 404
    world.as_actor("master")
    assert (
        api.request(
            "PATCH", f"/master/portfolio/{identifier}", json={"alt_text": "Updated"}
        ).status_code
        == 200
    )
    assert api.request("DELETE", f"/master/portfolio/{identifier}").status_code == 204


def test_admin_moderation_and_blocked_master_visibility(world):
    api = world.as_actor("admin")
    assert api.request("GET", "/admin/users").json()["total"] == 5
    assert api.request("GET", "/admin/masters").json()["total"] == 2
    assert (
        api.request(
            "PATCH", f"/admin/users/{world.actors['admin'].id}", json={"is_active": False}
        ).status_code
        == 409
    )
    assert (
        api.request(
            "PATCH", f"/admin/masters/{world.master.id}", json={"is_published": False}
        ).status_code
        == 200
    )
    assert api.request("GET", f"/masters/{world.master.id}").status_code == 404
    api.request("PATCH", f"/admin/masters/{world.master.id}", json={"is_published": True})
    assert (
        api.request(
            "PATCH", f"/admin/users/{world.actors['master'].id}", json={"is_active": False}
        ).status_code
        == 200
    )
    assert api.request("GET", "/masters").json()["total"] == 0


def test_search_price_sort_pagination_and_no_n_plus_one(world, db, pg_engine):
    for number in range(25):
        user = User(
            email=f"bulk{number}@example.test",
            display_name=f"Bulk {number:02d}",
            role="MASTER",
            password_hash="!test-disabled",
        )
        db.add(user)
        db.flush()
        master = MasterProfile(user_id=user.id, is_published=True)
        db.add(master)
        db.flush()
        db.add(
            MasterService(
                master_id=master.id,
                service_id=world.service.id,
                price=1000 + number,
                duration_minutes=30,
            )
        )
    db.commit()
    api = world.as_actor("client")
    calls = []

    def record(conn, cursor, statement, params, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            calls.append(statement)

    event.listen(pg_engine, "before_cursor_execute", record)
    try:
        response = api.request(
            "GET", "/masters", params={"search": "Bulk", "page_size": 5, "page": 2}
        )
        assert response.status_code == 200, response.text
        assert response.json()["total"] == 25 and len(response.json()["items"]) == 5
        assert len(calls) == 2  # Count and result, independent of the number of masters.
    finally:
        event.remove(pg_engine, "before_cursor_execute", record)
    filtered = api.request(
        "GET", "/masters", params={"min_price": "1003", "max_price": "1006", "sort": "price_desc"}
    ).json()
    assert filtered["total"] == 4 and Decimal(filtered["items"][0]["price_from"]) == 1006
    assert api.request("GET", "/masters", params={"page_size": 51}).status_code == 422
    assert (
        api.request("GET", "/masters", params={"min_price": 20, "max_price": 10}).status_code == 422
    )


def test_timezone_can_map_local_date_to_previous_utc_day(world):
    api = world.as_actor("master")
    assert (
        api.request("PATCH", "/master/profile", json={"timezone": "Pacific/Kiritimati"}).status_code
        == 200
    )
    slots = world.slots().json()["slots"]
    start = datetime.fromisoformat(slots[0]["starts_at"].replace("Z", "+00:00"))
    assert start.date() == date(2030, 1, 7)
    assert start.astimezone(ZoneInfo("Pacific/Kiritimati")).date() == date(2030, 1, 8)


def test_api_concurrent_requests_create_exactly_one_booking(world, pg_engine):
    chosen = world.slots().json()["slots"][0]["starts_at"]
    token = access_token(world.actors["client"].id, "CLIENT")
    app = create_app()

    def independent_db():
        with Session(pg_engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_db] = independent_db
    barrier = Barrier(2)

    def create():
        client = AuthAPI(app)
        client.token = token
        barrier.wait(timeout=10)
        response = client.request(
            "POST",
            "/bookings",
            headers={"Idempotency-Key": str(uuid4())},
            json={"master_service_id": str(world.offer.id), "starts_at": chosen},
        )
        return response.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(lambda _: create(), range(2)))
    assert sorted(statuses) == [201, 409]


def test_admin_cancellation_requires_reason_and_preserves_status_rules(world):
    item = world.book().json()
    api = world.as_actor("admin")
    assert api.request("GET", "/admin/bookings").json()["total"] == 1
    assert (
        api.request("PATCH", f"/bookings/{item['id']}", json={"status": "CANCELLED"}).status_code
        == 422
    )
    assert (
        api.request(
            "PATCH",
            f"/bookings/{item['id']}",
            json={"status": "CANCELLED", "cancellation_reason": "Test reason"},
        ).status_code
        == 200
    )
    assert (
        api.request("PATCH", f"/bookings/{item['id']}", json={"status": "COMPLETED"}).status_code
        == 409
    )
