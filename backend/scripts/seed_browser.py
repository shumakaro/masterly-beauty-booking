"""Explicit demonstration catalog for disposable browser-test databases only."""

import os
from datetime import UTC, datetime, time, timedelta
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models import (
    Booking,
    Category,
    MasterProfile,
    MasterService,
    PortfolioItem,
    Schedule,
    Service,
    User,
)


def seed_browser():
    url = os.environ["TEST_DATABASE_URL"]
    parsed = make_url(url)
    if parsed.get_backend_name() != "postgresql" or not (parsed.database or "").endswith("_test"):
        raise RuntimeError("Browser fixtures require a disposable PostgreSQL *_test database")
    engine = create_engine(url, hide_parameters=True)
    password = os.environ.get("BROWSER_TEST_PASSWORD")
    if not password or len(password) < 32:
        raise RuntimeError("Generate an ephemeral BROWSER_TEST_PASSWORD for browser fixtures")

    def identifier(key):
        return uuid5(NAMESPACE_URL, f"masterly-browser-fixture:{key}")

    with Session(engine) as db, db.begin():
        for slug, name in [("hair", "Волосы"), ("nails", "Ногти")]:
            category = db.get(Category, identifier(slug))
            if not category:
                category = Category(id=identifier(slug), name=name, slug=f"browser-{slug}")
                db.add(category)
                db.flush()
                db.add(
                    Service(
                        id=identifier(f"service-{slug}"),
                        category_id=category.id,
                        name="Демо-стрижка" if slug == "hair" else "Демо-маникюр",
                        description="Демонстрационная услуга для проверки каталога.",
                    )
                )
        db.flush()
        for index in range(14):
            key = str(index)
            if db.get(User, identifier(f"user-{key}")):
                continue
            user = User(
                id=identifier(f"user-{key}"),
                email=f"catalog-{index}@example.test",
                display_name=f"Демо Каталог {index + 1:02d}",
                password_hash="!browser-fixture-no-login",
                role="MASTER",
            )
            db.add(user)
            db.flush()
            master = MasterProfile(
                id=identifier(f"master-{key}"),
                user_id=user.id,
                is_demo=True,
                is_published=True,
                bio="Демонстрационный профиль для тестирования. Не реальный специалист.",
                address="Демонстрационный адрес, Кызылорда",
            )
            db.add(master)
            db.flush()
            db.add(
                MasterService(
                    id=identifier(f"offer-{key}"),
                    master_id=master.id,
                    service_id=identifier("service-nails" if index == 1 else "service-hair"),
                    price=1000 + index * 500,
                    duration_minutes=60,
                )
            )
            for weekday in range(7):
                db.add(
                    Schedule(
                        master_id=master.id,
                        weekday=weekday,
                        starts_local=time(9),
                        ends_local=time(18),
                    )
                )
            if index == 0:
                db.add(
                    PortfolioItem(
                        master_id=master.id,
                        url="/images/nails-editorial.jpg",
                        alt_text="Демонстрационная редакционная фотография маникюра",
                        license="Unsplash License, демонстрационный пример",
                        position=0,
                    )
                )
        for role in ["CLIENT", "ADMIN"]:
            if not db.get(User, identifier(role)):
                db.add(
                    User(
                        id=identifier(role),
                        email=f"browser-{role.lower()}@example.test",
                        display_name=f"Демо {role}",
                        password_hash=hash_password(password),
                        role=role,
                    )
                )
        db.get(User, identifier("user-0")).password_hash = hash_password(password)
        db.flush()
        past = datetime.now(UTC).replace(minute=0, second=0, microsecond=0) - timedelta(days=2)
        if not db.get(Booking, identifier("past-booking")):
            db.add(
                Booking(
                    id=identifier("past-booking"),
                    client_id=identifier("CLIENT"),
                    master_id=identifier("master-0"),
                    master_service_id=identifier("offer-0"),
                    starts_at=past,
                    ends_at=past + timedelta(hours=1),
                    price_snapshot=1000,
                    duration_snapshot=60,
                    service_name_snapshot="Прошедшее демо-посещение",
                    status="CONFIRMED",
                    idempotency_key=identifier("past-key"),
                    request_hash="browser-fixture",
                    timezone_snapshot="Asia/Qyzylorda",
                )
            )
    engine.dispose()
    print("Browser-only demo catalog ready with ephemeral test accounts.")


if __name__ == "__main__":
    seed_browser()
