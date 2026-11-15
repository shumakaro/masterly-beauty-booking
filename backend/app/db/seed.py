"""Idempotent demo data. No login credentials are embedded in source."""

from uuid import NAMESPACE_URL, uuid5

from sqlalchemy.orm import Session

from app.db.models import Category, MasterProfile, MasterService, Service, User
from app.db.session import get_engine


def seed_demo() -> None:
    with Session(get_engine()) as db, db.begin():
        for slug, category_name, service_name, duration, price in [
            ("hair", "Волосы", "Стрижка", 60, "12000.00"),
            ("nails", "Ногти", "Маникюр", 90, "9000.00"),
            ("makeup", "Макияж", "Дневной макияж", 60, "15000.00"),
        ]:

            def identifier(kind: str, key: str = slug):
                return uuid5(NAMESPACE_URL, f"masterly-demo:{kind}:{key}")

            category = db.get(Category, identifier("category"))
            if not category:
                category = Category(id=identifier("category"), slug=slug, name=category_name)
                db.add(category)
                db.flush()
            service = db.get(Service, identifier("service"))
            if not service:
                service = Service(
                    id=identifier("service"), category_id=category.id, name=service_name
                )
                db.add(service)
                db.flush()
            owner = db.get(User, identifier("user"))
            if not owner:
                # Disabled until the auth stage assigns a private, properly hashed password.
                owner = User(
                    id=identifier("user"),
                    email=f"demo-{slug}@example.test",
                    password_hash="!disabled-demo-account",
                    role="MASTER",
                    display_name=f"Демо-мастер: {category_name}",
                    is_active=False,
                )
                db.add(owner)
                db.flush()
            profile = db.get(MasterProfile, identifier("profile"))
            if not profile:
                profile = MasterProfile(
                    id=identifier("profile"),
                    user_id=owner.id,
                    is_demo=True,
                    is_published=False,
                    bio="Тестовый профиль, не реальный зарегистрированный мастер.",
                )
                db.add(profile)
                db.flush()
            if not db.get(MasterService, identifier("offer")):
                db.add(
                    MasterService(
                        id=identifier("offer"),
                        master_id=profile.id,
                        service_id=service.id,
                        price=price,
                        duration_minutes=duration,
                    )
                )
    print("Demo catalog seeded; accounts remain disabled and unpublished.")


if __name__ == "__main__":
    seed_demo()
