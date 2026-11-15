import { expect, it, vi, afterEach, beforeEach } from "vitest";

beforeEach(() => {
  vi.resetModules();
  vi.stubEnv("VITE_API_BASE_URL", "http://localhost:8000/api/v1");
});
afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

it("preserves HTTP status and sanitized error details", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue({
        ok: false,
        status: 403,
        json: async () => ({
          error: {
            code: "FORBIDDEN",
            message: "Недостаточно прав.",
            fields: [],
          },
        }),
      }),
  );
  const { requestJson } = await import("./client");
  await expect(requestJson("health")).rejects.toMatchObject({
    status: 403,
    code: "FORBIDDEN",
  });
});

it("coordinates concurrent 401 responses with one refresh and one retry", async () => {
  const user = {
    id: "user-id",
    role: "CLIENT",
    display_name: "Test",
    email: "test@example.com",
  };
  let refreshes = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, options: RequestInit) => {
      if (url.endsWith("auth/token"))
        return {
          ok: true,
          status: 200,
          json: async () => ({ access_token: "old", user }),
        };
      if (url.endsWith("auth/refresh")) {
        refreshes++;
        return {
          ok: true,
          status: 200,
          json: async () => ({ access_token: "new", user }),
        };
      }
      const authorized =
        (options.headers as Record<string, string>).Authorization ===
        "Bearer new";
      return {
        ok: authorized,
        status: authorized ? 200 : 401,
        json: async () => (authorized ? user : {}),
      };
    }),
  );
  const { loginSession, requestJson } = await import("./client");
  await loginSession("test@example.com", "TestPassword123");
  expect(
    await Promise.all([requestJson("users/me"), requestJson("users/me")]),
  ).toEqual([user, user]);
  expect(refreshes).toBe(1);
});

it("stops after a failed refresh instead of looping", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) =>
      url.endsWith("auth/token")
        ? {
            ok: true,
            status: 200,
            json: async () => ({
              access_token: "old",
              user: { id: "id", role: "CLIENT" },
            }),
          }
        : { ok: false, status: 401, json: async () => ({}) },
    ),
  );
  const { loginSession, requestJson } = await import("./client");
  await loginSession("test@example.com", "TestPassword123");
  await expect(requestJson("users/me")).rejects.toMatchObject({ status: 401 });
  expect(fetch).toHaveBeenCalledTimes(3);
});
