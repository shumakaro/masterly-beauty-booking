from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models import (
    Booking,
    Category,
    Favorite,
    MasterProfile,
    MasterService,
    PortfolioItem,
    Review,
    Service,
)
from app.repositories.business import BusinessRepository
from app.services.common import apply_patch, change, found


class CatalogService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = BusinessRepository(db)

    def category(self, identifier, *, admin=False):
        item = found(self.repo.get(Category, identifier))
        if not admin and not item.is_active:
            raise AppError(404, "NOT_FOUND", "Категория не найдена.")
        return item

    def service(self, identifier, *, admin=False):
        item = found(self.repo.get(Service, identifier))
        if not admin:
            self.category(item.category_id)
            if not item.is_active:
                raise AppError(404, "NOT_FOUND", "Услуга не найдена.")
        return item

    def create_category(self, data):
        item = Category(**data.model_dump())
        with change(self.db):
            self.db.add(item)
        return item

    def update_category(self, identifier, data):
        item = self.category(identifier, admin=True)
        with change(self.db):
            apply_patch(item, data.model_dump(exclude_unset=True))
        return item

    def delete_category(self, identifier):
        with change(self.db):
            self.db.delete(self.category(identifier, admin=True))

    def create_service(self, data):
        self.category(data.category_id, admin=True)
        item = Service(**data.model_dump())
        with change(self.db):
            self.db.add(item)
        return item

    def update_service(self, identifier, data):
        item = self.service(identifier, admin=True)
        values = data.model_dump(exclude_unset=True)
        if "category_id" in values:
            self.category(values["category_id"], admin=True)
        with change(self.db):
            apply_patch(item, values)
        return item

    def delete_service(self, identifier):
        with change(self.db):
            self.db.delete(self.service(identifier, admin=True))

    def public_master(self, identifier):
        return found(self.repo.public_master(identifier))

    def own_master(self, actor, *, lock=False):
        return found(self.repo.master(user_id=actor.id, lock=lock))

    def update_master(self, actor, data):
        values = data.model_dump(exclude_unset=True)
        with change(self.db):
            master = self.own_master(actor, lock=True)
            if "timezone" in values and values["timezone"] != master.timezone:
                if self.repo.future_bookings(master.id, datetime.now(UTC)):
                    raise AppError(
                        409,
                        "SCHEDULE_CONFLICT",
                        "Нельзя сменить часовой пояс при действующих записях.",
                    )
            apply_patch(master, values)
        return master

    def own_offer(self, master_id, identifier):
        item = found(self.repo.offer(identifier))
        if item.master_id != master_id:
            raise AppError(404, "NOT_FOUND", "Предложение не найдено.")
        return item

    def create_offer(self, actor, data):
        with change(self.db):
            master = self.own_master(actor, lock=True)
            self.service(data.service_id)
            item = MasterService(master_id=master.id, **data.model_dump())
            self.db.add(item)
            self.db.flush()
            identifier = item.id
        return self.repo.offer_read(identifier)

    def update_offer(self, actor, identifier, data):
        with change(self.db):
            master = self.own_master(actor, lock=True)
            item = self.own_offer(master.id, identifier)
            apply_patch(item, data.model_dump(exclude_unset=True))
        return self.repo.offer_read(identifier)

    def delete_offer(self, actor, identifier):
        with change(self.db):
            master = self.own_master(actor, lock=True)
            self.own_offer(master.id, identifier).is_active = False

    def create_portfolio(self, actor, data):
        master = self.own_master(actor)
        item = PortfolioItem(master_id=master.id, **data.model_dump())
        with change(self.db):
            self.db.add(item)
        return item

    def owned_portfolio(self, actor, identifier):
        master = self.own_master(actor)
        item = found(self.repo.get(PortfolioItem, identifier))
        if item.master_id != master.id:
            raise AppError(404, "NOT_FOUND", "Изображение не найдено.")
        return item

    def update_portfolio(self, actor, identifier, data):
        item = self.owned_portfolio(actor, identifier)
        with change(self.db):
            apply_patch(item, data.model_dump(exclude_unset=True))
        return item

    def delete_portfolio(self, actor, identifier):
        with change(self.db):
            self.db.delete(self.owned_portfolio(actor, identifier))

    def favorites(self, actor, page, size):
        stmt = (
            self.repo.master_statement()
            .join(Favorite, Favorite.master_id == MasterProfile.id)
            .where(Favorite.client_id == actor.id)
        )
        # The join uses the existing profile column; no per-master lookups are performed.
        return self.repo.paginate(
            stmt.order_by(Favorite.created_at.desc(), Favorite.master_id), page, size, mappings=True
        )

    def add_favorite(self, actor, master_id):
        self.public_master(master_id)
        with change(self.db):
            self.repo.add_favorite(actor.id, master_id)

    def remove_favorite(self, actor, master_id):
        with change(self.db):
            self.repo.remove_favorite(actor.id, master_id)

    def create_review(self, actor, data):
        booking = found(self.repo.booking(data.booking_id))
        if booking.client_id != actor.id:
            raise AppError(404, "NOT_FOUND", "Запись не найдена.")
        if booking.status != "COMPLETED":
            raise AppError(
                409, "VISIT_NOT_COMPLETED", "Отзыв можно оставить после завершенного посещения."
            )
        item = Review(**data.model_dump())
        with change(self.db):
            self.db.add(item)
            self.db.flush()
            identifier = item.id
        return self.repo.review_read(identifier)

    def owned_review(self, actor, identifier):
        item = found(self.repo.get(Review, identifier))
        booking = found(self.repo.get(Booking, item.booking_id))
        if booking.client_id != actor.id and actor.role != "ADMIN":
            raise AppError(404, "NOT_FOUND", "Отзыв не найден.")
        return item

    def update_review(self, actor, identifier, data):
        item = self.owned_review(actor, identifier)
        with change(self.db):
            apply_patch(item, data.model_dump(exclude_unset=True))
        return self.repo.review_read(identifier)

    def delete_review(self, actor, identifier):
        with change(self.db):
            self.db.delete(self.owned_review(actor, identifier))

    def user_status(self, actor, identifier, data):
        with change(self.db):
            target = found(self.repo.lock_user(identifier))
            if target.role == "ADMIN" and not data.is_active:
                raise AppError(
                    409, "ADMIN_PROTECTED", "Блокировка администраторов из этого раздела запрещена."
                )
            target.is_active = data.is_active
        return target

    def visibility(self, identifier, data):
        with change(self.db):
            master = found(self.repo.master(identifier, lock=True))
            master.is_published = data.is_published
        return master

    def categories(self, page, size, *, admin=False):
        return self.repo.categories(page, size, all_rows=admin)

    def services(self, page, size, *, category_id=None, search=None, admin=False):
        return self.repo.services(
            page, size, category_id=category_id, search=search, all_rows=admin
        )

    def masters(self, page, size, sort, **filters):
        if (
            filters.get("min_price") is not None
            and filters.get("max_price") is not None
            and filters["min_price"] > filters["max_price"]
        ):
            raise AppError(422, "INVALID_PRICE_RANGE", "Минимальная цена больше максимальной.")
        return self.repo.masters(page, size, sort, **filters)

    def public_offers(self, master_id, page, size):
        self.public_master(master_id)
        return self.repo.offers(master_id, page, size, public=True)

    def own_offers(self, actor, page, size):
        return self.repo.offers(self.own_master(actor).id, page, size)

    def public_portfolio(self, master_id, page, size):
        self.public_master(master_id)
        return self.repo.portfolio(master_id, page, size)

    def own_portfolio(self, actor, page, size):
        return self.repo.portfolio(self.own_master(actor).id, page, size)

    def public_reviews(self, master_id, page, size):
        self.public_master(master_id)
        return self.repo.reviews(master_id, page, size)

    def admin_users(self, page, size):
        return self.repo.admin_users(page, size)

    def admin_masters(self, page, size):
        return self.repo.admin_masters(page, size)
