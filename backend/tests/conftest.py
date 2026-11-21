"""Integration fixtures require an explicitly isolated PostgreSQL database."""

import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from secrets import token_urlsafe
from uuid import uuid4

import pytest
from alembic.config import Config
from auth_helpers import AuthAPI
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from alembic import command
from app.core.config import get_settings
from app.db.models import Base, Category, MasterProfile, MasterService, Service, User
from app.db.session import get_db
from app.main import create_app


@pytest.fixture(scope="session")
def pg_engine():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is not configured; real PostgreSQL tests need isolated DB")
    parsed = make_url(url)
    if parsed.get_backend_name() != "postgresql" or not (parsed.database or "").endswith("_test"):
        raise RuntimeError("Integration tests require PostgreSQL database name ending in _test")
    os.environ["DATABASE_URL_UNPOOLED"] = url
    get_settings.cache_clear()
    cfg = Config("alembic.ini")
    engine = create_engine(url, hide_parameters=True)
    # Exercise every downgrade boundary, including complete rollback, on test DB only.
    command.upgrade(cfg, "head")
    for target in ["004", "003", "002", "001", "base"]:
        command.downgrade(cfg, target)
        command.upgrade(cfg, "head")
    assert set(Base.metadata.tables).issubset(inspect(engine).get_table_names())
    yield engine
    engine.dispose()
    get_settings.cache_clear()


@pytest.fixture
def db(pg_engine):
    session = Session(pg_engine, expire_on_commit=False)
    yield session
    session.close()
    # This fixture is guarded above and is never enabled against the application DB.
    names = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    with pg_engine.begin() as connection:
        connection.execute(text(f"TRUNCATE TABLE {names} CASCADE"))


@pytest.fixture
def offer(db):
    client = User(
        email="client@example.test",
        password_hash="test-only-unusable",
        role="CLIENT",
        display_name="Client",
    )
    owner = User(
        email="master@example.test",
        password_hash="test-only-unusable",
        role="MASTER",
        display_name="Master",
    )
    category = Category(slug="hair", name="Hair")
    db.add_all([client, owner, category])
    db.flush()
    master = MasterProfile(user_id=owner.id)
    service = Service(category_id=category.id, name="Haircut")
    db.add_all([master, service])
    db.flush()
    offered = MasterService(
        master_id=master.id, service_id=service.id, price=Decimal("10000.00"), duration_minutes=60
    )
    db.add(offered)
    db.flush()
    return client, master, offered


def booking_values(offer, offset=0):
    client, master, offered = offer
    start = datetime(2030, 1, 15, 10, tzinfo=UTC) + timedelta(minutes=offset)
    return dict(
        client_id=client.id,
        master_id=master.id,
        master_service_id=offered.id,
        starts_at=start,
        ends_at=start + timedelta(hours=1),
        status="CONFIRMED",
        price_snapshot=offered.price,
        duration_snapshot=60,
        service_name_snapshot="Haircut",
        currency="KZT",
        idempotency_key=uuid4(),
        request_hash="a" * 64,
    )


@pytest.fixture
def api(db, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", token_urlsafe(48))
    monkeypatch.setenv("COOKIE_SECURE", "true")
    monkeypatch.setenv("AUTH_RATE_LIMIT", "100")
    get_settings.cache_clear()
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    yield AuthAPI(app)
    app.dependency_overrides.clear()
    get_settings.cache_clear()
