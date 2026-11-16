import { test, expect } from "@playwright/test";
import {
  api,
  registerClient,
  login,
  fixtureMaster,
  chooseTime,
  cancelBooking,
} from "./helpers.mjs";

test("a lost booking response can be retried without duplicate creation; reload and cancellation persist", async ({
  page,
  request,
}, testInfo) => {
  const credentials = await registerClient(request);
  const session = await login(page, credentials);
  const { master, offer } = await fixtureMaster(request, "03");
  const keys = [];
  let lost = false;
  await page.route("**/api/v1/bookings", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    keys.push(route.request().headers()["idempotency-key"]);
    if (!lost) {
      const response = await route.fetch();
      expect(response.status()).toBe(201); // The real server commits before the response is lost.
      lost = true;
      await route.abort("failed");
    } else await route.continue();
  });
  const start = await chooseTime(page, master, offer);
  for (const width of [320, 375, 768, 1440]) {
    await page.setViewportSize({ width, height: 1000 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth,
      ),
    ).toBe(false);
    if ([375, 1440].includes(width))
      await page.screenshot({
        path: testInfo.outputPath(`booking-confirm-${width}.png`),
        fullPage: true,
      });
  }
  await page
    .getByRole("button", { name: "Подтвердить запись", exact: true })
    .click();
  await expect(
    page.getByText(/Ответ не получен. Запись могла сохраниться/),
  ).toBeVisible();
  await page.reload();
  await page
    .getByRole("button", { name: "Восстановить подтверждение", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Проверить и повторить", exact: true })
    .click();
  await expect(page).toHaveURL(/\/bookings\/[0-9a-f-]+$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Запись подтверждена.",
  );
  expect(keys).toHaveLength(2);
  expect(keys[0]).toBe(keys[1]);
  const response = await request.get(`${api}/bookings`, {
    headers: { Authorization: `Bearer ${session.access_token}` },
  });
  const items = (await response.json()).items.filter(
    (item) => item.starts_at === start && item.master_id === master.id,
  );
  expect(items).toHaveLength(1);
  await page.reload();
  await expect(page.locator(".booking-status")).toHaveText("Подтверждена");
  await page.screenshot({
    path: testInfo.outputPath("booking-created.png"),
    fullPage: true,
  });
  await cancelBooking(page);
  await page.reload();
  await expect(page.locator(".booking-status")).toHaveText("Отменена");
  const availability = await request.get(
    `${api}/masters/${master.id}/availability?master_service_id=${offer.id}&date=${start.slice(0, 10)}`,
  );
  expect(
    (await availability.json()).slots.some((slot) => slot.starts_at === start),
  ).toBe(true);
  await page.getByRole("link", { name: "← В кабинет" }).click();
  await expect(page.locator(".booking-card")).toHaveCount(1);
});

test("two clients choosing the same time receive one booking and a recoverable conflict", async ({
  page,
  browser,
  request,
}) => {
  const context = await browser.newContext({
    baseURL: "http://127.0.0.1:5173",
  });
  const other = await context.newPage();
  try {
    await login(page, await registerClient(request));
    await login(other, await registerClient(request));
    const { master, offer } = await fixtureMaster(request, "04");
    const first = await chooseTime(page, master, offer);
    const second = await chooseTime(other, master, offer);
    expect(first).toBe(second);
    await page
      .getByRole("button", { name: "Подтвердить запись", exact: true })
      .click();
    await expect(page).toHaveURL(/\/bookings\//);
    await other
      .getByRole("button", { name: "Подтвердить запись", exact: true })
      .click();
    await expect(other.getByText(/Условия записи изменились/)).toBeVisible();
    await expect(
      other.getByRole("button", { name: "Продолжить", exact: true }),
    ).toBeDisabled();
    await expect(
      other.locator(`.slot-options input[value="${first}"]`),
    ).toHaveCount(0);
    await expect(other).toHaveURL(/\/book\//);
    await cancelBooking(page);
  } finally {
    await context.close();
  }
});

test("a guest returns to the selected offer after sign-in and can save a favorite", async ({
  page,
  request,
}) => {
  const { master, offer } = await fixtureMaster(request, "05");
  const credentials = await registerClient(request);
  const path = `/book/${master.id}?offer=${offer.id}`;
  await page.goto(path);
  await expect(page).toHaveURL("/login");
  await page.getByLabel("Email", { exact: true }).fill(credentials.email);
  await page.getByLabel("Пароль", { exact: true }).fill(credentials.password);
  await page.getByRole("button", { name: "Войти", exact: true }).click();
  await expect(page).toHaveURL(path);
  await expect(
    page.getByRole("combobox", { name: "Услуга", exact: true }),
  ).toHaveValue(offer.id);
  await page.goto(`/masters/${master.id}`);
  await page.getByRole("button", { name: "В избранное", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "В избранном · убрать" }),
  ).toHaveAttribute("aria-pressed", "true");
  await page.goto("/favorites");
  await expect(page).toHaveURL("/dashboard?tab=favorites");
  await expect(page.locator(".resource-item h3")).toHaveText(
    master.display_name,
  );
  await page.getByRole("button", { name: "Убрать из избранного" }).click();
  await expect(page.locator(".resource-item")).toHaveCount(0);
});
