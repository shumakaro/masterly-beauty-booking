import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { randomUUID } from "node:crypto";
import {
  fixtureMaster,
  fixturePassword,
  login,
  screenshot,
} from "./helpers.mjs";

async function ready(page) {
  if (await page.getByRole("dialog").count())
    await expect(page.getByRole("dialog")).toBeVisible();
  else await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(
    page.getByText(/^(Загружаем…|Загружаем данные…|Проверяем сессию…)$/),
  ).toHaveCount(0);
  await page.evaluate(async () => {
    await document.fonts.ready;
    document.getAnimations().forEach((animation) => {
      if (animation.effect?.getTiming().iterations !== Infinity)
        animation.finish();
    });
  });
}
async function audit(page, testInfo, name) {
  await ready(page);
  const report = await new AxeBuilder({ page })
    .withTags([
      "wcag2a",
      "wcag2aa",
      "wcag21a",
      "wcag21aa",
      "wcag22aa",
      "best-practice",
    ])
    .analyze();
  await testInfo.attach(`${name}-axe.json`, {
    body: JSON.stringify(report, null, 2),
    contentType: "application/json",
  });
  expect(
    report.violations.map((violation) => ({
      id: violation.id,
      impact: violation.impact,
      nodes: violation.nodes.map((node) => ({
        target: node.target,
        summary: node.failureSummary,
      })),
    })),
  ).toEqual([]);
}

test("theme follows the device, survives reload and synchronizes between tabs", async ({
  page,
  context,
}) => {
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  const picker = page.getByRole("combobox", {
    name: "Цветовая тема",
    exact: true,
  });
  await picker.selectOption("light");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  const other = await context.newPage();
  await other.goto("/services");
  await picker.selectOption("dark");
  await expect(other.locator("html")).toHaveAttribute("data-theme", "dark");
  await picker.selectOption("system");
  await page.emulateMedia({ colorScheme: "light" });
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await other.close();
});

for (const theme of ["light", "dark"])
  for (const width of [375, 1440]) {
    test(`public pages: axe, responsive layout, ${theme} ${width}px`, async ({
      page,
      request,
    }, testInfo) => {
      await page.setViewportSize({ width, height: 1000 });
      await page.emulateMedia({ reducedMotion: "reduce" });
      await page.goto("/");
      await page
        .getByRole("combobox", { name: "Цветовая тема", exact: true })
        .selectOption(theme);
      const { master } = await fixtureMaster(request);
      for (const [name, path] of [
        ["home", "/"],
        ["masters", "/masters"],
        ["services", "/services"],
        ["profile", `/masters/${master.id}`],
        ["brand", "/brand"],
        ["login", "/login"],
        ["register", "/register"],
        ["404", "/missing-page"],
      ]) {
        await page.goto(path);
        await audit(page, testInfo, name);
        expect(
          await page.evaluate(
            () => document.documentElement.scrollWidth > innerWidth,
          ),
        ).toBe(false);
        if (["home", "profile", "brand"].includes(name))
          await screenshot(page, {
            path: testInfo.outputPath(`${name}-${theme}-${width}.png`),
            fullPage: true,
          });
      }
    });
  }

test("keyboard skip link, mobile disclosure, route focus and gallery trap", async ({
  page,
  request,
}, testInfo) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setViewportSize({ width: 375, height: 1000 });
  await page.goto("/");
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("link", { name: "Перейти к содержимому" }),
  ).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("main")).toBeFocused();
  const menu = page.getByRole("button", { name: "Открыть меню" });
  await menu.focus();
  await page.keyboard.press("Enter");
  await expect(
    page
      .getByRole("navigation", { name: "Основная навигация" })
      .getByRole("link", { name: "Мастера", exact: true }),
  ).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(menu).toBeFocused();
  await expect(menu).toHaveAttribute("aria-expanded", "false");
  await page.keyboard.press("Enter");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL("/masters");
  await expect(page.getByRole("heading", { level: 1 })).toBeFocused();
  const { master } = await fixtureMaster(request);
  await page.goto(`/masters/${master.id}`);
  const enlarge = page.getByRole("button", { name: /Увеличить:/ });
  await enlarge.focus();
  await page.keyboard.press("Enter");
  const close = page.getByRole("button", { name: "Закрыть фотографию" });
  await expect(close).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(close).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await expect(close).toBeFocused();
  await audit(page, testInfo, "gallery");
  await page.keyboard.press("Escape");
  await expect(enlarge).toBeFocused();
  expect(
    await page.evaluate(
      () =>
        document
          .getAnimations()
          .filter((animation) => animation.playState === "running").length,
    ),
  ).toBe(0);
});

test("loading skeleton, retry and real empty results remain distinct", async ({
  page,
}, testInfo) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  let release;
  const gate = new Promise((resolve) => {
    release = resolve;
  });
  await page.route("**/api/v1/masters?**", async (route) => {
    await gate;
    await route.continue();
  });
  await page.goto("/masters");
  await expect(
    page.getByText("Загружаем данные…", { exact: true }),
  ).toBeVisible();
  await expect(page.locator(".skeleton-lines")).toHaveAttribute(
    "aria-hidden",
    "true",
  );
  await screenshot(page, {
    path: testInfo.outputPath("loading-state.png"),
    fullPage: true,
  });
  release();
  await expect(page.locator(".master-card")).toHaveCount(12);
  await page.unroute("**/api/v1/masters?**");
  await page.route("**/api/v1/masters?**", (route) => route.abort());
  await page.reload();
  await expect(page.getByRole("alert")).toContainText("Не удалось связаться");
  await page.unroute("**/api/v1/masters?**");
  await page.getByRole("button", { name: "Повторить загрузку" }).click();
  await expect(page.locator(".master-card")).toHaveCount(12);
  await page.goto(`/masters?search=${randomUUID()}`);
  await expect(page.getByText(/По этим условиям мастеров нет/)).toBeVisible();
  await audit(page, testInfo, "empty-result");
});

for (const [role, email, path, tabs] of [
  [
    "CLIENT",
    "browser-client@example.test",
    "/dashboard",
    ["bookings", "favorites", "reviews"],
  ],
  [
    "MASTER",
    "catalog-0@example.test",
    "/master/dashboard",
    [
      "bookings",
      "business-profile",
      "offers",
      "schedules",
      "exceptions",
      "portfolio",
    ],
  ],
  [
    "ADMIN",
    "browser-admin@example.test",
    "/admin",
    ["bookings", "users", "masters", "categories", "services"],
  ],
])
  test(`${role}: dark workspace forms and keyboard edit recovery`, async ({
    page,
  }, testInfo) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await login(page, { email, password: fixturePassword() });
    await page
      .getByRole("combobox", { name: "Цветовая тема", exact: true })
      .selectOption("dark");
    for (const tab of tabs) {
      await page.goto(`${path}?tab=${tab}`);
      await audit(page, testInfo, tab);
      const create = page.locator("details > summary");
      if (await create.count()) {
        await create.click();
        await audit(page, testInfo, `${tab}-form`);
      }
    }
    if (role === "MASTER") {
      await page.goto(`${path}?tab=offers`);
      const item = page.locator(".resource-item").first();
      const edit = item.getByRole("button", { name: "Изменить", exact: true });
      await edit.focus();
      await page.keyboard.press("Enter");
      await expect(
        item.getByRole("spinbutton", { name: "Стоимость, ₸", exact: true }),
      ).toBeFocused();
      await item
        .getByRole("button", { name: "Закрыть редактирование" })
        .click();
      await expect(edit).toBeFocused();
      const disable = item.getByRole("button", {
        name: "Отключить",
        exact: true,
      });
      await disable.click();
      await expect(
        item.getByRole("button", { name: "Подтвердить", exact: true }),
      ).toBeFocused();
      await page.keyboard.press("Escape");
      await expect(disable).toBeFocused();
    }
    await screenshot(page, {
      path: testInfo.outputPath(`${role.toLowerCase()}-dark-workspace.png`),
      fullPage: true,
    });
  });
