from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.engine import create_mock_engine
from sqlalchemy.exc import IntegrityError

from app.db.models import Booking, MasterProfile, PortfolioItem, Review, Service
from app.db.showcase import identifier, seed_showcase
from app.services import appointments

pytest_plugins = ["test_business"]


def test_master_details_are_searchable_and_role_protected(world):
    api = world.as_actor("master")
    response = api.request(
        "PATCH",
        "/master/profile",
        json={
            "specialization": "Балаяж и тонирование",
            "experience_years": 7,
        },
    )
    assert response.status_code == 200
    public = api.request("GET", f"/masters/{world.master.id}").json()
    assert public["specialization"] == "Балаяж и тонирование"
    assert public["experience_years"] == 7
    assert api.request("GET", "/masters", params={"search": "тонирование"}).json()["total"] == 1
    for years in (-1, 81):
        assert (
            api.request("PATCH", "/master/profile", json={"experience_years": years}).status_code
            == 422
        )
    assert api.request("PATCH", "/master/profile", json={"is_demo": True}).status_code == 422
    world.as_actor("client")
    assert api.request("PATCH", "/master/profile", json={"experience_years": 2}).status_code == 403


def test_portfolio_metadata_preserves_ownership_and_nullable_category(world):
    api = world.as_actor("master")
    response = api.request(
        "POST",
        "/master/portfolio",
        json={
            "title": "Мягкие волны",
            "description": "Укладка на длинные волосы",
            "category_id": str(world.category.id),
            "url": "/images/example.webp",
            "alt_text": "Пример укладки",
            "license": "Собственная работа",
        },
    )
    assert response.status_code == 201, response.text
    item = response.json()
    assert item["title"] == "Мягкие волны" and item["category_id"] == str(world.category.id)
    path = f"/master/portfolio/{item['id']}"
    world.as_actor("other_master")
    assert api.request("PATCH", path, json={"title": "Чужая работа"}).status_code == 404
    assert api.request("DELETE", path).status_code == 404
    world.as_actor("master")
    assert api.request("PATCH", path, json={"category_id": str(uuid4())}).status_code == 404
    assert (
        api.request(
            "PATCH", path, json={"category_id": None, "description": "Новое описание"}
        ).status_code
        == 200
    )
    public = api.request("GET", f"/masters/{world.master.id}/portfolio").json()["items"][0]
    assert public["category_id"] is None and public["description"] == "Новое описание"
    assert api.request("DELETE", path).status_code == 204


def test_review_photo_requires_completed_visit_and_cannot_forge_demo(world, monkeypatch):
    booking = world.book().json()
    api = world.as_actor("client")
    body = {
        "booking_id": booking["id"],
        "rating": 5,
        "text": "Результат понравился",
        "photo_url": "/images/review.webp",
    }
    assert api.request("POST", "/reviews", json=body).status_code == 409
    end = datetime.fromisoformat(booking["ends_at"].replace("Z", "+00:00"))
    monkeypatch.setattr(appointments, "now_utc", lambda: end + timedelta(minutes=1))
    world.as_actor("master")
    assert (
        api.request("PATCH", f"/bookings/{booking['id']}", json={"status": "COMPLETED"}).status_code
        == 200
    )
    world.as_actor("client")
    assert api.request("POST", "/reviews", json={**body, "is_demo": True}).status_code == 422
    assert (
        api.request(
            "POST", "/reviews", json={**body, "photo_url": "javascript:alert(1)"}
        ).status_code
        == 422
    )
    assert api.request("POST", "/reviews", json={**body, "text": "   "}).status_code == 422
    response = api.request("POST", "/reviews", json=body)
    assert response.status_code == 201, response.text
    review = response.json()
    assert review["photo_url"] == body["photo_url"] and review["is_demo"] is False
    assert api.request("POST", "/reviews", json=body).status_code == 409
    world.as_actor("other_client")
    path = f"/reviews/{review['id']}"
    assert api.request("PATCH", path, json={"photo_url": None}).status_code == 404
    world.as_actor("client")
    assert api.request("PATCH", path, json={"photo_url": None}).status_code == 200
    public = api.request("GET", f"/masters/{world.master.id}/reviews").json()["items"][0]
    assert public["photo_url"] is None and public["rating"] == 5
    assert "booking_id" not in public


def test_showcase_is_repeatable_transparent_and_does_not_overwrite(db, pg_engine):
    seed_showcase(pg_engine)
    profile = db.get(MasterProfile, identifier("profile:manicure"))
    profile.specialization = "Изменено владельцем"
    db.commit()
    seed_showcase(pg_engine)
    db.expire_all()
    assert profile.specialization == "Изменено владельцем"
    assert db.scalar(select(func.count()).select_from(MasterProfile)) == 8
    assert db.scalar(select(func.count()).select_from(PortfolioItem)) == 8
    assert db.scalar(select(func.count()).select_from(Review)) == 16
    assert all(db.scalars(select(Review.is_demo)))
    assert set(db.scalars(select(Booking.status))) == {"COMPLETED"}
    assert all(db.scalars(select(MasterProfile.is_demo)))
    descriptions = list(db.scalars(select(Service.description)))
    assert len(descriptions) == len(set(descriptions)) == 16


def test_showcase_refuses_application_database_before_sql():
    engine = create_mock_engine("postgresql+psycopg://localhost/masterly", lambda *a, **k: None)
    # Mock engine URL is supplied explicitly; no DB connection is made for this safety test.
    engine.url = type("URL", (), {"database": "masterly"})()
    with pytest.raises(RuntimeError, match="isolated"):
        seed_showcase(engine)


def test_experience_constraint_is_enforced_by_postgresql(db, offer):
    offer[1].experience_years = -1
    with pytest.raises(IntegrityError) as error:
        db.flush()
    assert error.value.orig.sqlstate == "23514"
