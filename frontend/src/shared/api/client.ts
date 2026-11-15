export type Role = "CLIENT" | "MASTER" | "ADMIN";
export interface User {
  id: string;
  email: string;
  display_name: string;
  role: Role;
}
export interface SessionResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  user: User;
}
export interface FieldError {
  path: string;
  message: string;
}

export class ApiError extends Error {
  readonly status: number;
  readonly fields: FieldError[];
  readonly code: string;
  constructor(
    status: number,
    message = `API request failed (${status})`,
    fields: FieldError[] = [],
    code = "HTTP_ERROR",
  ) {
    super(message);
    this.status = status;
    this.fields = fields;
    this.code = code;
  }
}

const baseUrl = import.meta.env.VITE_API_BASE_URL as string | undefined;
let token: string | null = null;
let refreshPromise: Promise<SessionResponse> | null = null;
const listeners = new Set<(user: User | null) => void>();

export function subscribeSession(listener: (user: User | null) => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}
function acceptSession(data: SessionResponse) {
  token = data.access_token;
  listeners.forEach((listener) => listener(data.user));
  return data;
}
function clearSession() {
  token = null;
  listeners.forEach((listener) => listener(null));
}

async function responseError(response: Response) {
  let message = "Не удалось выполнить запрос. Попробуйте позже.";
  let fields: FieldError[] = [];
  let code = "HTTP_ERROR";
  try {
    const value: unknown = await response.json();
    if (typeof value === "object" && value !== null && "error" in value) {
      const error = value.error;
      if (typeof error === "object" && error !== null) {
        if ("message" in error && typeof error.message === "string")
          message = error.message;
        if ("code" in error && typeof error.code === "string")
          code = error.code;
        if ("fields" in error && Array.isArray(error.fields))
          fields = error.fields.filter(
            (field): field is FieldError =>
              typeof field === "object" &&
              field !== null &&
              "path" in field &&
              typeof field.path === "string" &&
              "message" in field &&
              typeof field.message === "string",
          );
      }
    }
  } catch {
    /* Non-JSON proxy errors still retain their HTTP status. */
  }
  return new ApiError(response.status, message, fields, code);
}

export interface RequestOptions {
  method?: string;
  body?: unknown;
  signal?: AbortSignal;
}
async function send(path: string, options: RequestOptions = {}) {
  if (!baseUrl) throw new Error("Адрес API не настроен. Попробуйте позже.");
  const headers: Record<string, string> = { Accept: "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  if (options.method && options.method !== "GET")
    headers["X-CSRF-Protection"] = "1";
  return fetch(`${baseUrl.replace(/\/$/, "")}/${path.replace(/^\//, "")}`, {
    method: options.method ?? "GET",
    credentials: "include",
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    signal: options.signal,
  });
}

export async function refreshSession(): Promise<SessionResponse> {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      const response = await send("auth/refresh", { method: "POST" });
      if (!response.ok) {
        if (response.status === 401) clearSession();
        throw await responseError(response);
      }
      return acceptSession((await response.json()) as SessionResponse);
    })().finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

export async function requestJson<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  let response = await send(path, options);
  if (response.status === 401 && token && !path.startsWith("auth/")) {
    await refreshSession();
    response = await send(path, options); // A single retry; never a refresh loop.
  }
  if (!response.ok) throw await responseError(response);
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export async function loginSession(email: string, password: string) {
  if (refreshPromise) await refreshPromise.catch(() => undefined);
  const data = await requestJson<SessionResponse>("auth/token", {
    method: "POST",
    body: { email, password },
  });
  return acceptSession(data);
}
export async function logoutSession() {
  if (refreshPromise) await refreshPromise.catch(() => undefined);
  await requestJson<void>("auth/session", { method: "DELETE" });
  clearSession();
}
export function describeError(error: unknown) {
  if (error instanceof ApiError) return error.message;
  return "Не удалось связаться с сервером. Проверьте подключение и попробуйте снова.";
}

export async function updateOwnProfile(displayName: string) {
  const user = await requestJson<User>("users/me", {
    method: "PATCH",
    body: { display_name: displayName },
  });
  listeners.forEach((listener) => listener(user));
  return user;
}
