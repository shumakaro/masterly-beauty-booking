import { useEffect, useRef, useState } from "react";
import { CircleCheck } from "lucide-react";
import "./workspace.css";
import {
  Link,
  useLocation,
  useParams,
  useSearchParams,
} from "react-router-dom";
import { useAuth } from "../auth/authState";
import { homeForRole } from "../auth/paths";
import { isIdentifier, money, type Page, type Review } from "../catalog/api";
import {
  dateTime,
  usePrivateQuery,
  usePrivateOptions,
  useWrite,
  type Booking,
} from "./api";
import { DataPanel, Feedback, Pager } from "./ui";
import { pageNumber } from "./api";
import { ResourceForm, ResourceManager, type Field } from "./ResourceManager";

export interface OwnReview extends Review {
  booking_id: string;
}
const statusNames = {
  CONFIRMED: "Подтверждена",
  CANCELLED: "Отменена",
  COMPLETED: "Завершена",
};
const reviewFields: Field[] = [
  {
    name: "rating",
    label: "Оценка от 1 до 5",
    type: "number",
    min: 1,
    max: 5,
    step: 1,
    required: true,
    default: 5,
  },
  {
    name: "text",
    label: "Ваш отзыв",
    type: "textarea",
    maxLength: 3000,
    required: true,
  },
  {
    name: "photo_url",
    label: "Фотография результата по ссылке (необязательно)",
    type: "url",
    maxLength: 1000,
  },
];

export function BookingCard({
  booking,
  reviewed = false,
  reviewsReady = true,
  detail = false,
}: {
  booking: Booking;
  reviewed?: boolean;
  reviewsReady?: boolean;
  detail?: boolean;
}) {
  const { user } = useAuth();
  const [action, setAction] = useState<"CANCELLED" | "COMPLETED" | null>(null);
  const [reviewing, setReviewing] = useState(false);
  const write = useWrite<Booking>();
  const cardHeading = useRef<HTMLHeadingElement>(null);
  const actionTrigger = useRef<HTMLButtonElement | null>(null);
  const actionPanel = useRef<HTMLFormElement>(null);
  useEffect(() => {
    if (action)
      actionPanel.current
        ?.querySelector<HTMLElement>("textarea, button")
        ?.focus();
  }, [action]);
  const closeAction = () => {
    setAction(null);
    actionTrigger.current?.focus({ preventScroll: true });
  };
  const [clock, setClock] = useState(() => Date.now());
  useEffect(() => {
    const interval = window.setInterval(() => setClock(Date.now()), 30_000);
    return () => window.clearInterval(interval);
  }, []);
  if (!user) return null;
  const confirmed = booking.status === "CONFIRMED";
  const canCancel = confirmed && Date.parse(booking.starts_at) > clock;
  const canComplete =
    confirmed && user.role !== "CLIENT" && Date.parse(booking.ends_at) <= clock;
  return (
    <article className="booking-card">
      <div className="booking-card-top">
        <p className={`booking-status status-${booking.status.toLowerCase()}`}>
          {statusNames[booking.status]}
        </p>
        <span className="workspace-hint">№ {booking.id.slice(0, 8)}</span>
      </div>
      <h3 ref={cardHeading} tabIndex={-1}>
        {booking.service_name}
      </h3>
      <dl className="detail-list">
        <div>
          <dt>Мастер</dt>
          <dd>
            <Link to={`/masters/${booking.master_id}`}>
              {booking.master_name}
            </Link>
          </dd>
        </div>
        {user.role !== "CLIENT" && (
          <div>
            <dt>Клиент</dt>
            <dd>{booking.client_name}</dd>
          </div>
        )}
        <div>
          <dt>Начало</dt>
          <dd>{dateTime(booking.starts_at, booking.timezone)}</dd>
        </div>
        <div>
          <dt>Окончание</dt>
          <dd>{dateTime(booking.ends_at, booking.timezone)}</dd>
        </div>
        <div>
          <dt>Часовой пояс</dt>
          <dd>{booking.timezone}</dd>
        </div>
        <div>
          <dt>Стоимость</dt>
          <dd>
            {money(booking.price)} · {booking.duration_minutes} мин
          </dd>
        </div>
        {booking.cancellation_reason && (
          <div>
            <dt>Причина отмены</dt>
            <dd>{booking.cancellation_reason}</dd>
          </div>
        )}
      </dl>
      <div className="workspace-actions">
        {!detail && (
          <Link className="text-link" to={`/bookings/${booking.id}`}>
            Подробнее →
          </Link>
        )}
        {canCancel && (
          <button
            className="text-link"
            onClick={(event) => {
              actionTrigger.current = event.currentTarget;
              write.reset();
              setAction("CANCELLED");
            }}
          >
            Отменить запись
          </button>
        )}
        {canComplete && (
          <button
            className="text-link"
            onClick={(event) => {
              actionTrigger.current = event.currentTarget;
              write.reset();
              setAction("COMPLETED");
            }}
          >
            Завершить посещение
          </button>
        )}
        {user.role === "CLIENT" &&
          booking.status === "COMPLETED" &&
          (reviewed ? (
            <Link className="text-link" to="/dashboard?tab=reviews">
              Мой отзыв →
            </Link>
          ) : (
            <button
              className="text-link"
              disabled={!reviewsReady}
              onClick={() => setReviewing(!reviewing)}
            >
              {reviewsReady ? "Оставить отзыв" : "Проверяем отзыв…"}
            </button>
          ))}
      </div>
      {action && confirmed && (
        <form
          ref={actionPanel}
          className="confirm-action workspace-form"
          onKeyDown={(event) => {
            if (event.key === "Escape" && !write.isPending) closeAction();
          }}
          onSubmit={async (event) => {
            event.preventDefault();
            const values = new FormData(event.currentTarget);
            try {
              await write.mutateAsync({
                path: `bookings/${booking.id}`,
                method: "PATCH",
                body: {
                  status: action,
                  ...(action === "CANCELLED" && values.get("reason")
                    ? {
                        cancellation_reason: String(
                          values.get("reason"),
                        ).trim(),
                      }
                    : {}),
                },
              });
              setAction(null);
              requestAnimationFrame(() =>
                cardHeading.current?.focus({ preventScroll: true }),
              );
            } catch {
              /* Feedback below. */
            }
          }}
        >
          <p>
            {action === "CANCELLED"
              ? "Отменить запись? Это время снова станет доступным."
              : "Подтвердить, что посещение состоялось?"}
          </p>
          {action === "CANCELLED" && (
            <label>
              Причина отмены{" "}
              {user.role === "ADMIN" ? "(обязательно)" : "(необязательно)"}
              <textarea
                name="reason"
                required={user.role === "ADMIN"}
                maxLength={500}
                rows={3}
              />
            </label>
          )}
          <Feedback error={write.error} focus />
          <div className="workspace-actions">
            <button
              className="button button-outline"
              disabled={write.isPending}
            >
              {write.isPending ? "Сохраняем…" : "Подтвердить"}
            </button>
            <button
              className="text-link"
              type="button"
              disabled={write.isPending}
              onClick={closeAction}
            >
              Оставить без изменений
            </button>
          </div>
        </form>
      )}
      {write.isSuccess && (
        <p className="form-success" role="status">
          Статус посещения обновлен.
        </p>
      )}
      {reviewing && !reviewed && (
        <ResourceForm
          path="reviews"
          method="POST"
          fields={reviewFields}
          prepare={(values) => ({ ...values, booking_id: booking.id })}
          onSaved={() => setReviewing(false)}
        />
      )}
    </article>
  );
}

export function BookingsList() {
  const { user } = useAuth();
  const [params, setParams] = useSearchParams();
  const status = ["CONFIRMED", "CANCELLED", "COMPLETED"].includes(
    params.get("status") ?? "",
  )
    ? params.get("status")!
    : "";
  const endpoint =
    user?.role === "MASTER"
      ? "master/bookings"
      : user?.role === "ADMIN"
        ? "admin/bookings"
        : "bookings";
  const query = usePrivateQuery<Page<Booking>>(
    `${endpoint}?page=${pageNumber(params)}&page_size=10${status ? `&status=${status}` : ""}`,
  );
  const reviews = usePrivateOptions<OwnReview>(
    "reviews",
    user?.role === "CLIENT",
  );
  return (
    <section className="workspace-section">
      <div className="workspace-section-heading">
        <h2>Посещения</h2>
        <button className="text-link" onClick={() => void query.refetch()}>
          Обновить
        </button>
      </div>
      <label className="workspace-filter">
        Статус посещения
        <select
          value={status}
          onChange={(event) => {
            const next = new URLSearchParams(params);
            next.delete("page");
            if (event.target.value) next.set("status", event.target.value);
            else next.delete("status");
            setParams(next);
          }}
        >
          <option value="">Все статусы</option>
          {Object.entries(statusNames).map(([key, name]) => (
            <option key={key} value={key}>
              {name}
            </option>
          ))}
        </select>
      </label>
      {user?.role === "CLIENT" && reviews.isError && (
        <Feedback error={reviews.error} />
      )}
      <DataPanel query={query}>
        {(data) => (
          <>
            {data.items.length === 0 && (
              <p className="workspace-state">
                Посещений с таким статусом пока нет.{" "}
                <Link className="text-link" to="/masters">
                  Найти мастера →
                </Link>
              </p>
            )}
            <div className="bookings-grid">
              {data.items.map((booking) => (
                <BookingCard
                  key={booking.id}
                  booking={booking}
                  reviewed={reviews.data?.some(
                    (review) => review.booking_id === booking.id,
                  )}
                  reviewsReady={reviews.isSuccess}
                />
              ))}
            </div>
            <Pager data={data} />
          </>
        )}
      </DataPanel>
    </section>
  );
}
export function MyReviews() {
  return (
    <ResourceManager
      config={{
        title: "Мои отзывы",
        read: "reviews",
        write: "reviews",
        fields: reviewFields,
        remove: true,
        summary: (row) => `Оценка ${row.rating} / 5`,
        description:
          "Оставить отзыв можно в завершенном посещении. Здесь можно изменить или удалить свой отзыв.",
      }}
    />
  );
}
export function BookingDetailsPage() {
  const { id = "" } = useParams();
  const { user } = useAuth();
  const location = useLocation();
  const valid = isIdentifier(id);
  const query = usePrivateQuery<Booking>(`bookings/${id}`, valid);
  const reviews = usePrivateOptions<OwnReview>(
    "reviews",
    user?.role === "CLIENT",
  );
  return (
    <main id="main" className="shell workspace-page">
      <Link className="text-link" to={homeForRole(user!.role)}>
        ← В кабинет
      </Link>
      <p className="eyebrow">MASTERLY / Ваше посещение</p>
      {!valid ? (
        <h1>Запись не найдена.</h1>
      ) : (
        <DataPanel query={query}>
          {(booking) => (
            <>
              <h1>
                {location.state?.created && booking.status === "CONFIRMED"
                  ? "Запись подтверждена."
                  : "Детали посещения."}
              </h1>
              {location.state?.created && booking.status === "CONFIRMED" && (
                <p className="booking-success" role="status">
                  <CircleCheck aria-hidden="true" />
                  Посещение сохранено. Его детали и отмена доступны в кабинете.
                </p>
              )}
              <BookingCard
                key={booking.id}
                booking={booking}
                detail
                reviewed={reviews.data?.some(
                  (review) => review.booking_id === booking.id,
                )}
                reviewsReady={reviews.isSuccess}
              />
            </>
          )}
        </DataPanel>
      )}
    </main>
  );
}
