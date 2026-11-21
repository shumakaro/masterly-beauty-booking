import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../auth/authState";
import { requestJson, type RequestOptions } from "../../shared/api/client";
import { isIdentifier, type Page } from "../catalog/api";

export interface Booking {
  id: string;
  client_id: string;
  master_id: string;
  master_service_id: string;
  client_name: string;
  master_name: string;
  service_name: string;
  starts_at: string;
  ends_at: string;
  timezone: string;
  price: string;
  currency: string;
  duration_minutes: number;
  status: "CONFIRMED" | "CANCELLED" | "COMPLETED";
  cancellation_reason: string | null;
}
export function pageNumber(params: URLSearchParams) {
  const page = params.get("page") ?? "1";
  return /^[1-9]\d{0,5}$/.test(page) ? Number(page) : 1;
}
// Приватный кеш разделен по user.id: смена пользователя не открывает прежние данные.
export function usePrivateQuery<T>(path: string, enabled = true) {
  const { user } = useAuth();
  return useQuery({
    queryKey: ["private", user?.id, path],
    queryFn: ({ signal }) => requestJson<T>(path, { signal }),
    enabled: !!user && enabled,
    staleTime: 0,
    retry: false,
  });
}
export function usePrivateOptions<T>(path: string, enabled = true) {
  const { user } = useAuth();
  return useQuery({
    queryKey: ["private", user?.id, "all", path],
    enabled: !!user && enabled,
    staleTime: 0,
    retry: false,
    queryFn: async ({ signal }) => {
      const items: T[] = [];
      for (let page = 1; ; page += 1) {
        const result = await requestJson<Page<T>>(
          `${path}?page=${page}&page_size=50`,
          { signal },
        );
        items.push(...result.items);
        if (items.length >= result.total || result.items.length === 0)
          return items;
      }
    },
  });
}
export function useWrite<T = unknown>() {
  const cache = useQueryClient();
  return useMutation({
    mutationFn: ({ path, ...options }: RequestOptions & { path: string }) =>
      requestJson<T>(path, options),
    onSuccess: async () => {
      await Promise.all([
        cache.invalidateQueries({ queryKey: ["private"] }),
        cache.invalidateQueries({ queryKey: ["catalog"] }),
      ]);
    },
    retry: false,
  });
}
export function dateTime(value: string, timezone: string) {
  return new Intl.DateTimeFormat("ru-RU", {
    timeZone: timezone,
    dateStyle: "long",
    timeStyle: "short",
  }).format(new Date(value));
}
export function timeLabel(value: string, timezone: string) {
  return new Intl.DateTimeFormat("ru-RU", {
    timeZone: timezone,
    hour: "2-digit",
    minute: "2-digit",
    timeZoneName: "shortOffset",
  }).format(new Date(value));
}

// A retry after a lost response must reuse the same key, including after a reload.
// Session storage holds only an operation key and public offer/time IDs, never tokens.
const fallbackKeys = new Map<string, string>();
export function bookingKey(userId: string, offerId: string, start: string) {
  const name = `masterly:booking:${userId}:${offerId}:${start}`;
  const fallback = fallbackKeys.get(name);
  if (fallback) return fallback;
  let key: string | null = null;
  try {
    key = sessionStorage.getItem(name);
  } catch {
    /* Private browsing may block storage. */
  }
  if (!key || !/^[0-9a-f-]{36}$/i.test(key)) key = crypto.randomUUID();
  fallbackKeys.set(name, key);
  try {
    sessionStorage.setItem(name, key);
  } catch {
    /* In-memory retry remains safe. */
  }
  return key;
}
export function forgetBookingKey(
  userId: string,
  offerId: string,
  start: string,
) {
  const name = `masterly:booking:${userId}:${offerId}:${start}`;
  fallbackKeys.delete(name);
  try {
    sessionStorage.removeItem(name);
  } catch {
    /* Storage is optional. */
  }
}

export interface PendingBooking {
  offerId: string;
  startsAt: string;
}
const pendingBookings = new Map<string, PendingBooking>();
const pendingName = (userId: string, masterId: string) =>
  `masterly:pending-booking:${userId}:${masterId}`;
export function readPendingBooking(
  userId: string,
  masterId: string,
): PendingBooking | null {
  const name = pendingName(userId, masterId);
  if (pendingBookings.has(name)) return pendingBookings.get(name)!;
  try {
    const raw = sessionStorage.getItem(name);
    if (!raw) return null;
    const value: unknown = JSON.parse(raw);
    if (
      value &&
      typeof value === "object" &&
      "offerId" in value &&
      "startsAt" in value &&
      typeof value.offerId === "string" &&
      isIdentifier(value.offerId) &&
      typeof value.startsAt === "string" &&
      Number.isFinite(Date.parse(value.startsAt))
    )
      return { offerId: value.offerId, startsAt: value.startsAt };
  } catch {
    /* Corrupt or unavailable storage does not block the page. */
  }
  return null;
}
export function savePendingBooking(
  userId: string,
  masterId: string,
  pending: PendingBooking,
) {
  const name = pendingName(userId, masterId);
  pendingBookings.set(name, pending);
  try {
    sessionStorage.setItem(name, JSON.stringify(pending));
  } catch {
    /* In-memory recovery remains available. */
  }
}
export function clearPendingBooking(userId: string, masterId: string) {
  const name = pendingName(userId, masterId);
  pendingBookings.delete(name);
  try {
    sessionStorage.removeItem(name);
  } catch {
    /* Storage is optional. */
  }
}
