import { useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  Link,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom";
import { useAuth } from "../features/auth/authState";
import {
  type Master,
  type Offer,
  type Availability,
  isIdentifier,
  localDate,
  money,
  useCatalogQuery,
  usePublicOptions,
} from "../features/catalog/api";
import { ApiError } from "../shared/api/client";
import {
  bookingKey,
  forgetBookingKey,
  readPendingBooking,
  savePendingBooking,
  clearPendingBooking,
  dateTime,
  timeLabel,
  useWrite,
  type Booking,
} from "../features/workspace/api";
import { DataPanel, Feedback } from "../features/workspace/ui";
import "../features/workspace/workspace.css";

function BookingForm({ master, offers }: { master: Master; offers: Offer[] }) {
  const [params, setParams] = useSearchParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const cache = useQueryClient();
  const today = localDate(master.timezone);
  const end = new Date(`${today}T00:00:00Z`);
  end.setUTCDate(end.getUTCDate() + 90);
  const maximum = end.toISOString().slice(0, 10);
  const [date, setDate] = useState(() => params.get("date") || today);
  const [pending, setPending] = useState(() =>
    user ? readPendingBooking(user.id, master.id) : null,
  );
  const [start, setStart] = useState("");
  const [confirm, setConfirm] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const locked = useRef(false);
  const write = useWrite<Booking>();
  const offer = offers.find((item) => item.id === params.get("offer"));
  const valid =
    !!offer &&
    /^\d{4}-\d{2}-\d{2}$/.test(date) &&
    date >= today &&
    date <= maximum;
  const slots = useCatalogQuery<Availability>(
    `masters/${master.id}/availability?master_service_id=${offer?.id}&date=${date}`,
    valid,
  );
  const selected = slots.data?.slots.find((slot) => slot.starts_at === start);
  if (!user) return null;
  if (offers.length === 0)
    return (
      <p className="workspace-state">
        Мастер пока не добавил услуги.{" "}
        <Link to="/masters">Выбрать другого мастера</Link>
      </p>
    );
  return (
    <>
      <ol className="booking-steps" aria-label="Шаги записи">
        <li aria-current={!confirm ? "step" : undefined}>
          01 · Услуга и время
        </li>
        <li aria-current={confirm ? "step" : undefined}>02 · Подтверждение</li>
        <li>03 · Ваша запись</li>
      </ol>
      <Feedback error={write.error} />
      {write.error instanceof ApiError && write.error.status === 409 && (
        <p role="status">
          Условия записи изменились. Расписание обновлено — выберите доступное
          время заново.
        </p>
      )}
      {!confirm && pending ? (
        <section className="booking-confirm">
          <h2>Проверим прежнюю запись.</h2>
          <p className="workspace-hint">
            Подтверждение было отправлено, но результат еще не проверен.
            Восстановите попытку или проверьте посещения в кабинете.
          </p>
          <div className="workspace-actions">
            {offers.some((item) => item.id === pending.offerId) && (
              <button
                className="button button-dark"
                onClick={() => {
                  const next = new URLSearchParams();
                  next.set("offer", pending.offerId);
                  setParams(next, { replace: true });
                  setStart(pending.startsAt);
                  setDate(
                    localDate(master.timezone, new Date(pending.startsAt)),
                  );
                  setConfirm(true);
                  setUncertain(true);
                }}
              >
                Восстановить подтверждение
              </button>
            )}
            <Link className="text-link" to="/dashboard">
              Проверить мои посещения →
            </Link>
            <button
              className="text-link"
              onClick={() => {
                forgetBookingKey(user.id, pending.offerId, pending.startsAt);
                clearPendingBooking(user.id, master.id);
                setPending(null);
              }}
            >
              Посещения проверены — выбрать заново
            </button>
          </div>
        </section>
      ) : !confirm ? (
        <section className="booking-form">
          <label>
            Услуга
            <select
              value={offer?.id ?? ""}
              onChange={(event) => {
                const next = new URLSearchParams();
                next.set("offer", event.target.value);
                next.set("date", date);
                setParams(next, { replace: true });
                setStart("");
                write.reset();
              }}
            >
              <option value="">Выберите услугу</option>
              {offers.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name} · {item.duration_minutes} мин ·{" "}
                  {money(item.price)}
                </option>
              ))}
            </select>
          </label>
          {params.get("offer") && !offer && (
            <p role="alert">Эта услуга недоступна. Выберите другую.</p>
          )}
          <p className="workspace-hint">
            Дата и время мастера: {master.timezone}. Стоимость подтверждает
            сервер при записи.
          </p>
          <label>
            Дата посещения
            <input
              type="date"
              min={today}
              max={maximum}
              value={date}
              onChange={(event) => {
                setDate(event.target.value);
                const next = new URLSearchParams(params);
                next.set("date", event.target.value);
                setParams(next, { replace: true });
                setStart("");
                write.reset();
              }}
            />
          </label>
          {offer &&
            (!valid ? (
              <p role="alert">Выберите дату от сегодня до {maximum}.</p>
            ) : (
              <DataPanel query={slots}>
                {(data) =>
                  data.slots.length === 0 ? (
                    <p role="status">На эту дату свободного времени нет.</p>
                  ) : (
                    <fieldset className="slot-options">
                      <legend>Время начала</legend>
                      {data.slots.map((slot) => (
                        <label key={slot.starts_at}>
                          <input
                            type="radio"
                            name="slot"
                            value={slot.starts_at}
                            checked={start === slot.starts_at}
                            onChange={() => setStart(slot.starts_at)}
                          />
                          <span>
                            {timeLabel(slot.starts_at, data.timezone)}
                          </span>
                        </label>
                      ))}
                    </fieldset>
                  )
                }
              </DataPanel>
            ))}
          <button
            className="button button-dark"
            disabled={!selected || !valid || slots.isFetching || slots.isError}
            onClick={() => {
              setConfirm(true);
              write.reset();
            }}
          >
            Продолжить
          </button>
        </section>
      ) : (
        offer && (
          <section className="booking-confirm">
            <h2>Все верно?</h2>
            <dl className="detail-list">
              <div>
                <dt>Мастер</dt>
                <dd>{master.display_name}</dd>
              </div>
              <div>
                <dt>Услуга</dt>
                <dd>{offer.name}</dd>
              </div>
              <div>
                <dt>Посещение</dt>
                <dd>
                  {dateTime(start, master.timezone)} · {master.timezone}
                </dd>
              </div>
              <div>
                <dt>Длительность</dt>
                <dd>{offer.duration_minutes} мин</dd>
              </div>
              <div>
                <dt>Стоимость</dt>
                <dd>{money(offer.price)}</dd>
              </div>
              <div>
                <dt>Адрес</dt>
                <dd>
                  {master.address ||
                    "Адрес пока не указан — уточните у мастера"}
                </dd>
              </div>
            </dl>
            {uncertain && (
              <p className="workspace-hint" role="status">
                Ответ не получен. Запись могла сохраниться. Повторите
                подтверждение: оно проверит прежнюю операцию без создания
                дубликата. Также можно проверить посещения в кабинете.
              </p>
            )}
            <div className="workspace-actions">
              <button
                className="button button-dark"
                disabled={write.isPending}
                onClick={async () => {
                  if (locked.current) return;
                  locked.current = true;
                  try {
                    const attempt = { offerId: offer.id, startsAt: start };
                    savePendingBooking(user.id, master.id, attempt);
                    setPending(attempt);
                    const result = await write.mutateAsync({
                      path: "bookings",
                      method: "POST",
                      body: { master_service_id: offer.id, starts_at: start },
                      idempotencyKey: bookingKey(user.id, offer.id, start),
                    });
                    cache.setQueryData(
                      ["private", user.id, `bookings/${result.id}`],
                      result,
                    );
                    forgetBookingKey(user.id, offer.id, start);
                    clearPendingBooking(user.id, master.id);
                    navigate(`/bookings/${result.id}`, {
                      replace: true,
                      state: { created: true },
                    });
                  } catch (error) {
                    if (error instanceof ApiError && error.status === 409) {
                      setConfirm(false);
                      setStart("");
                      setUncertain(false);
                      clearPendingBooking(user.id, master.id);
                      setPending(null);
                      await cache.invalidateQueries({ queryKey: ["catalog"] });
                    } else {
                      if (error instanceof ApiError && error.status < 500) {
                        clearPendingBooking(user.id, master.id);
                        setPending(null);
                      }
                      setUncertain(
                        !(error instanceof ApiError) || error.status >= 500,
                      );
                    }
                  } finally {
                    locked.current = false;
                  }
                }}
              >
                {write.isPending
                  ? "Подтверждаем…"
                  : uncertain
                    ? "Проверить и повторить"
                    : "Подтвердить запись"}
              </button>
              {!uncertain && (
                <button
                  className="button button-outline"
                  disabled={write.isPending}
                  onClick={() => {
                    setConfirm(false);
                    write.reset();
                  }}
                >
                  Изменить выбор
                </button>
              )}
              <Link className="text-link" to="/dashboard">
                Мои посещения →
              </Link>
            </div>
          </section>
        )
      )}
    </>
  );
}
export function BookingPage() {
  const { masterId = "" } = useParams();
  const valid = isIdentifier(masterId);
  const master = useCatalogQuery<Master>(`masters/${masterId}`, valid);
  const offers = usePublicOptions<Offer>(`masters/${masterId}/services`, valid);
  return (
    <main id="main" className="shell workspace-page">
      <Link
        className="text-link"
        to={valid ? `/masters/${masterId}` : "/masters"}
      >
        ← К профилю мастера
      </Link>
      <p className="eyebrow">MASTERLY / Время для себя</p>
      <h1>
        Ваша следующая <em>встреча.</em>
      </h1>
      {!valid ? (
        <p role="alert">Неверная ссылка на мастера.</p>
      ) : (
        <DataPanel query={master}>
          {(data) => (
            <DataPanel query={offers}>
              {(items) => (
                <BookingForm key={data.id} master={data} offers={items} />
              )}
            </DataPanel>
          )}
        </DataPanel>
      )}
    </main>
  );
}
