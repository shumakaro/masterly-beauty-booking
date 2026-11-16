import { test, expect } from "@playwright/test";

test("catalog uses real API filters, pagination, reload and browser history", async ({
  page,
}) => {
  await page.goto("/masters?search=Демо%20Каталог");
  await expect(page.locator(".master-card")).toHaveCount(12);
  await expect(page.getByRole("status")).toContainText("Найдено мастеров: 14");
  await page.getByRole("link", { name: "Далее →" }).click();
  await expect(page).toHaveURL(/page=2/);
  await expect(page.locator(".master-card")).toHaveCount(2);
  await page.reload();
  await expect(page.locator(".master-card")).toHaveCount(2);
  await page
    .getByLabel("Направление", { exact: true })
    .selectOption({ label: "Волосы" });
  await page.getByLabel("Цена до, ₸").fill("3000");
  await page.getByLabel("Сортировка").selectOption("price_desc");
  await page.getByRole("button", { name: "Найти", exact: true }).click();
  await expect(page).not.toHaveURL(/page=2/);
  await expect(page.locator(".master-card")).toHaveCount(4);
  await expect(page.locator(".master-card h2").first()).toHaveText(
    "Демо Каталог 05",
  );
  await page.goBack();
  await expect(page).toHaveURL(/page=2/);
  await expect(page.locator(".master-card")).toHaveCount(2);
  await page.goForward();
  await expect(page.getByLabel("Цена до, ₸")).toHaveValue("3000");
  await page.getByLabel("Поиск", { exact: true }).fill("ничего-не-найдется");
  await page.getByRole("button", { name: "Найти", exact: true }).click();
  await expect(page.getByText(/По этим условиям мастеров нет/)).toBeVisible();
  await page.goto("/masters?min_price=900&max_price=100");
  await expect(page.getByRole("alert")).toContainText("Проверьте фильтры");
});

test("profile shows real services, availability timezone and accessible portfolio", async ({
  page,
}, testInfo) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/masters?search=Демо%20Каталог%2001");
  await page
    .getByRole("link", { name: "Профиль: Демо Каталог 01", exact: true })
    .click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Демо Каталог 01",
  );
  await expect(
    page.getByText("Пока без отзывов", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Демо-стрижка", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Свободное время", exact: true })
    .click();
  const dateInput = page.getByLabel("Дата посещения");
  const today = await dateInput.inputValue();
  const next = new Date(`${today}T00:00:00Z`);
  next.setUTCDate(next.getUTCDate() + 1);
  await dateInput.fill(next.toISOString().slice(0, 10));
  await expect(
    page.getByRole("list", { name: "Свободные интервалы" }),
  ).toBeVisible();
  await expect(
    page
      .getByRole("list", { name: "Свободные интервалы" })
      .locator("li")
      .first(),
  ).toContainText("09:00 GMT+5");
  const enlarge = page.getByRole("button", { name: /Увеличить:/ });
  await enlarge.click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Закрыть фотографию" }),
  ).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await expect(enlarge).toBeFocused();
  await expect(
    page.getByText(/Отзывов пока нет. Их могут оставить/),
  ).toBeVisible();
  const profile = page.url();
  for (const width of [320, 375, 768, 1440]) {
    await page.setViewportSize({ width, height: 1000 });
    for (const route of [
      "/masters?search=Демо%20Каталог",
      "/services",
      profile,
    ]) {
      await page.goto(route);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      await expect(
        page.getByText("Загружаем данные…", { exact: true }),
      ).toHaveCount(0);
      await page.evaluate(() => document.fonts.ready);
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth > innerWidth,
        ),
      ).toBe(false);
      if ([375, 1440].includes(width)) {
        const name =
          new URL(page.url()).pathname === "/masters"
            ? "masters"
            : new URL(page.url()).pathname === "/services"
              ? "services"
              : "profile";
        await page.screenshot({
          path: testInfo.outputPath(`${name}-${width}.png`),
          fullPage: true,
        });
      }
    }
  }
  expect(errors).toEqual([]);
});

test("services lead to their category and a missing profile offers recovery", async ({
  page,
}) => {
  await page.goto("/services");
  await expect(page.locator(".service-card")).toHaveCount(2);
  const service = page.locator(".service-card").filter({
    has: page.getByRole("heading", { name: "Демо-маникюр", exact: true }),
  });
  await service
    .getByRole("link", { name: /Мастера этого направления/ })
    .click();
  await expect(page.locator(".master-card")).toHaveCount(1);
  await expect(page.locator(".master-card h2")).toHaveText("Демо Каталог 02");
  await page.goto("/masters/00000000-0000-4000-8000-000000000099");
  await expect(
    page.getByRole("heading", { name: "Мастер не найден." }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Вернуться в каталог" }).click();
  await expect(page).toHaveURL("/masters");
});
