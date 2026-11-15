from concurrent.futures import ThreadPoolExecutor
from datetime import time
from threading import Barrier
from uuid import uuid4

import pytest
from conftest import booking_values
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Booking, Favorite, MasterService, Schedule, ScheduleException, User


def test_schema_has_twelve_tables_and_three_revisions(pg_engine):
    assert len(set(inspect(pg_engine).get_table_names()) - {"alembic_version"}) == 12
    with pg_engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "003"


def test_overlap_is_rejected_by_postgresql(db, offer):
    db.add(Booking(**booking_values(offer)))
    db.flush()
    db.add(Booking(**booking_values(offer, 30)))
    with pytest.raises(IntegrityError) as error:
        db.flush()
    assert error.value.orig.sqlstate == "23P01"


def test_adjacent_intervals_are_allowed(db, offer):
    db.add_all([Booking(**booking_values(offer)), Booking(**booking_values(offer, 60))])
    db.flush()
    assert len(db.scalars(select(Booking)).all()) == 2


def test_cancellation_releases_interval(db, offer):
    original = Booking(**booking_values(offer))
    db.add(original)
    db.flush()
    original.status = "CANCELLED"
    original.cancelled_by = offer[0].id
    db.flush()
    db.add(Booking(**booking_values(offer)))
    db.flush()


def test_offer_cannot_belong_to_different_master(db, offer):
    values = booking_values(offer)
    values["master_id"] = uuid4()
    db.add(Booking(**values))
    with pytest.raises(IntegrityError):
        db.flush()


def test_negative_price_is_rejected(db, offer):
    offer[2].price = -1
    with pytest.raises(IntegrityError) as error:
        db.flush()
    assert error.value.orig.sqlstate == "23514"


def test_booking_end_must_match_duration_snapshot(db, offer):
    values = booking_values(offer)
    values["duration_snapshot"] = 30
    db.add(Booking(**values))
    with pytest.raises(IntegrityError):
        db.flush()


def test_duplicate_favorite_is_rejected(db, offer):
    client, master, _ = offer
    db.add(Favorite(client_id=client.id, master_id=master.id))
    db.flush()
    db.add(Favorite(client_id=client.id, master_id=master.id))
    with pytest.raises(IntegrityError):
        db.flush()


def test_same_idempotency_key_is_unique_per_client(db, offer):
    values = booking_values(offer)
    db.add(Booking(**values))
    db.flush()
    adjacent = booking_values(offer, 60)
    adjacent["idempotency_key"] = values["idempotency_key"]
    db.add(Booking(**adjacent))
    with pytest.raises(IntegrityError) as error:
        db.flush()
    assert error.value.orig.sqlstate == "23505"


def test_schedule_overlap_is_rejected(db, offer):
    master = offer[1]
    db.add(Schedule(master_id=master.id, weekday=0, starts_local=time(9), ends_local=time(12)))
    db.flush()
    db.add(Schedule(master_id=master.id, weekday=0, starts_local=time(11), ends_local=time(14)))
    with pytest.raises(IntegrityError) as error:
        db.flush()
    assert error.value.orig.sqlstate == "23P01"


def test_closed_exception_cannot_have_hours(db, offer):
    from datetime import date

    db.add(
        ScheduleException(
            master_id=offer[1].id,
            local_date=date(2030, 1, 1),
            is_closed=True,
            starts_local=time(9),
            ends_local=time(12),
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()


def test_email_is_normalized_at_database_boundary(db):
    db.add(
        User(
            email="Upper@Example.test", password_hash="unusable", role="CLIENT", display_name="Test"
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()


def test_real_concurrent_connections_cannot_double_book(db, offer, pg_engine):
    values = booking_values(offer)
    db.commit()  # Parent rows must be visible to both independent connections.
    barrier = Barrier(2)

    def insert():
        with Session(pg_engine) as session:
            payload = values | {"idempotency_key": uuid4()}
            session.add(Booking(**payload))
            barrier.wait(timeout=10)
            try:
                session.commit()
                return "created"
            except IntegrityError as error:
                session.rollback()
                return error.orig.sqlstate

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: insert(), range(2)))
    assert sorted(outcomes) == ["23P01", "created"]


def test_price_snapshot_survives_offer_change(db, offer):
    booking = Booking(**booking_values(offer))
    db.add(booking)
    db.flush()
    offer[2].price = 20000
    db.flush()
    db.expire_all()
    saved = db.get(Booking, booking.id)
    assert saved.price_snapshot == 10000
    assert db.get(MasterService, offer[2].id).price == 20000


def test_query_plans_for_master_and_client_indexes(db, offer):
    import json
    from datetime import timedelta
    from pathlib import Path

    from sqlalchemy import insert

    template = booking_values(offer)
    rows = []
    for index in range(3000):
        starts_at = template["starts_at"] + timedelta(hours=index)
        rows.append(
            template
            | {
                "idempotency_key": uuid4(),
                "starts_at": starts_at,
                "ends_at": starts_at + timedelta(hours=1),
            }
        )
    db.execute(insert(Booking), rows)
    db.execute(text("ANALYZE bookings"))
    plans = {}
    for label, column, identifier in [
        ("master_schedule", "master_id", offer[1].id),
        ("client_history", "client_id", offer[0].id),
    ]:
        # column comes from this fixed allowlist, never user input.
        result = db.execute(
            text(
                "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) "
                f"SELECT id, starts_at FROM bookings WHERE {column} = :identifier "
                "AND starts_at >= :cutoff ORDER BY starts_at DESC LIMIT 10"
            ),
            {"identifier": identifier, "cutoff": template["starts_at"] + timedelta(hours=1000)},
        )
        plans[label] = result.scalar_one()
    output = Path("test-results")
    output.mkdir(exist_ok=True)
    (output / "query-plans.json").write_text(json.dumps(plans, indent=2), encoding="utf-8")
    assert set(plans) == {"master_schedule", "client_history"}


def test_demo_seed_is_idempotent_and_not_published(db, pg_engine, monkeypatch):
    from app.db import seed
    from app.db.models import MasterProfile

    monkeypatch.setattr(seed, "get_engine", lambda: pg_engine)
    seed.seed_demo()
    seed.seed_demo()
    profiles = db.scalars(select(MasterProfile)).all()
    assert len(profiles) == 3
    assert all(profile.is_demo and not profile.is_published for profile in profiles)
    users = db.scalars(select(User)).all()
    assert len(users) == 3 and all(not user.is_active for user in users)
