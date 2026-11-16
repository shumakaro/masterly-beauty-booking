from datetime import UTC, datetime, time, timedelta
from uuid import UUID

from sqlalchemy import any_, bindparam, delete, func, or_, select
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Session, aliased

from app.db.models import (
    Base,
    Booking,
    Category,
    MasterProfile,
    MasterService,
    PortfolioItem,
    Review,
    Schedule,
    ScheduleException,
    Service,
    User,
)


class BusinessRepository:
    def __init__(self, db: Session):
        self.db = db

    def get[T: Base](self, model: type[T], identifier: UUID) -> T | None:
        return self.db.get(model, identifier)

    def paginate(self, statement, page: int, size: int, *, mappings=False):
        total = self.db.scalar(
            select(func.count()).select_from(statement.order_by(None).subquery())
        )
        result = self.db.execute(statement.limit(size).offset((page - 1) * size))
        items = result.mappings().all() if mappings else result.scalars().all()
        return {"items": items, "total": total or 0, "page": page, "page_size": size}

    def categories(self, page, size, *, all_rows=False):
        stmt = select(Category)
        if not all_rows:
            stmt = stmt.where(Category.is_active.is_(True))
        return self.paginate(stmt.order_by(Category.name, Category.id), page, size)

    def services(self, page, size, *, category_id=None, search=None, all_rows=False):
        stmt = select(Service).join(Category)
        if not all_rows:
            stmt = stmt.where(Service.is_active.is_(True), Category.is_active.is_(True))
        if category_id:
            stmt = stmt.where(Service.category_id == category_id)
        if search:
            stmt = stmt.where(Service.name.ilike(self.search_pattern(search), escape="\\"))
        return self.paginate(stmt.order_by(Service.name, Service.id), page, size)

    @staticmethod
    def search_pattern(value: str):
        return "%" + value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"

    def master_statement(
        self,
        *,
        category_id=None,
        search=None,
        min_price=None,
        max_price=None,
        available_offer_ids=None,
    ):
        offers = (
            select(MasterService.master_id, func.min(MasterService.price).label("price_from"))
            .join(Service, Service.id == MasterService.service_id)
            .join(Category)
            .where(
                MasterService.is_active.is_(True),
                Service.is_active.is_(True),
                Category.is_active.is_(True),
            )
        )
        if category_id:
            offers = offers.where(Service.category_id == category_id)
        if min_price is not None:
            offers = offers.where(MasterService.price >= min_price)
        if max_price is not None:
            offers = offers.where(MasterService.price <= max_price)
        if available_offer_ids is not None:
            offers = offers.where(self.uuid_in(MasterService.id, available_offer_ids))
        offers = offers.group_by(MasterService.master_id).subquery()
        ratings = (
            select(
                Booking.master_id,
                func.avg(Review.rating).label("rating"),
                func.count(Review.id).label("review_count"),
            )
            .select_from(Booking)
            .join(Review, Review.booking_id == Booking.id)
            .where(Review.is_visible.is_(True))
            .group_by(Booking.master_id)
            .subquery()
        )
        stmt = (
            select(
                MasterProfile.id,
                User.display_name,
                MasterProfile.bio,
                MasterProfile.timezone,
                MasterProfile.address,
                MasterProfile.avatar_url,
                MasterProfile.is_demo,
                offers.c.price_from,
                ratings.c.rating,
                func.coalesce(ratings.c.review_count, 0).label("review_count"),
            )
            .join(User, User.id == MasterProfile.user_id)
            .outerjoin(offers, offers.c.master_id == MasterProfile.id)
            .outerjoin(ratings, ratings.c.master_id == MasterProfile.id)
            .where(
                MasterProfile.is_published.is_(True),
                User.is_active.is_(True),
                User.role == "MASTER",
            )
        )
        if (
            category_id
            or min_price is not None
            or max_price is not None
            or available_offer_ids is not None
        ):
            stmt = stmt.where(offers.c.master_id.is_not(None))
        if search:
            pattern = self.search_pattern(search)
            stmt = stmt.where(
                or_(
                    User.display_name.ilike(pattern, escape="\\"),
                    MasterProfile.bio.ilike(pattern, escape="\\"),
                )
            )
        return stmt

    @staticmethod
    def uuid_in(column, values):
        # One typed array parameter, including empty arrays and large catalogs.
        return column == any_(bindparam(None, value=values, type_=ARRAY(PGUUID(as_uuid=True))))

    def calendar_candidates(self, *, category_id=None, search=None, min_price=None, max_price=None):
        candidates = (
            self.master_statement(
                category_id=category_id, search=search, min_price=min_price, max_price=max_price
            )
            .with_only_columns(MasterProfile.id)
            .subquery()
        )
        stmt = (
            select(
                MasterService.id,
                MasterService.master_id,
                MasterService.duration_minutes,
                MasterProfile.timezone,
            )
            .join(MasterProfile, MasterProfile.id == MasterService.master_id)
            .join(Service, Service.id == MasterService.service_id)
            .join(Category)
            .where(
                MasterService.master_id.in_(select(candidates.c.id)),
                MasterService.is_active.is_(True),
                Service.is_active.is_(True),
                Category.is_active.is_(True),
            )
        )
        if category_id:
            stmt = stmt.where(Service.category_id == category_id)
        if min_price is not None:
            stmt = stmt.where(MasterService.price >= min_price)
        if max_price is not None:
            stmt = stmt.where(MasterService.price <= max_price)
        return self.db.execute(
            stmt.order_by(MasterService.master_id, MasterService.duration_minutes, MasterService.id)
        ).all()

    def calendar_batch(self, identifiers, day):
        schedules, exceptions, busy = {}, {}, {}
        for row in self.db.scalars(
            select(Schedule)
            .where(self.uuid_in(Schedule.master_id, identifiers), Schedule.weekday == day.weekday())
            .order_by(Schedule.starts_local)
        ):
            schedules.setdefault(row.master_id, []).append((row.starts_local, row.ends_local))
        for row in self.db.scalars(
            select(ScheduleException).where(
                self.uuid_in(ScheduleException.master_id, identifiers),
                ScheduleException.local_date == day,
            )
        ):
            exceptions[row.master_id] = row
        beginning = datetime.combine(day, time(), tzinfo=UTC) - timedelta(days=2)
        ending = beginning + timedelta(days=5)
        for row in self.db.execute(
            select(Booking.master_id, Booking.starts_at, Booking.ends_at).where(
                self.uuid_in(Booking.master_id, identifiers),
                Booking.status == "CONFIRMED",
                Booking.starts_at < ending,
                Booking.ends_at > beginning,
            )
        ):
            busy.setdefault(row.master_id, []).append((row.starts_at, row.ends_at))
        return schedules, exceptions, busy

    def masters(self, page, size, sort="name", **filters):
        stmt = self.master_statement(**filters)
        columns = stmt.selected_columns
        order = {
            "name": columns.display_name.asc(),
            "price_asc": columns.price_from.asc().nulls_last(),
            "price_desc": columns.price_from.desc().nulls_last(),
            "rating": columns.rating.desc().nulls_last(),
        }[sort]
        return self.paginate(stmt.order_by(order, MasterProfile.id), page, size, mappings=True)

    def public_master(self, identifier):
        return (
            self.db.execute(self.master_statement().where(MasterProfile.id == identifier))
            .mappings()
            .first()
        )

    def master(self, identifier=None, *, user_id=None, lock=False):
        stmt = (
            select(MasterProfile).where(MasterProfile.id == identifier)
            if identifier
            else select(MasterProfile).where(MasterProfile.user_id == user_id)
        )
        if lock:
            stmt = stmt.with_for_update()
        return self.db.scalar(stmt.execution_options(populate_existing=True))

    def lock_user(self, identifier):
        return self.db.scalar(
            select(User)
            .where(User.id == identifier)
            .with_for_update(key_share=True)
            .execution_options(populate_existing=True)
        )

    def offer_statement(self):
        return (
            select(
                MasterService.id,
                MasterService.master_id,
                MasterService.service_id,
                Service.name,
                Service.description,
                Service.category_id,
                MasterService.price,
                MasterService.duration_minutes,
                MasterService.is_active,
            )
            .join(Service, Service.id == MasterService.service_id)
            .join(Category)
        )

    def offers(self, master_id, page, size, *, public=False):
        stmt = self.offer_statement().where(MasterService.master_id == master_id)
        if public:
            stmt = stmt.where(
                MasterService.is_active.is_(True),
                Service.is_active.is_(True),
                Category.is_active.is_(True),
            )
        return self.paginate(
            stmt.order_by(Service.name, MasterService.id), page, size, mappings=True
        )

    def offer_read(self, identifier):
        return (
            self.db.execute(self.offer_statement().where(MasterService.id == identifier))
            .mappings()
            .first()
        )

    def offer(self, identifier):
        return self.db.scalar(
            select(MasterService)
            .where(MasterService.id == identifier)
            .execution_options(populate_existing=True)
        )

    def windows(self, master_id, day):
        override = self.db.scalar(
            select(ScheduleException).where(
                ScheduleException.master_id == master_id, ScheduleException.local_date == day
            )
        )
        if override:
            return [] if override.is_closed else [(override.starts_local, override.ends_local)]
        return list(
            self.db.execute(
                select(Schedule.starts_local, Schedule.ends_local)
                .where(Schedule.master_id == master_id, Schedule.weekday == day.weekday())
                .order_by(Schedule.starts_local)
            ).tuples()
        )

    def schedules(self, master_id, page, size):
        return self.paginate(
            select(Schedule)
            .where(Schedule.master_id == master_id)
            .order_by(Schedule.weekday, Schedule.starts_local, Schedule.id),
            page,
            size,
        )

    def exceptions(self, master_id, page, size, from_date, to_date):
        return self.paginate(
            select(ScheduleException)
            .where(
                ScheduleException.master_id == master_id,
                ScheduleException.local_date >= from_date,
                ScheduleException.local_date <= to_date,
            )
            .order_by(ScheduleException.local_date, ScheduleException.id),
            page,
            size,
        )

    def busy(self, master_id, starts, ends):
        return list(
            self.db.execute(
                select(Booking.starts_at, Booking.ends_at).where(
                    Booking.master_id == master_id,
                    Booking.status == "CONFIRMED",
                    Booking.starts_at < ends,
                    Booking.ends_at > starts,
                )
            ).tuples()
        )

    def future_bookings(self, master_id, now):
        return self.db.scalars(
            select(Booking)
            .where(
                Booking.master_id == master_id, Booking.status == "CONFIRMED", Booking.ends_at > now
            )
            .order_by(Booking.starts_at)
        ).all()

    def idempotent_booking(self, client_id, key):
        return self.db.scalar(
            select(Booking).where(Booking.client_id == client_id, Booking.idempotency_key == key)
        )

    def booking(self, identifier):
        return self.db.scalar(
            select(Booking)
            .where(Booking.id == identifier)
            .execution_options(populate_existing=True)
        )

    def booking_statement(self):
        client, owner = aliased(User), aliased(User)
        return (
            select(
                Booking.id,
                Booking.client_id,
                Booking.master_id,
                Booking.master_service_id,
                client.display_name.label("client_name"),
                owner.display_name.label("master_name"),
                Booking.service_name_snapshot.label("service_name"),
                Booking.starts_at,
                Booking.ends_at,
                Booking.timezone_snapshot.label("timezone"),
                Booking.price_snapshot.label("price"),
                Booking.currency,
                Booking.duration_snapshot.label("duration_minutes"),
                Booking.status,
                Booking.cancellation_reason,
            )
            .join(client, client.id == Booking.client_id)
            .join(MasterProfile, MasterProfile.id == Booking.master_id)
            .join(owner, owner.id == MasterProfile.user_id)
        )

    def booking_read(self, identifier):
        return (
            self.db.execute(self.booking_statement().where(Booking.id == identifier))
            .mappings()
            .first()
        )

    def bookings(self, page, size, *, client_id=None, master_id=None, status=None):
        stmt = self.booking_statement()
        if client_id:
            stmt = stmt.where(Booking.client_id == client_id)
        if master_id:
            stmt = stmt.where(Booking.master_id == master_id)
        if status:
            stmt = stmt.where(Booking.status == status)
        return self.paginate(
            stmt.order_by(Booking.starts_at.desc(), Booking.id), page, size, mappings=True
        )

    def booking_overview(self, now, *, client_id=None, master_id=None):
        stmt = select(
            func.count(Booking.id).label("total"),
            func.count(Booking.id).filter(Booking.status == "CONFIRMED").label("confirmed"),
            func.count(Booking.id)
            .filter(Booking.status == "CONFIRMED", Booking.starts_at > now)
            .label("upcoming"),
            func.count(Booking.id).filter(Booking.status == "COMPLETED").label("completed"),
            func.count(Booking.id).filter(Booking.status == "CANCELLED").label("cancelled"),
            func.coalesce(
                func.sum(Booking.price_snapshot).filter(Booking.status == "COMPLETED"), 0
            ).label("completed_value"),
        )
        stmt = (
            stmt.where(Booking.client_id == client_id)
            if client_id
            else stmt.where(Booking.master_id == master_id)
        )
        return self.db.execute(stmt).mappings().one()

    def portfolio(self, master_id, page, size):
        return self.paginate(
            select(PortfolioItem)
            .where(PortfolioItem.master_id == master_id)
            .order_by(PortfolioItem.position, PortfolioItem.id),
            page,
            size,
        )

    def reviews(self, master_id, page, size):
        stmt = (
            select(
                Review.id,
                Review.rating,
                Review.text,
                Review.created_at,
                User.display_name.label("author_name"),
            )
            .select_from(Review)
            .join(Booking, Booking.id == Review.booking_id)
            .join(User, User.id == Booking.client_id)
            .where(Booking.master_id == master_id, Review.is_visible.is_(True))
        )
        return self.paginate(
            stmt.order_by(Review.created_at.desc(), Review.id), page, size, mappings=True
        )

    def review_read(self, identifier):
        return (
            self.db.execute(
                select(
                    Review.id,
                    Review.rating,
                    Review.text,
                    Review.created_at,
                    User.display_name.label("author_name"),
                )
                .select_from(Review)
                .join(Booking, Booking.id == Review.booking_id)
                .join(User, User.id == Booking.client_id)
                .where(Review.id == identifier)
            )
            .mappings()
            .first()
        )

    def own_reviews(self, client_id, page, size):
        stmt = (
            select(
                Review.id,
                Review.booking_id,
                Review.rating,
                Review.text,
                Review.created_at,
                User.display_name.label("author_name"),
            )
            .select_from(Review)
            .join(Booking, Booking.id == Review.booking_id)
            .join(User, User.id == Booking.client_id)
            .where(Booking.client_id == client_id)
        )
        return self.paginate(
            stmt.order_by(Review.created_at.desc(), Review.id), page, size, mappings=True
        )

    def admin_users(self, page, size):
        return self.paginate(select(User).order_by(User.created_at.desc(), User.id), page, size)

    def admin_masters(self, page, size):
        return self.paginate(
            select(MasterProfile).order_by(MasterProfile.created_at.desc(), MasterProfile.id),
            page,
            size,
        )

    def remove_favorite(self, client_id, master_id):
        from app.db.models import Favorite

        self.db.execute(
            delete(Favorite).where(Favorite.client_id == client_id, Favorite.master_id == master_id)
        )

    def add_favorite(self, client_id, master_id):
        from sqlalchemy.dialects.postgresql import insert

        from app.db.models import Favorite

        self.db.execute(
            insert(Favorite)
            .values(client_id=client_id, master_id=master_id)
            .on_conflict_do_nothing()
        )
