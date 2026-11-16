import { test, expect } from "@playwright/test";
import {
  api,
  fixtureMaster,
  registerClient,
  login,
  screenshot,
} from "./helpers.mjs";

test("available date survives catalog, profile and booking; empty dates can be cleared", async ({
  page,
  request,
}, testInfo) => {
  const { master } = await fixtureMaster(request, "08");
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: master.timezone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date());
  const today = ["year", "month", "day"]
    .map((key) => parts.find((part) => part.type === key).value)
    .join("-");
  const next = new Date(`${today}T00:00:00Z`);
  next.setUTCDate(next.getUTCDate() + 2);
  const date = next.toISOString().slice(0, 10);
  await page.goto(
    `/masters?search=${encodeURIComponent(master.display_name)}&available_on=${date}`,
  );
  await expect(page.locator(".master-card")).toHaveCount(1);
  await expect(page.getByLabel("Свободная дата")).toHaveValue(date);
  await page.reload();
  await page
    .getByRole("link", { name: `Профиль: ${master.display_name}`, exact: true })
    .click();
  await expect(page).toHaveURL(new RegExp(`date=${date}`));
  await page
    .getByRole("button", { name: "Свободное время", exact: true })
    .click();
  await expect(page.getByLabel("Дата посещения")).toHaveValue(date);
  await expect(
    page.getByRole("list", { name: "Свободные интервалы" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Записаться", exact: true }),
  ).toHaveAttribute("href", new RegExp(`date=${date}`));
  await page.getByRole("link", { name: "Перейти к записи" }).click();
  await expect(page).toHaveURL(/\/login$/);
  // ProtectedRoute keeps the return address in router state.
  // Verify the actual return after authentication instead of assuming a query parameter.
  const credentials = await registerClient(request);
  await page.getByLabel("Email", { exact: true }).fill(credentials.email);
  await page.getByLabel("Пароль", { exact: true }).fill(credentials.password);
  await page.getByRole("button", { name: "Войти", exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/book/${master.id}.*date=${date}`));
  await expect(page.getByLabel("Дата посещения")).toHaveValue(date);
  await expect(page.locator(".slot-options label").first()).toBeVisible();
  await page.goto("/masters?available_on=2030-02-30");
  await expect(page.getByRole("alert")).toContainText("Проверьте фильтры");
  await page.getByRole("link", { name: "Сбросить", exact: true }).click();
  await expect(page.locator(".master-card")).toHaveCount(12);
  for (const width of [320, 640, 1440]) {
    await page.setViewportSize({ width, height: 1000 });
    await page.evaluate(() => document.fonts.ready);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  }
  await screenshot(page, {
    path: testInfo.outputPath("dated-catalog.png"),
    fullPage: true,
  });
});

test("private overview uses real scoped data, refreshes after reload, and reflows with enlarged text", async ({
  page,
  request,
}, testInfo) => {
  const credentials = await registerClient(request);
  const session = await login(page, credentials);
  const response = await request.get(`${api}/overview`, {
    headers: { Authorization: `Bearer ${session.access_token}` },
  });
  expect(response.status()).toBe(200);
  expect(response.headers()["cache-control"]).toBe("no-store");
  expect((await response.json()).total).toBe(0);
  await expect(
    page.getByRole("heading", { name: "Обзор", exact: true }),
  ).toBeVisible();
  await expect(
    page
      .locator(".overview-grid")
      .locator("div")
      .filter({ has: page.getByText("Всего посещений", { exact: true }) })
      .locator("dd"),
  ).toHaveText("0");
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Обзор", exact: true }),
  ).toBeVisible();
  await page.setViewportSize({ width: 640, height: 1000 });
  // Text-size emulation plus a 640 CSS-pixel viewport checks reflow at 200%.
  // This is not a substitute for physical-device or assistive-technology testing.
  await page.addStyleTag({ content: "html { font-size: 200% !important; }" });
  await page.evaluate(() => document.fonts.ready);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await screenshot(page, {
    path: testInfo.outputPath("overview-large-text.png"),
    fullPage: true,
  });
});
