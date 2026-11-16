import { randomUUID } from "node:crypto";
import { test, expect } from "@playwright/test";

test("packaged React app authenticates through Nginx with CSP and restores the secure session", async ({
  page,
}, testInfo) => {
  const errors = [];
  const foreignApiRequests = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (
      url.pathname.startsWith("/api/") &&
      url.origin !== new URL(testInfo.project.use.baseURL).origin
    )
      foreignApiRequests.push(url.origin);
  });
  await page.addInitScript(() => {
    window.cspViolations = [];
    document.addEventListener("securitypolicyviolation", (event) => {
      window.cspViolations.push({
        directive: event.violatedDirective,
        uri: event.blockedURI,
      });
    });
  });
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await page.goto("/register");
  const email = `packaged-${randomUUID()}@example.com`;
  const password = `Packaged-${randomUUID()}`;
  await page.getByLabel("Ваше имя", { exact: true }).fill("Проверка сборки");
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel("Пароль", { exact: true }).fill(password);
  await page.getByLabel("Повторите пароль", { exact: true }).fill(password);
  await page
    .getByRole("button", { name: "Создать аккаунт", exact: true })
    .click();
  await expect(page).toHaveURL(/\/login$/);
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel("Пароль", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Войти", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Обзор", exact: true }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Обзор", exact: true }),
  ).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({
    path: testInfo.outputPath("packaged-dashboard.png"),
    fullPage: true,
  });
  expect(await page.evaluate(() => window.cspViolations)).toEqual([]);
  await page.goto("/masters");
  await expect(page.getByText(/По этим условиям мастеров нет/)).toBeVisible();
  expect(await page.evaluate(() => window.cspViolations)).toEqual([]);
  expect(foreignApiRequests).toEqual([]);
  expect(errors).toEqual([]);
});
