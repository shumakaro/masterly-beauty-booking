import { randomUUID } from "node:crypto";
import { expect } from "@playwright/test";

export const api =
  process.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1";
export const writeHeaders = {
  Origin: "http://127.0.0.1:5173",
  "X-CSRF-Protection": "1",
};
export async function screenshot(page, options) {
  // Full-page capture must start at the top, otherwise Chromium can include
  // fixed controls that are correctly hidden above the current viewport.
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
  await page.evaluate(() => document.fonts.ready);
  return page.screenshot(options);
}
export function fixturePassword() {
  if (!process.env.BROWSER_TEST_PASSWORD)
    throw new Error(
      "BROWSER_TEST_PASSWORD is required for disposable browser fixtures",
    );
  return process.env.BROWSER_TEST_PASSWORD;
}
export async function registerClient(request) {
  const email = `booking-${randomUUID()}@example.com`;
  const password = `Test-${randomUUID()}`;
  const result = await request.post(`${api}/auth/register`, {
    headers: writeHeaders,
    data: { email, password, display_name: "Тест записи", role: "CLIENT" },
  });
  expect(result.status()).toBe(201);
  return { email, password };
}
export async function login(page, credentials) {
  await page.goto("/login");
  await page.getByLabel("Email", { exact: true }).fill(credentials.email);
  await page.getByLabel("Пароль", { exact: true }).fill(credentials.password);
  const response = page.waitForResponse(
    (response) =>
      response.url().endsWith("/auth/token") &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Войти", exact: true }).click();
  const result = await response;
  expect(result.status()).toBe(200);
  await expect(page).not.toHaveURL(/\/login/);
  return result.json();
}
export async function fixtureMaster(request, number = "01") {
  const response = await request.get(
    `${api}/masters?search=${encodeURIComponent(`Демо Каталог ${number}`)}`,
  );
  expect(response.status()).toBe(200);
  const master = (await response.json()).items.find(
    (item) => item.display_name === `Демо Каталог ${number}`,
  );
  expect(master).toBeTruthy();
  const result = await request.get(`${api}/masters/${master.id}/services`);
  const offers = (await result.json()).items;
  return { master, offer: offers[0] };
}
export async function chooseTime(page, master, offer) {
  await page.goto(`/book/${master.id}?offer=${offer.id}`);
  const input = page.getByLabel("Дата посещения");
  const date = new Date(`${await input.inputValue()}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + 1);
  await input.fill(date.toISOString().slice(0, 10));
  const first = page.locator(".slot-options label").first();
  await first.click();
  const start = await first.locator("input").getAttribute("value");
  await page.getByRole("button", { name: "Продолжить", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Все верно?" })).toBeVisible();
  return start;
}
export async function cancelBooking(page) {
  await page
    .getByRole("button", { name: "Отменить запись", exact: true })
    .click();
  await page.getByRole("button", { name: "Подтвердить", exact: true }).click();
  await expect(page.locator(".booking-status")).toHaveText("Отменена");
}
