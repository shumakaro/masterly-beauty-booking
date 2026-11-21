"""Воспроизводимое демонстрационное наполнение только для изолированных БД."""

import os
from datetime import UTC, datetime, time, timedelta
from hashlib import sha256
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import (
    Booking,
    Category,
    MasterProfile,
    MasterService,
    PortfolioItem,
    Review,
    Schedule,
    Service,
    User,
)

# Имена и отзывы вымышлены; is_demo остается видимым признаком в API и интерфейсе.
PROFILES = [
    (
        "manicure",
        "Маникюр",
        "Амина Садыкова",
        "amina",
        "Маникюр и дизайн ногтей",
        8,
        (
            "Спокойные оттенки, аккуратная форма и тонкие акценты. Обсуждает "
            "дизайн и уход перед процедурой."
        ),
        [("Маникюр с покрытием", 9000, 90), ("Дизайн ногтей", 12000, 120)],
        "manicure",
    ),
    (
        "pedicure",
        "Педикюр",
        "Диана Ахметова",
        "diana",
        "Эстетический педикюр",
        6,
        (
            "Деликатный уход за стопами и ногтями. Работает с классическими "
            "оттенками и естественным покрытием."
        ),
        [("Педикюр с покрытием", 12000, 90), ("Уход за стопами", 8000, 60)],
        "pedicure",
    ),
    (
        "makeup",
        "Макияж",
        "Мадина Тулегенова",
        "madina",
        "Дневной и вечерний макияж",
        7,
        (
            "Мягкая растушевка и внимание к индивидуальным чертам. Помогает "
            "выбрать образ под событие."
        ),
        [("Дневной макияж", 15000, 60), ("Вечерний макияж", 22000, 90)],
        "makeup",
    ),
    (
        "hairstyle",
        "Прически",
        "Арина Волкова",
        "arina",
        "Укладки и собранные прически",
        9,
        (
            "Объемные укладки и текстурные пучки. Подбирает форму прически к "
            "длине и структуре волос."
        ),
        [("Укладка волос", 10000, 60), ("Вечерняя прическа", 18000, 90)],
        "hairstyle",
    ),
    (
        "color",
        "Окрашивание",
        "Айгерим Нурланова",
        "aigerim",
        "Сложное окрашивание и уход",
        11,
        (
            "Естественные переходы цвета и бережный подход к длине. "
            "Предварительно обсуждает желаемый оттенок."
        ),
        [("Тонирование волос", 18000, 90), ("Окрашивание в технике балаяж", 35000, 180)],
        "color",
    ),
    (
        "brows",
        "Брови",
        "Дана Бекетова",
        "dana",
        "Архитектура и укладка бровей",
        5,
        (
            "Естественные формы и мягкие оттенки. Учитывает пропорции лица и "
            "пожелания по насыщенности цвета."
        ),
        [("Оформление бровей", 5000, 30), ("Долговременная укладка бровей", 9000, 60)],
        "brows",
    ),
    (
        "lashes",
        "Ресницы",
        "София Ким",
        "sofia",
        "Ламинирование и наращивание ресниц",
        4,
        (
            "Легкие естественные эффекты и аккуратная работа с изгибом. "
            "Объясняет рекомендации по уходу."
        ),
        [("Ламинирование ресниц", 10000, 60), ("Классическое наращивание ресниц", 16000, 120)],
        "lashes",
    ),
    (
        "care",
        "Уход",
        "Алия Каримова",
        "aliya",
        "Косметический уход за кожей",
        10,
        (
            "Мягкие уходовые ритуалы и понятные рекомендации. Предлагает "
            "косметические, не медицинские процедуры."
        ),
        [("Увлажняющий уход за лицом", 14000, 60), ("Косметический уход за руками", 6000, 45)],
        "skincare",
    ),
]


def identifier(key):
    return uuid5(NAMESPACE_URL, f"masterly-showcase-v2:{key}")


def seed_showcase(engine):
    # Защита стоит до первого SQL-запроса: приложение и production нельзя наполнить случайно.
    database = engine.url.database or ""
    if engine.dialect.name != "postgresql" or not database.endswith(("_test", "_demo")):
        raise RuntimeError("Showcase requires an isolated PostgreSQL *_test or *_demo database")

    with Session(engine) as db, db.begin():

        def ensure(model, key, **values):
            item = db.get(model, identifier(key))
            if item is None:
                item = model(id=identifier(key), **values)
                db.add(item)
                db.flush()
            else:
                # Не присваиваем данные уже существующим объектам, включая измененные пользователем.
                for owner_key in ("user_id", "master_id", "client_id", "booking_id", "service_id"):
                    if owner_key in values and getattr(item, owner_key) != values[owner_key]:
                        raise RuntimeError("Showcase identifier belongs to another owner")
            return item

        past = (datetime.now(UTC) - timedelta(days=30)).replace(
            hour=5, minute=0, second=0, microsecond=0
        )
        for index, (
            key,
            category_name,
            name,
            portrait,
            specialty,
            years,
            bio,
            offers,
            work,
        ) in enumerate(PROFILES):
            category = ensure(
                Category, f"category:{key}", slug=f"showcase-{key}", name=category_name
            )
            user = ensure(
                User,
                f"user:{key}",
                email=f"showcase-{key}@example.test",
                password_hash="!disabled-showcase-account",
                role="MASTER",
                display_name=name,
            )
            master = ensure(
                MasterProfile,
                f"profile:{key}",
                user_id=user.id,
                specialization=specialty,
                experience_years=years,
                bio=bio + " Демонстрационный профиль, реальный прием не проводится.",
                timezone="Asia/Qyzylorda",
                address="Демонстрационный адрес — прием не проводится",
                avatar_url=f"/images/showcase/portrait-{portrait}.webp",
                is_demo=True,
                is_published=True,
            )
            first_offer = None
            for offer_index, (service_name, price, duration) in enumerate(offers):
                service = ensure(
                    Service,
                    f"service:{key}:{offer_index}",
                    category_id=category.id,
                    name=service_name,
                    description=(
                        f"{service_name}. {specialty}. Подбор процедуры и рекомендации по уходу. "
                        "Демонстрационная услуга."
                    ),
                )
                offer = ensure(
                    MasterService,
                    f"offer:{key}:{offer_index}",
                    master_id=master.id,
                    service_id=service.id,
                    price=price,
                    duration_minutes=duration,
                )
                first_offer = first_offer or offer
            for weekday in range(7):
                for shift, start, end in [(0, time(10), time(13)), (1, time(14), time(19))]:
                    ensure(
                        Schedule,
                        f"schedule:{key}:{weekday}:{shift}",
                        master_id=master.id,
                        weekday=weekday,
                        starts_local=start,
                        ends_local=end,
                    )
            photo = f"/images/showcase/work-{work}.webp"
            ensure(
                PortfolioItem,
                f"portfolio:{key}",
                master_id=master.id,
                category_id=category.id,
                title=f"{category_name} в естественном стиле",
                description=(
                    "Демонстрационный пример результата. Изображение не является "
                    "работой зарегистрированного специалиста."
                ),
                url=photo,
                alt_text=f"Демонстрационный пример — {category_name.lower()}",
                license="Демонстрационное изображение проекта MASTERLY",
                position=0,
            )
            for review_index, (author, rating, content) in enumerate(
                [
                    (
                        "Екатерина Денисова",
                        5,
                        (
                            "Понравилось внимание к пожеланиям и аккуратный результат. Все "
                            "этапы были понятны."
                        ),
                    ),
                    (
                        "Мария Исаева",
                        4,
                        (
                            "Комфортная атмосфера и подробные рекомендации по уходу. Результат"
                            " соответствует выбранному образу."
                        ),
                    ),
                ]
            ):
                rating = ((5, 4), (5, 5), (4, 4))[index % 3][review_index]
                client = ensure(
                    User,
                    f"client:{key}:{review_index}",
                    email=f"showcase-client-{key}-{review_index}@example.test",
                    password_hash="!disabled-showcase-client",
                    role="CLIENT",
                    display_name=author,
                    is_active=False,
                )
                start = past - timedelta(days=index * 2 + review_index)
                booking = ensure(
                    Booking,
                    f"booking:{key}:{review_index}",
                    client_id=client.id,
                    master_id=master.id,
                    master_service_id=first_offer.id,
                    starts_at=start,
                    ends_at=start + timedelta(minutes=first_offer.duration_minutes),
                    status="COMPLETED",
                    price_snapshot=first_offer.price,
                    duration_snapshot=first_offer.duration_minutes,
                    service_name_snapshot=offers[0][0],
                    timezone_snapshot=master.timezone,
                    currency="KZT",
                    idempotency_key=identifier(f"booking-key:{key}:{review_index}"),
                    request_hash=sha256(f"showcase:{key}:{review_index}".encode()).hexdigest(),
                )
                ensure(
                    Review,
                    f"review:{key}:{review_index}",
                    booking_id=booking.id,
                    rating=rating,
                    text=f"{offers[0][0]}. {content}",
                    photo_url=photo,
                    is_demo=True,
                    created_at=start + timedelta(hours=4),
                )


def main():
    url = os.environ.get("DEMO_DATABASE_URL") or os.environ.get("TEST_DATABASE_URL")
    if not url:
        raise SystemExit("Set DEMO_DATABASE_URL or TEST_DATABASE_URL for an isolated database")
    engine = create_engine(url, hide_parameters=True)
    try:
        seed_showcase(engine)
    finally:
        engine.dispose()
    print("Showcase ready: eight fictional profiles; no credentials; existing data preserved.")


if __name__ == "__main__":
    main()
