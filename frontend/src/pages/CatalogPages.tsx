import { useRef, useState, type ReactNode } from "react";
import "./catalog.css";
import type { UseQueryResult } from "@tanstack/react-query";
import { FavoriteButton } from "../features/workspace/Favorites";
import { LoadingState } from "../shared/ui/LoadingState";
import { containDialogFocus } from "../shared/ui/dialogFocus";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { ArrowRight, MapPin, Star, X } from "lucide-react";
import { ApiError, describeError } from "../shared/api/client";
import {
  type Page,
  type Master,
  type Service,
  type Offer,
  type Portfolio,
  type Review,
  type Availability,
  isIdentifier,
  localDate,
  money,
  experienceLabel,
  readFilters,
  useCatalogQuery,
  useCategories,
} from "../features/catalog/api";

function QueryContent<T>({
  query,
  children,
  empty,
}: {
  query: UseQueryResult<T, Error>;
  children: (data: T) => ReactNode;
  empty?: string;
}) {
  if (query.isPending)
    return <LoadingState label="Загружаем данные…" className="catalog-state" />;
  if (query.isError)
    return (
      <div className="catalog-state" role="alert">
        <p>
          {query.error instanceof ApiError && query.error.status === 404
            ? "Мастер не найден или профиль скрыт."
            : describeError(query.error)}
        </p>
        <button
          className="button button-outline"
          onClick={() => void query.refetch()}
        >
          Повторить загрузку
        </button>
      </div>
    );
  if (
    empty &&
    typeof query.data === "object" &&
    query.data !== null &&
    "items" in query.data &&
    Array.isArray(query.data.items) &&
    query.data.items.length === 0
  )
    return (
      <p className="catalog-state" role="status">
        {empty}
      </p>
    );
  return children(query.data);
}

function Pagination({
  data,
  name = "page",
}: {
  data: Page<unknown>;
  name?: string;
}) {
  const [params] = useSearchParams();
  const total = Math.max(1, Math.ceil(data.total / data.page_size));
  const target = (page: number) => {
    const next = new URLSearchParams(params);
    next.set(name, String(page));
    return `?${next}`;
  };
  if (total === 1 && data.page === 1) return null;
  return (
    <nav
      className="catalog-pagination"
      aria-label={`Страницы: ${name === "page" ? "каталог" : name === "offers_page" ? "услуги мастера" : name === "reviews_page" ? "отзывы" : "портфолио"}`}
    >
      {data.page > 1 && (
        <Link className="text-link" to={target(data.page - 1)}>
          ← Назад
        </Link>
      )}
      <span>
        Страница {data.page} из {total}
      </span>
      {data.page < total && (
        <Link className="text-link" to={target(data.page + 1)}>
          Далее →
        </Link>
      )}
      {data.page > total && (
        <Link className="text-link" to={target(1)}>
          К первой странице
        </Link>
      )}
    </nav>
  );
}

function Filters({ masters }: { masters: boolean }) {
  const [params, setParams] = useSearchParams();
  const filters = readFilters(params, masters);
  const categories = useCategories();
  return (
    <form
      className={`catalog-filters ${masters ? "with-prices" : ""}`}
      key={params.toString()}
      onSubmit={(event) => {
        event.preventDefault();
        const data = new FormData(event.currentTarget);
        const next = new URLSearchParams();
        if (!categories.data && filters.category)
          next.set("category_id", filters.category);
        for (const [key, value] of data)
          if (typeof value === "string" && value.trim())
            next.set(key, value.trim());
        setParams(next);
      }}
    >
      <label>
        Поиск
        <input
          name="search"
          defaultValue={filters.search}
          maxLength={100}
          placeholder={
            masters
              ? "Имя или описание мастера"
              : "Название или описание услуги"
          }
          type="search"
        />
      </label>
      <label>
        Направление
        <select
          key={categories.data ? "loaded" : "loading"}
          name="category_id"
          defaultValue={filters.category}
          disabled={!categories.data}
        >
          <option value="">Все направления</option>
          {filters.category &&
            !categories.data?.some((item) => item.id === filters.category) && (
              <option value={filters.category}>Выбранное направление</option>
            )}
          {categories.data?.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
      </label>
      {masters && (
        <>
          <label>
            Цена от, ₸
            <input
              name="min_price"
              type="number"
              min="0"
              max="9999999999"
              step="0.01"
              defaultValue={filters.min}
              placeholder="0"
            />
          </label>
          <label>
            Цена до, ₸
            <input
              name="max_price"
              type="number"
              min="0"
              max="9999999999"
              step="0.01"
              defaultValue={filters.max}
              placeholder="Без ограничения"
            />
          </label>
          <label>
            Сортировка
            <select name="sort" defaultValue={filters.sort}>
              <option value="name">По имени</option>
              <option value="price_asc">Сначала дешевле</option>
              <option value="price_desc">Сначала дороже</option>
              <option value="rating">По рейтингу</option>
            </select>
          </label>
          <label>
            Свободная дата
            <input
              type="date"
              name="available_on"
              defaultValue={filters.availableOn}
            />
          </label>
        </>
      )}
      <div className="filter-actions">
        <button className="button button-dark" type="submit">
          Найти
        </button>
        <Link className="text-link" to={masters ? "/masters" : "/services"}>
          Сбросить
        </Link>
      </div>
      {masters && (
        <p className="filter-note">
          Дата в часовом поясе мастера, до 90 дней вперед. Показываем мастеров с
          подходящими свободными услугами.
        </p>
      )}
      {categories.isError && (
        <p className="filter-note" role="alert">
          Направления не загрузились.{" "}
          <button type="button" onClick={() => void categories.refetch()}>
            Повторить
          </button>
        </p>
      )}
    </form>
  );
}

function MasterImage({ master }: { master: Master }) {
  const [failed, setFailed] = useState(false);
  return master.avatar_url && !failed ? (
    <img
      className="master-image"
      src={master.avatar_url}
      alt={master.display_name}
      loading="lazy"
      onError={() => setFailed(true)}
    />
  ) : (
    <div
      className="master-image master-monogram"
      role="img"
      aria-label="Фотография пока не добавлена"
    >
      {master.display_name.slice(0, 1)}
    </div>
  );
}
function Rating({ master }: { master: Master }) {
  return (
    <span className="master-rating">
      <Star size={14} aria-hidden="true" />{" "}
      {master.rating === null
        ? "Пока без отзывов"
        : `${master.rating.toFixed(1)} / 5 · Отзывов: ${master.review_count}`}
    </span>
  );
}

export function MastersPage() {
  const [params] = useSearchParams();
  const filters = readFilters(params, true);
  const query = useCatalogQuery<Page<Master>>(
    `masters?${filters.query}`,
    filters.valid,
  );
  return (
    <main id="main" className="shell catalog-page">
      <p className="eyebrow">MASTERLY / Ваш круг заботы</p>
      <div className="catalog-heading">
        <h1>
          Найдите <em>своего мастера.</em>
        </h1>
        <p>
          Подход, работы и стоимость.
          <br />
          Все, чтобы выбрать спокойно.
        </p>
      </div>
      <Filters masters />
      {!filters.valid ? (
        <p className="catalog-state" role="alert">
          Проверьте фильтры: корректные направление и дата, страница от 1 и цена
          «от» не выше цены «до».
        </p>
      ) : (
        <QueryContent query={query}>
          {(data) => (
            <>
              <p className="catalog-count" role="status">
                Найдено мастеров: {data.total}
              </p>
              {data.items.length === 0 && (
                <p className="catalog-state">
                  По этим условиям мастеров нет. Измените фильтры или вернитесь
                  позже.
                </p>
              )}
              <div className="masters-grid">
                {data.items.map((master) => (
                  <article className="master-card" key={master.id}>
                    <Link
                      to={`/masters/${master.id}${filters.availableOn ? `?date=${filters.availableOn}` : ""}`}
                      className="master-photo-link"
                      aria-label={`Профиль: ${master.display_name}`}
                    >
                      <MasterImage key={master.avatar_url} master={master} />
                    </Link>
                    <div className="master-card-body">
                      {master.is_demo && (
                        <span className="badge">Демо-профиль</span>
                      )}
                      <h2>
                        <Link
                          to={`/masters/${master.id}${filters.availableOn ? `?date=${filters.availableOn}` : ""}`}
                        >
                          {master.display_name}
                        </Link>
                      </h2>
                      <Rating master={master} />
                      {master.specialization && (
                        <p className="master-specialization">
                          {master.specialization}
                        </p>
                      )}
                      {master.experience_years > 0 && (
                        <p className="master-experience">
                          Опыт работы:{" "}
                          {experienceLabel(master.experience_years)}
                        </p>
                      )}
                      <p className="master-bio-preview">
                        {master.bio || "Мастер пока не добавил описание."}
                      </p>
                      {master.address && (
                        <p className="master-address">
                          <MapPin size={14} aria-hidden="true" />
                          {master.address}
                        </p>
                      )}
                      <div className="master-card-bottom">
                        <span>
                          {master.price_from === null
                            ? "Услуги пока не добавлены"
                            : `от ${money(master.price_from)}`}
                        </span>
                        <Link
                          to={`/masters/${master.id}${filters.availableOn ? `?date=${filters.availableOn}` : ""}`}
                          aria-label={`Подробнее: ${master.display_name}`}
                        >
                          <ArrowRight size={20} />
                        </Link>
                      </div>
                    </div>
                  </article>
                ))}
              </div>
              <Pagination data={data} />
            </>
          )}
        </QueryContent>
      )}
    </main>
  );
}

export function ServicesPage() {
  const [params] = useSearchParams();
  const filters = readFilters(params, false);
  const query = useCatalogQuery<Page<Service>>(
    `services?${filters.query}`,
    filters.valid,
  );
  const categories = useCategories();
  return (
    <main id="main" className="shell catalog-page">
      <p className="eyebrow">MASTERLY / Ритуалы красоты</p>
      <div className="catalog-heading">
        <h1>
          Маленькое время.
          <br />
          <em>Большое внимание.</em>
        </h1>
        <p>
          Знакомьтесь с услугами.
          <br />
          Цены и длительность — в профилях мастеров.
        </p>
      </div>
      <Filters masters={false} />
      {!filters.valid ? (
        <p className="catalog-state" role="alert">
          Проверьте параметры поиска или сбросьте фильтры.
        </p>
      ) : (
        <QueryContent query={query}>
          {(data) => (
            <>
              <p className="catalog-count" role="status">
                Найдено услуг: {data.total}
              </p>
              {data.items.length === 0 && (
                <p className="catalog-state">
                  Подходящих услуг пока нет. Попробуйте другое направление.
                </p>
              )}
              <div className="services-grid">
                {data.items.map((service, index) => (
                  <article className="service-card" key={service.id}>
                    <p className="eyebrow">
                      {String(
                        (data.page - 1) * data.page_size + index + 1,
                      ).padStart(2, "0")}{" "}
                      /{" "}
                      {categories.data?.find(
                        (category) => category.id === service.category_id,
                      )?.name ?? "Услуга"}
                    </p>
                    <h2>{service.name}</h2>
                    <p>
                      {service.description || "Описание пока не добавлено."}
                    </p>
                    <Link
                      className="text-link"
                      to={`/masters?category_id=${service.category_id}`}
                    >
                      Мастера этого направления <ArrowRight size={16} />
                    </Link>
                  </article>
                ))}
              </div>
              <Pagination data={data} />
            </>
          )}
        </QueryContent>
      )}
    </main>
  );
}

function resourcePage(params: URLSearchParams, key: string) {
  const value = params.get(key) ?? "1";
  return /^[1-9]\d{0,5}$/.test(value) ? Number(value) : 1;
}

function PortfolioImage({
  item,
  categoryName,
}: {
  item: Portfolio;
  categoryName?: string;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [failed, setFailed] = useState(false);
  return (
    <figure>
      {failed ? (
        <p className="catalog-state">Изображение недоступно</p>
      ) : (
        <button
          className="portfolio-image"
          onClick={() => dialog.current?.showModal()}
          aria-label={`Увеличить: ${item.alt_text}`}
        >
          <img
            src={item.url}
            alt={item.alt_text}
            loading="lazy"
            onError={() => setFailed(true)}
          />
        </button>
      )}
      <figcaption>
        <strong>{item.title || item.alt_text}</strong>
        {categoryName && <span className="badge">{categoryName}</span>}
        {item.description && <p>{item.description}</p>}
        <small>
          {item.license}
          {item.source_url && (
            <>
              {" "}
              ·{" "}
              <a href={item.source_url} target="_blank" rel="noreferrer">
                Источник
              </a>
            </>
          )}
        </small>
      </figcaption>
      <dialog
        className="portfolio-dialog"
        onKeyDown={containDialogFocus}
        ref={dialog}
        aria-label={item.alt_text}
      >
        <button
          className="icon-button"
          autoFocus
          onClick={() => dialog.current?.close()}
          aria-label="Закрыть фотографию"
        >
          <X />
        </button>
        <img
          src={item.url}
          alt={item.alt_text}
          onError={() => setFailed(true)}
        />
        <p>{item.title || item.alt_text}</p>
        {item.description && <p>{item.description}</p>}
      </dialog>
    </figure>
  );
}

function AvailabilityPanel({
  master,
  offer,
  initialDate,
}: {
  master: Master;
  offer: Offer;
  initialDate: string;
}) {
  const today = localDate(master.timezone);
  const end = new Date(`${today}T00:00:00Z`);
  end.setUTCDate(end.getUTCDate() + 90);
  const maximum = end.toISOString().slice(0, 10);
  const [date, setDate] = useState(initialDate || today);
  const valid =
    /^\d{4}-\d{2}-\d{2}$/.test(date) && date >= today && date <= maximum;
  const query = useCatalogQuery<Availability>(
    `masters/${master.id}/availability?master_service_id=${offer.id}&date=${date}`,
    valid,
  );
  const format = (value: string) =>
    new Intl.DateTimeFormat("ru-RU", {
      timeZone: master.timezone,
      hour: "2-digit",
      minute: "2-digit",
      timeZoneName: "shortOffset",
    }).format(new Date(value));
  return (
    <section
      className="availability-panel"
      aria-labelledby="availability-title"
    >
      <p className="eyebrow">Свободное время</p>
      <h3 id="availability-title">
        {offer.name} · {offer.duration_minutes} мин · {money(offer.price)}
      </h3>
      <p>
        Время мастера: {master.timezone}. Выберите удобную дату, затем перейдите
        к оформлению записи.
      </p>
      <label>
        Дата посещения
        <input
          type="date"
          value={date}
          min={today}
          max={maximum}
          onChange={(event) => setDate(event.target.value)}
        />
      </label>
      <Link
        className="button button-dark"
        to={`/book/${master.id}?offer=${offer.id}&date=${date}`}
      >
        Перейти к записи
      </Link>
      {!valid ? (
        <p role="alert">Выберите дату от сегодня до {maximum}.</p>
      ) : (
        <QueryContent query={query}>
          {(data) =>
            data.slots.length === 0 ? (
              <p role="status">На эту дату свободного времени нет.</p>
            ) : (
              <ul
                className="availability-slots"
                aria-label="Свободные интервалы"
              >
                {data.slots.map((slot) => (
                  <li key={slot.starts_at}>
                    <time dateTime={slot.starts_at}>
                      {format(slot.starts_at)}
                    </time>{" "}
                    —{" "}
                    <time dateTime={slot.ends_at}>{format(slot.ends_at)}</time>
                  </li>
                ))}
              </ul>
            )
          }
        </QueryContent>
      )}
    </section>
  );
}

function ReviewPhoto({ url }: { url: string }) {
  const [failed, setFailed] = useState(false);
  if (failed)
    return (
      <p className="image-fallback" role="status">
        Фотография к отзыву недоступна
      </p>
    );
  return (
    <a
      href={url}
      target="_blank"
      rel="noreferrer"
      aria-label="Открыть фотографию к отзыву"
    >
      <img
        className="review-photo"
        src={url}
        alt="Фотография результата к отзыву"
        loading="lazy"
        onError={() => setFailed(true)}
      />
    </a>
  );
}

function MasterDetails({ master }: { master: Master }) {
  const [params, setParams] = useSearchParams();
  const offers = useCatalogQuery<Page<Offer>>(
    `masters/${master.id}/services?page=${resourcePage(params, "offers_page")}&page_size=12`,
  );
  const portfolio = useCatalogQuery<Page<Portfolio>>(
    `masters/${master.id}/portfolio?page=${resourcePage(params, "portfolio_page")}&page_size=12`,
  );
  const reviews = useCatalogQuery<Page<Review>>(
    `masters/${master.id}/reviews?page=${resourcePage(params, "reviews_page")}&page_size=6`,
  );
  const selected = offers.data?.items.find(
    (offer) => offer.id === params.get("offer"),
  );
  const categories = useCategories();
  return (
    <>
      <Link className="text-link" to="/masters">
        ← Все мастера
      </Link>
      <section className="master-profile-heading">
        <MasterImage key={master.avatar_url} master={master} />
        <div>
          <p className="eyebrow">
            {master.is_demo
              ? "Демонстрационный профиль"
              : "Ваш мастер / MASTERLY"}
          </p>
          <h1>{master.display_name}</h1>
          {master.specialization && (
            <p className="master-specialization">{master.specialization}</p>
          )}
          {master.experience_years > 0 && (
            <p className="master-experience">
              Опыт работы: {experienceLabel(master.experience_years)}
            </p>
          )}
          <Rating master={master} />
          {master.is_demo && (
            <p className="demo-notice">
              Демонстрационный профиль. Имя, опыт, работы и примеры отзывов
              используются для знакомства с платформой. Реальный прием не
              проводится.
            </p>
          )}
          <p className="profile-bio">
            {master.bio || "Мастер пока не добавил описание."}
          </p>
          <p className="master-address">
            <MapPin size={16} aria-hidden="true" />
            {master.address || "Адрес пока не указан"}
          </p>
          <p className="profile-timezone">Часовой пояс: {master.timezone}</p>
          <FavoriteButton masterId={master.id} />
        </div>
      </section>
      <section className="profile-section" aria-labelledby="offers-title">
        <p className="eyebrow">01 / Ваш ритуал</p>
        <h2 id="offers-title">
          Услуги <em>и стоимость.</em>
        </h2>
        <QueryContent query={offers} empty="Мастер пока не добавил услуги.">
          {(data) => (
            <>
              <div className="offer-list">
                {data.items.map((offer) => (
                  <article key={offer.id} className="offer-row">
                    <div>
                      <h3>{offer.name}</h3>
                      <p>{offer.description}</p>
                      <span>{offer.duration_minutes} мин</span>
                    </div>
                    <div>
                      <strong>{money(offer.price)}</strong>
                      <Link
                        className="button button-dark"
                        to={`/book/${master.id}?offer=${offer.id}${params.get("date") ? `&date=${encodeURIComponent(params.get("date")!)}` : ""}`}
                      >
                        Записаться
                      </Link>
                      <button
                        className="text-link"
                        aria-pressed={selected?.id === offer.id}
                        onClick={() => {
                          const next = new URLSearchParams(params);
                          next.set("offer", offer.id);
                          setParams(next, { replace: true });
                        }}
                      >
                        Свободное время <ArrowRight size={16} />
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            </>
          )}
        </QueryContent>
        {offers.data && <Pagination data={offers.data} name="offers_page" />}
        {selected && (
          <AvailabilityPanel
            key={selected.id}
            master={master}
            offer={selected}
            initialDate={params.get("date") ?? ""}
          />
        )}
      </section>
      <section className="profile-section" aria-labelledby="portfolio-title">
        <p className="eyebrow">02 / Внимание к деталям</p>
        <h2 id="portfolio-title">
          Работы <em>мастера.</em>
        </h2>
        <QueryContent
          query={portfolio}
          empty="Фотографии работ пока не добавлены."
        >
          {(data) => (
            <div className="portfolio-grid">
              {data.items.map((item) => (
                <PortfolioImage
                  key={item.id}
                  item={item}
                  categoryName={
                    categories.data?.find(
                      (category) => category.id === item.category_id,
                    )?.name
                  }
                />
              ))}
            </div>
          )}
        </QueryContent>
        {portfolio.data && (
          <Pagination data={portfolio.data} name="portfolio_page" />
        )}
      </section>
      <section className="profile-section" aria-labelledby="reviews-title">
        <p className="eyebrow">03 / Личный опыт</p>
        <h2 id="reviews-title">
          Слова <em>после встречи.</em>
        </h2>
        <QueryContent
          query={reviews}
          empty="Отзывов пока нет. Их могут оставить клиенты после завершенного посещения."
        >
          {(data) => (
            <div className="reviews-list">
              {data.items.map((review) => (
                <article key={review.id}>
                  <div>
                    <strong>{review.author_name}</strong>
                    <span>{review.rating} / 5</span>
                  </div>
                  <p>{review.text}</p>
                  {review.is_demo && (
                    <span className="badge">
                      Пример отзыва · демонстрационные данные
                    </span>
                  )}
                  {review.photo_url && (
                    <ReviewPhoto
                      key={review.photo_url}
                      url={review.photo_url}
                    />
                  )}
                  <time dateTime={review.created_at}>
                    {new Intl.DateTimeFormat("ru-RU", {
                      dateStyle: "long",
                      timeZone: master.timezone,
                    }).format(new Date(review.created_at))}
                  </time>
                </article>
              ))}
            </div>
          )}
        </QueryContent>
        {reviews.data && <Pagination data={reviews.data} name="reviews_page" />}
      </section>
    </>
  );
}

export function MasterPage() {
  const { id = "" } = useParams();
  const valid = isIdentifier(id);
  const query = useCatalogQuery<Master>(`masters/${id}`, valid);
  return (
    <main id="main" className="shell catalog-page">
      {!valid ? (
        <div className="catalog-state">
          <h1>Мастер не найден.</h1>
          <Link className="text-link" to="/masters">
            Вернуться в каталог
          </Link>
        </div>
      ) : query.isError &&
        query.error instanceof ApiError &&
        query.error.status === 404 ? (
        <div className="catalog-state">
          <h1>Мастер не найден.</h1>
          <p>Профиль скрыт или больше недоступен.</p>
          <Link className="text-link" to="/masters">
            Вернуться в каталог
          </Link>
        </div>
      ) : (
        <QueryContent query={query}>
          {(master) => <MasterDetails key={master.id} master={master} />}
        </QueryContent>
      )}
    </main>
  );
}
