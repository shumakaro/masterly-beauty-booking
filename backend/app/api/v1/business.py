from datetime import date
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response
from pydantic import BaseModel

from app.api.dependencies import AdminUser, ClientUser, CurrentUser, Db, MasterUser
from app.schemas.auth import AdminMasterRead, MasterProfileRead
from app.schemas.business import (
    AdminUserRead,
    AvailabilityRead,
    BookingCreate,
    BookingOverview,
    BookingRead,
    BookingUpdate,
    CategoryCreate,
    CategoryRead,
    CategoryUpdate,
    ExceptionCreate,
    ExceptionRead,
    ExceptionUpdate,
    MasterRead,
    MasterUpdate,
    OfferCreate,
    OfferRead,
    OfferUpdate,
    OwnReviewRead,
    Page,
    PortfolioCreate,
    PortfolioRead,
    PortfolioUpdate,
    ReviewCreate,
    ReviewRead,
    ReviewUpdate,
    ScheduleCreate,
    ScheduleRead,
    ScheduleUpdate,
    ServiceCreate,
    ServiceRead,
    ServiceUpdate,
    UserStatusUpdate,
    VisibilityUpdate,
)
from app.schemas.errors import ErrorResponse
from app.services.appointments import AppointmentService
from app.services.catalog import CatalogService

router = APIRouter(
    responses={status: {"model": ErrorResponse} for status in (400, 401, 403, 404, 409, 422, 503)}
)


class Pagination(BaseModel):
    page: int
    page_size: int


def pagination(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=50)):
    return Pagination(page=page, page_size=page_size)


Paging = Annotated[Pagination, Depends(pagination)]
Status = Literal["CONFIRMED", "CANCELLED", "COMPLETED"]


@router.get("/categories", response_model=Page[CategoryRead], tags=["Catalog"])
def categories(db: Db, paging: Paging):
    """Активные направления каталога. Пагинация и сортировка выполняются в PostgreSQL."""
    return CatalogService(db).categories(paging.page, paging.page_size)


@router.get("/categories/{identifier}", response_model=CategoryRead, tags=["Catalog"])
def category(identifier: UUID, db: Db):
    """
    Открыть активное направление по UUID. Неактивное или отсутствующее направление возвращает
    404.
    """
    return CatalogService(db).category(identifier)


@router.post("/categories", response_model=CategoryRead, status_code=201, tags=["Catalog"])
def create_category(data: CategoryCreate, actor: AdminUser, db: Db):
    """ADMIN создает направление. Уникальность slug проверяется в БД; конфликт возвращает 409."""
    return CatalogService(db).create_category(data)


@router.patch("/categories/{identifier}", response_model=CategoryRead, tags=["Catalog"])
def update_category(identifier: UUID, data: CategoryUpdate, actor: AdminUser, db: Db):
    """
    ADMIN изменяет только переданные поля направления. Пустое тело и недопустимые значения
    дают 422.
    """
    return CatalogService(db).update_category(identifier, data)


@router.delete("/categories/{identifier}", status_code=204, tags=["Catalog"])
def delete_category(identifier: UUID, actor: AdminUser, db: Db):
    """
    ADMIN удаляет неиспользуемое направление. Связанные услуги защищены внешними ключами;
    конфликт дает 409.
    """
    CatalogService(db).delete_category(identifier)
    return Response(status_code=204)


@router.get("/services", response_model=Page[ServiceRead], tags=["Catalog"])
def services(
    db: Db,
    paging: Paging,
    category_id: UUID | None = None,
    search: str | None = Query(None, max_length=100),
):
    """Активные услуги с поиском, фильтром направления и серверной пагинацией."""
    return CatalogService(db).services(
        paging.page, paging.page_size, category_id=category_id, search=search
    )


@router.get("/services/{identifier}", response_model=ServiceRead, tags=["Catalog"])
def service(identifier: UUID, db: Db):
    """Открыть активную услугу и ее описание по UUID; недоступная услуга возвращает 404."""
    return CatalogService(db).service(identifier)


@router.post("/services", response_model=ServiceRead, status_code=201, tags=["Catalog"])
def create_service(data: ServiceCreate, actor: AdminUser, db: Db):
    """
    ADMIN создает услугу в существующем направлении. Предложения конкретных мастеров
    настраиваются отдельно.
    """
    return CatalogService(db).create_service(data)


@router.patch("/services/{identifier}", response_model=ServiceRead, tags=["Catalog"])
def update_service(identifier: UUID, data: ServiceUpdate, actor: AdminUser, db: Db):
    """ADMIN изменяет услугу. Изменение каталога не переписывает исторические snapshot посещений."""
    return CatalogService(db).update_service(identifier, data)


@router.delete("/services/{identifier}", status_code=204, tags=["Catalog"])
def delete_service(identifier: UUID, actor: AdminUser, db: Db):
    """ADMIN удаляет неиспользуемую услугу; ссылки из предложений защищены БД и дают 409."""
    CatalogService(db).delete_service(identifier)
    return Response(status_code=204)


@router.get("/masters", response_model=Page[MasterRead], tags=["Masters"])
def masters(
    db: Db,
    paging: Paging,
    category_id: UUID | None = None,
    search: str | None = Query(None, max_length=100),
    min_price: Annotated[Decimal | None, Query(ge=0, allow_inf_nan=False)] = None,
    max_price: Annotated[Decimal | None, Query(ge=0, allow_inf_nan=False)] = None,
    sort: Literal["name", "price_asc", "price_desc", "rating"] = "name",
    available_on: date | None = None,
):
    """
    Опубликованные мастера активных аккаунтов. Поиск, цена, направление, доступная дата,
    сортировка и страницы вычисляются на сервере. Рейтинг агрегируется по отзывам.
    """
    return CatalogService(db).masters(
        paging.page,
        paging.page_size,
        sort,
        available_on=available_on,
        category_id=category_id,
        search=search,
        min_price=min_price,
        max_price=max_price,
    )


@router.get("/masters/{identifier}", response_model=MasterRead, tags=["Masters"])
def master(identifier: UUID, db: Db):
    """
    Публичный профиль опубликованного мастера: описание, специализация, стаж и агрегированный
    рейтинг. Скрытый профиль возвращает 404.
    """
    return CatalogService(db).public_master(identifier)


@router.get("/masters/{identifier}/services", response_model=Page[OfferRead], tags=["Masters"])
def master_services(identifier: UUID, db: Db, paging: Paging):
    """Активные предложения выбранного публичного мастера с ценой и длительностью."""
    return CatalogService(db).public_offers(identifier, paging.page, paging.page_size)


@router.get("/masters/{identifier}/portfolio", response_model=Page[PortfolioRead], tags=["Masters"])
def master_portfolio(identifier: UUID, db: Db, paging: Paging):
    """
    Работы выбранного публичного мастера: изображение, название, описание, категория и
    сведения об использовании.
    """
    return CatalogService(db).public_portfolio(identifier, paging.page, paging.page_size)


@router.get("/masters/{identifier}/reviews", response_model=Page[ReviewRead], tags=["Masters"])
def master_reviews(identifier: UUID, db: Db, paging: Paging):
    """
    Отзывы о выбранном публичном мастере с серверной пагинацией. Признак is_demo отличает
    демонстрационные примеры.
    """
    return CatalogService(db).public_reviews(identifier, paging.page, paging.page_size)


@router.get(
    "/masters/{identifier}/availability",
    response_model=AvailabilityRead,
    tags=["Availability"],
    summary="Available real UTC intervals, calculated in the master's IANA timezone",
)
def availability(identifier: UUID, master_service_id: UUID, date: date, db: Db):
    """
    Свободные интервалы для предложения конкретного мастера в указанную местную дату.
    Учитываются длительность, перерывы, исключения, часовой пояс и существующие записи.
    """
    return AppointmentService(db).availability(identifier, master_service_id, date)


@router.patch("/master/profile", response_model=MasterProfileRead, tags=["Master"])
def edit_master_profile(data: MasterUpdate, actor: MasterUser, db: Db):
    """
    MASTER изменяет собственный профиль. Пользователь и роль определяются по действующему JWT
    и текущему состоянию БД; is_demo не принимается.
    """
    return CatalogService(db).update_master(actor, data)


@router.get("/master/services", response_model=Page[OfferRead], tags=["Master"])
def own_services(actor: MasterUser, db: Db, paging: Paging):
    """MASTER получает собственные предложения, включая отключенные, с серверной пагинацией."""
    return CatalogService(db).own_offers(actor, paging.page, paging.page_size)


@router.post("/master/services", response_model=OfferRead, status_code=201, tags=["Master"])
def create_offer(data: OfferCreate, actor: MasterUser, db: Db):
    """
    MASTER добавляет собственное предложение: услуга, цена и длительность. Ограничения
    проверяются сервером и БД.
    """
    return CatalogService(db).create_offer(actor, data)


@router.patch("/master/services/{identifier}", response_model=OfferRead, tags=["Master"])
def update_offer(identifier: UUID, data: OfferUpdate, actor: MasterUser, db: Db):
    """
    MASTER изменяет собственное предложение под блокировкой профиля. Чужой UUID дает 404;
    конфликт с подтвержденными посещениями дает 409.
    """
    return CatalogService(db).update_offer(actor, identifier, data)


@router.delete("/master/services/{identifier}", status_code=204, tags=["Master"])
def delete_offer(identifier: UUID, actor: MasterUser, db: Db):
    """
    MASTER отключает собственное предложение, сохраняя историю посещений. Чужое предложение
    возвращает 404.
    """
    CatalogService(db).delete_offer(actor, identifier)
    return Response(status_code=204)


@router.get("/master/schedules", response_model=Page[ScheduleRead], tags=["Schedule"])
def schedules(actor: MasterUser, db: Db, paging: Paging):
    """MASTER получает собственные интервалы рабочей недели в своем часовом поясе."""
    return AppointmentService(db).schedules(actor, paging.page, paging.page_size)


@router.post("/master/schedules", response_model=ScheduleRead, status_code=201, tags=["Schedule"])
def create_schedule(data: ScheduleCreate, actor: MasterUser, db: Db):
    """
    MASTER добавляет рабочий интервал с шагом 15 минут. Пересечения и конфликты с
    подтвержденными посещениями дают 409.
    """
    return AppointmentService(db).create_schedule(actor, data)


@router.patch("/master/schedules/{identifier}", response_model=ScheduleRead, tags=["Schedule"])
def update_schedule(identifier: UUID, data: ScheduleUpdate, actor: MasterUser, db: Db):
    """
    MASTER изменяет собственный рабочий интервал. Порядок времени, шаг и сохранность
    подтвержденных посещений проверяются сервером.
    """
    return AppointmentService(db).edit_schedule(actor, identifier, data)


@router.delete("/master/schedules/{identifier}", status_code=204, tags=["Schedule"])
def delete_schedule(identifier: UUID, actor: MasterUser, db: Db):
    """
    MASTER удаляет собственный интервал, если это не нарушает подтвержденные посещения. Чужой
    UUID дает 404.
    """
    AppointmentService(db).edit_schedule(actor, identifier, delete=True)
    return Response(status_code=204)


@router.get("/master/schedule-exceptions", response_model=Page[ExceptionRead], tags=["Schedule"])
def exceptions(
    actor: MasterUser,
    db: Db,
    paging: Paging,
    from_date: date | None = None,
    to_date: date | None = None,
):
    """MASTER получает собственные исключения графика, при необходимости в диапазоне местных дат."""
    return AppointmentService(db).exceptions(
        actor, paging.page, paging.page_size, from_date, to_date
    )


@router.post(
    "/master/schedule-exceptions", response_model=ExceptionRead, status_code=201, tags=["Schedule"]
)
def create_exception(data: ExceptionCreate, actor: MasterUser, db: Db):
    """
    MASTER задает выходной или особые часы на местную дату. Исключение заменяет рабочую неделю
    для этой даты.
    """
    return AppointmentService(db).create_exception(actor, data)


@router.patch(
    "/master/schedule-exceptions/{identifier}", response_model=ExceptionRead, tags=["Schedule"]
)
def update_exception(identifier: UUID, data: ExceptionUpdate, actor: MasterUser, db: Db):
    """
    MASTER изменяет собственное исключение графика; подтвержденные посещения защищены от
    несовместимых изменений.
    """
    return AppointmentService(db).edit_exception(actor, identifier, data)


@router.delete("/master/schedule-exceptions/{identifier}", status_code=204, tags=["Schedule"])
def delete_exception(identifier: UUID, actor: MasterUser, db: Db):
    """
    MASTER удаляет собственное исключение, возвращая обычный график при отсутствии конфликта с
    посещениями.
    """
    AppointmentService(db).edit_exception(actor, identifier, delete=True)
    return Response(status_code=204)


@router.get("/master/portfolio", response_model=Page[PortfolioRead], tags=["Master"])
def own_portfolio(actor: MasterUser, db: Db, paging: Paging):
    """MASTER получает собственные работы с серверной пагинацией."""
    return CatalogService(db).own_portfolio(actor, paging.page, paging.page_size)


@router.post("/master/portfolio", response_model=PortfolioRead, status_code=201, tags=["Master"])
def create_portfolio(data: PortfolioCreate, actor: MasterUser, db: Db):
    """
    MASTER добавляет собственную работу. Категория должна быть доступна; изображение задается
    разрешенным локальным путем или HTTP(S) URL.
    """
    return CatalogService(db).create_portfolio(actor, data)


@router.patch("/master/portfolio/{identifier}", response_model=PortfolioRead, tags=["Master"])
def update_portfolio(identifier: UUID, data: PortfolioUpdate, actor: MasterUser, db: Db):
    """
    MASTER изменяет только собственную работу. Явный null очищает категорию. Чужой объект
    возвращает 404.
    """
    return CatalogService(db).update_portfolio(actor, identifier, data)


@router.delete("/master/portfolio/{identifier}", status_code=204, tags=["Master"])
def delete_portfolio(identifier: UUID, actor: MasterUser, db: Db):
    """MASTER удаляет только собственную работу; чужой или отсутствующий UUID возвращает 404."""
    CatalogService(db).delete_portfolio(actor, identifier)
    return Response(status_code=204)


@router.post(
    "/bookings",
    response_model=BookingRead,
    status_code=201,
    responses={200: {"model": BookingRead}},
    tags=["Bookings"],
)
def create_booking(
    data: BookingCreate,
    actor: ClientUser,
    db: Db,
    response: Response,
    idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
):
    """
    CLIENT подтверждает запись с обязательным UUID Idempotency-Key. В одной транзакции
    повторно проверяются слот, график и предложение; цена и длительность берутся с сервера.
    Повтор возвращает прежнюю запись, конфликт дает 409.
    """
    result, created = AppointmentService(db).create_booking(actor, data, idempotency_key)
    response.status_code = 201 if created else 200
    return result


@router.get("/bookings", response_model=Page[BookingRead], tags=["Bookings"])
def bookings(actor: ClientUser, db: Db, paging: Paging, status: Status | None = None):
    """CLIENT получает только свои посещения с серверной фильтрацией и пагинацией."""
    return AppointmentService(db).client_bookings(actor, paging.page, paging.page_size, status)


@router.get("/overview", response_model=BookingOverview, tags=["Dashboard"])
def own_overview(actor: CurrentUser, db: Db):
    """
    Сводка текущего пользователя с учетом роли и владения; данные других клиентов не
    раскрываются.
    """
    return AppointmentService(db).overview(actor)


@router.get("/bookings/{identifier}", response_model=BookingRead, tags=["Bookings"])
def booking(identifier: UUID, actor: CurrentUser, db: Db):
    """
    Посещение доступно своему клиенту, принимающему мастеру или ADMIN. Посторонний
    пользователь получает 404.
    """
    return AppointmentService(db).booking(actor, identifier)


@router.patch("/bookings/{identifier}", response_model=BookingRead, tags=["Bookings"])
def update_booking(identifier: UUID, data: BookingUpdate, actor: CurrentUser, db: Db):
    """
    Отмена участником до начала; завершение своим MASTER или ADMIN после окончания. ADMIN
    указывает причину отмены. Обратные переходы запрещены, повтор того же перехода
    идемпотентен.
    """
    return AppointmentService(db).update_booking(actor, identifier, data)


@router.get("/master/bookings", response_model=Page[BookingRead], tags=["Bookings"])
def master_bookings(actor: MasterUser, db: Db, paging: Paging, status: Status | None = None):
    """MASTER получает посещения только к своему профилю с серверной пагинацией и фильтрами."""
    return AppointmentService(db).master_bookings(actor, paging.page, paging.page_size, status)


@router.get("/favorites", response_model=Page[MasterRead], tags=["Favorites"])
def favorites(actor: ClientUser, db: Db, paging: Paging):
    """CLIENT получает только собственное избранное с серверной пагинацией."""
    return CatalogService(db).favorites(actor, paging.page, paging.page_size)


@router.put("/favorites/{identifier}", status_code=204, tags=["Favorites"])
def add_favorite(identifier: UUID, actor: ClientUser, db: Db):
    """CLIENT добавляет доступного мастера в собственное избранное. Повтор идемпотентен."""
    CatalogService(db).add_favorite(actor, identifier)
    return Response(status_code=204)


@router.delete("/favorites/{identifier}", status_code=204, tags=["Favorites"])
def remove_favorite(identifier: UUID, actor: ClientUser, db: Db):
    """CLIENT удаляет мастера только из собственного избранного. Повтор идемпотентен."""
    CatalogService(db).remove_favorite(actor, identifier)
    return Response(status_code=204)


@router.get("/reviews", response_model=Page[OwnReviewRead], tags=["Reviews"])
def own_reviews(actor: ClientUser, db: Db, paging: Paging):
    """CLIENT получает собственные отзывы и сведения о соответствующих посещениях."""
    return CatalogService(db).own_reviews(actor, paging.page, paging.page_size)


@router.post("/reviews", response_model=ReviewRead, status_code=201, tags=["Reviews"])
def create_review(data: ReviewCreate, actor: ClientUser, db: Db):
    """
    CLIENT оставляет один отзыв на собственное завершенное посещение: оценка 1–5, текст и
    необязательное фото. Повтор дает 409; is_demo назначается только демонстрационным
    наполнителем.
    """
    return CatalogService(db).create_review(actor, data)


@router.patch("/reviews/{identifier}", response_model=ReviewRead, tags=["Reviews"])
def update_review(identifier: UUID, data: ReviewUpdate, actor: ClientUser, db: Db):
    """
    CLIENT изменяет только собственный отзыв. Явный null удаляет фото; чужой UUID возвращает
    404.
    """
    return CatalogService(db).update_review(actor, identifier, data)


@router.delete("/reviews/{identifier}", status_code=204, tags=["Reviews"])
def delete_review(identifier: UUID, actor: CurrentUser, db: Db):
    """Автор CLIENT или ADMIN удаляет отзыв. Чужой CLIENT не получает доступ к объекту."""
    CatalogService(db).delete_review(actor, identifier)
    return Response(status_code=204)


@router.get("/admin/users", response_model=Page[AdminUserRead], tags=["Administration"])
def admin_users(actor: AdminUser, db: Db, paging: Paging):
    """
    ADMIN получает пользователей с серверной пагинацией; хеши паролей и refresh-токенов не
    возвращаются.
    """
    return CatalogService(db).admin_users(paging.page, paging.page_size)


@router.patch("/admin/users/{identifier}", response_model=AdminUserRead, tags=["Administration"])
def user_status(identifier: UUID, data: UserStatusUpdate, actor: AdminUser, db: Db):
    """
    ADMIN изменяет активность аккаунта с защитой административного доступа. Текущая активность
    проверяется на последующих защищенных запросах.
    """
    return CatalogService(db).user_status(actor, identifier, data)


@router.get("/admin/masters", response_model=Page[AdminMasterRead], tags=["Administration"])
def admin_masters(actor: AdminUser, db: Db, paging: Paging):
    """ADMIN получает профили, включая скрытые, с серверной пагинацией."""
    return CatalogService(db).admin_masters(paging.page, paging.page_size)


@router.patch(
    "/admin/masters/{identifier}", response_model=MasterProfileRead, tags=["Administration"]
)
def visibility(identifier: UUID, data: VisibilityUpdate, actor: AdminUser, db: Db):
    """
    ADMIN изменяет публикацию профиля. Скрытый профиль исключается из публичного каталога и
    записи.
    """
    return CatalogService(db).visibility(identifier, data)


@router.get("/admin/bookings", response_model=Page[BookingRead], tags=["Administration"])
def admin_bookings(
    actor: AdminUser,
    db: Db,
    paging: Paging,
    status: Status | None = None,
    master_id: UUID | None = None,
    client_id: UUID | None = None,
):
    """ADMIN получает посещения с серверной фильтрацией и пагинацией."""
    return AppointmentService(db).admin_bookings(
        paging.page, paging.page_size, status, master_id, client_id
    )


@router.get("/admin/categories", response_model=Page[CategoryRead], tags=["Administration"])
def admin_categories(actor: AdminUser, db: Db, paging: Paging):
    """ADMIN получает направления, включая отключенные, с серверной пагинацией."""
    return CatalogService(db).categories(paging.page, paging.page_size, admin=True)


@router.get("/admin/services", response_model=Page[ServiceRead], tags=["Administration"])
def admin_services(actor: AdminUser, db: Db, paging: Paging):
    """
    ADMIN получает услуги, включая отключенные, с серверными поиском, фильтром направления и
    пагинацией.
    """
    return CatalogService(db).services(paging.page, paging.page_size, admin=True)
