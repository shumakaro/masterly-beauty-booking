import { test, expect } from "@playwright/test";
import { randomUUID } from "node:crypto";
import {
  api,
  writeHeaders,
  fixturePassword,
  login,
  fixtureMaster,
  registerClient,
} from "./helpers.mjs";

async function openCreate(page) {
  await page.locator("details > summary").click();
  return page.locator("details .workspace-form");
}
async function remove(item) {
  await item.getByRole("button", { name: "Удалить", exact: true }).click();
  await item.getByRole("button", { name: "Подтвердить", exact: true }).click();
  await expect(item).toHaveCount(0);
}

test("master completes a real visit; client creates, edits and deletes their review", async ({
  page,
  request,
}, testInfo) => {
  await login(page, {
    email: "catalog-0@example.test",
    password: fixturePassword(),
  });
  const visit = page
    .locator(".booking-card")
    .filter({ hasText: "Прошедшее демо-посещение" });
  await visit.getByRole("button", { name: "Завершить посещение" }).click();
  await visit.getByRole("button", { name: "Подтвердить", exact: true }).click();
  await expect(visit.locator(".booking-status")).toHaveText("Завершена");
  await page.getByRole("button", { name: "Выйти из аккаунта" }).click();
  await login(page, {
    email: "browser-client@example.test",
    password: fixturePassword(),
  });
  const card = page
    .locator(".booking-card")
    .filter({ hasText: "Прошедшее демо-посещение" });
  await card
    .getByRole("button", { name: "Оставить отзыв", exact: true })
    .click();
  await card.getByLabel("Ваш отзыв").fill("Проверено настоящим посещением");
  await card.getByRole("button", { name: "Добавить", exact: true }).click();
  await expect(card.getByRole("link", { name: "Мой отзыв →" })).toBeVisible();
  const { master } = await fixtureMaster(request);
  expect(
    (await (await request.get(`${api}/masters/${master.id}`)).json()).rating,
  ).toBe(5);
  await card.getByRole("link", { name: "Мой отзыв →" }).click();
  const review = page
    .locator(".resource-item")
    .filter({ hasText: "Проверено настоящим посещением" });
  await review.getByRole("button", { name: "Изменить", exact: true }).click();
  await review.getByLabel("Оценка от 1 до 5").fill("4");
  await review.getByLabel("Ваш отзыв").fill("Отзыв изменен клиентом");
  await review.getByRole("button", { name: "Сохранить изменения" }).click();
  await expect(
    page.getByRole("heading", { name: "Оценка 4 / 5" }),
  ).toBeVisible();
  await page.screenshot({
    path: testInfo.outputPath("client-reviews.png"),
    fullPage: true,
  });
  expect(
    (await (await request.get(`${api}/masters/${master.id}`)).json()).rating,
  ).toBe(4);
  await remove(
    page
      .locator(".resource-item")
      .filter({ hasText: "Отзыв изменен клиентом" }),
  );
  expect(
    (await (await request.get(`${api}/masters/${master.id}`)).json()).rating,
  ).toBe(null);
});

test("master manages offers, work intervals, special dates, profile and portfolio", async ({
  page,
  request,
}, testInfo) => {
  await login(page, {
    email: "catalog-0@example.test",
    password: fixturePassword(),
  });
  await page.getByRole("link", { name: "Мои услуги", exact: true }).click();
  let form = await openCreate(page);
  await form
    .getByRole("combobox", { name: "Услуга каталога", exact: true })
    .selectOption({ label: "Демо-маникюр" });
  await form.getByLabel("Стоимость, ₸").fill("2500");
  await form.getByRole("button", { name: "Добавить", exact: true }).click();
  let item = page
    .locator(".resource-item")
    .filter({ has: page.getByRole("heading", { name: /Демо-маникюр/ }) });
  await item.getByRole("button", { name: "Изменить", exact: true }).click();
  await item.getByLabel("Длительность в минутах").fill("90");
  await item.getByRole("button", { name: "Сохранить изменения" }).click();
  await expect(item.getByRole("heading")).toContainText("90 мин");
  await item.getByRole("button", { name: "Отключить", exact: true }).click();
  await item.getByRole("button", { name: "Подтвердить", exact: true }).click();
  await expect(item.getByRole("heading")).toContainText("Отключено");
  await page.getByRole("link", { name: "Рабочая неделя", exact: true }).click();
  form = await openCreate(page);
  await form
    .getByRole("combobox", { name: "День недели", exact: true })
    .selectOption("0");
  await form.getByLabel("Начало работы").fill("18:00");
  await form.getByLabel("Конец работы").fill("19:00");
  await form.getByRole("button", { name: "Добавить", exact: true }).click();
  item = page
    .locator(".resource-item")
    .filter({ hasText: "Понедельник · 18:00–19:00" });
  await item.getByRole("button", { name: "Изменить", exact: true }).click();
  await item.getByLabel("Начало работы").fill("19:00");
  await item.getByLabel("Конец работы").fill("20:00");
  await item.getByRole("button", { name: "Сохранить изменения" }).click();
  await remove(
    page
      .locator(".resource-item")
      .filter({ hasText: "Понедельник · 19:00–20:00" }),
  );
  await page.getByRole("link", { name: "Особые даты", exact: true }).click();
  form = await openCreate(page);
  const future = new Date();
  future.setUTCDate(future.getUTCDate() + 7);
  await form
    .getByLabel("Дата", { exact: true })
    .fill(future.toISOString().slice(0, 10));
  await form.getByRole("button", { name: "Добавить", exact: true }).click();
  item = page.locator(".resource-item").filter({ hasText: "Выходной" });
  await item.getByRole("button", { name: "Изменить", exact: true }).click();
  await item.getByLabel("Выходной", { exact: true }).uncheck();
  await item.getByLabel("Начало работы").fill("10:00");
  await item.getByLabel("Конец работы").fill("12:00");
  await item.getByRole("button", { name: "Сохранить изменения" }).click();
  await remove(
    page.locator(".resource-item").filter({ hasText: "10:00–12:00" }),
  );
  await page.getByRole("link", { name: "Портфолио", exact: true }).click();
  form = await openCreate(page);
  await form
    .getByLabel("Ссылка на изображение", { exact: true })
    .fill("http://127.0.0.1:5173/images/nails-editorial.jpg");
  await form.getByLabel("Описание фотографии").fill("Тест портфолио");
  await form
    .getByLabel("Лицензия или разрешение на использование")
    .fill("Unsplash License · демо");
  await form.getByRole("button", { name: "Добавить", exact: true }).click();
  item = page.locator(".resource-item").filter({ hasText: "Тест портфолио" });
  await item.getByRole("button", { name: "Изменить", exact: true }).click();
  await item.getByLabel("Описание фотографии").fill("Обновленная работа");
  await item.getByLabel("Позиция в портфолио").fill("2");
  await item.getByRole("button", { name: "Сохранить изменения" }).click();
  await remove(
    page.locator(".resource-item").filter({ hasText: "Обновленная работа" }),
  );
  await page
    .getByRole("link", { name: "Профиль мастера", exact: true })
    .click();
  await page
    .getByRole("textbox", { name: "О себе", exact: true })
    .fill("Демонстрационный профиль, обновленный мастером.");
  await page.getByRole("checkbox", { name: "Профиль опубликован" }).uncheck();
  await page.getByRole("button", { name: "Сохранить изменения" }).click();
  await expect(page.getByRole("status")).toHaveText("Сохранено.");
  const hidden = await request.get(
    `${api}/masters?search=${encodeURIComponent("Демо Каталог 01")}`,
  );
  expect((await hidden.json()).total).toBe(0);
  await page.getByRole("checkbox", { name: "Профиль опубликован" }).check();
  await page.getByRole("button", { name: "Сохранить изменения" }).click();
  await expect(page.getByRole("status")).toHaveText("Сохранено.");
  for (const width of [320, 375, 768, 1440]) {
    await page.setViewportSize({ width, height: 1000 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth,
      ),
    ).toBe(false);
    if ([375, 1440].includes(width))
      await page.screenshot({
        path: testInfo.outputPath(`master-profile-${width}.png`),
        fullPage: true,
      });
  }
});

test("administrator manages catalog, visibility, user status and reasoned cancellation", async ({
  page,
  request,
}, testInfo) => {
  await login(page, {
    email: "browser-admin@example.test",
    password: fixturePassword(),
  });
  await page.getByRole("link", { name: "Направления", exact: true }).click();
  let form = await openCreate(page);
  await form.getByLabel("Название направления").fill("Тестовое направление");
  await form.getByLabel(/Короткое название латиницей/).fill("browser-care");
  await form.getByRole("button", { name: "Добавить", exact: true }).click();
  await expect(
    page.locator(".resource-item").filter({ hasText: "Тестовое направление" }),
  ).toBeVisible();
  await page
    .locator(".workspace-tabs")
    .getByRole("link", { name: "Услуги", exact: true })
    .click();
  form = await openCreate(page);
  await form
    .getByRole("combobox", { name: "Направление", exact: true })
    .selectOption({ label: "Тестовое направление" });
  await form.getByLabel("Название услуги").fill("Тестовая процедура");
  await form.getByRole("button", { name: "Добавить", exact: true }).click();
  let item = page
    .locator(".resource-item")
    .filter({ hasText: "Тестовая процедура" });
  await item.getByRole("button", { name: "Изменить", exact: true }).click();
  await item
    .getByLabel("Описание", { exact: true })
    .fill("Описание администратора");
  await item.getByRole("button", { name: "Сохранить изменения" }).click();
  await page.getByRole("link", { name: "Направления", exact: true }).click();
  item = page
    .locator(".resource-item")
    .filter({ hasText: "Тестовое направление" });
  await item.getByRole("button", { name: "Удалить", exact: true }).click();
  await item.getByRole("button", { name: "Подтвердить", exact: true }).click();
  await expect(item.getByRole("alert")).toBeVisible(); // FK conflict is surfaced, not silently discarded.
  await item.getByRole("button", { name: "Оставить", exact: true }).click();
  await page
    .locator(".workspace-tabs")
    .getByRole("link", { name: "Услуги", exact: true })
    .click();
  await remove(
    page.locator(".resource-item").filter({ hasText: "Тестовая процедура" }),
  );
  await page.getByRole("link", { name: "Направления", exact: true }).click();
  await remove(
    page.locator(".resource-item").filter({ hasText: "Тестовое направление" }),
  );
  const client = await registerClient(request);
  await page.getByRole("link", { name: "Пользователи", exact: true }).click();
  item = page.locator(".resource-item").filter({ hasText: client.email });
  await item.getByRole("button", { name: "Изменить", exact: true }).click();
  await item.getByLabel("Активно", { exact: true }).uncheck();
  await item.getByRole("button", { name: "Сохранить изменения" }).click();
  await expect(item.getByRole("heading")).toContainText("Заблокирован");
  expect(
    (
      await request.post(`${api}/auth/token`, {
        headers: writeHeaders,
        data: client,
      })
    ).status(),
  ).toBe(401);
  await item.getByRole("button", { name: "Изменить", exact: true }).click();
  await item.getByLabel("Активно", { exact: true }).check();
  await item.getByRole("button", { name: "Сохранить изменения" }).click();
  await expect(item.getByRole("heading")).toContainText("Активен");
  await page
    .locator(".workspace-tabs")
    .getByRole("link", { name: "Мастера", exact: true })
    .click();
  const { master } = await fixtureMaster(request);
  item = page.locator(".resource-item").filter({ hasText: "Демо Каталог 01" });
  await expect(
    page.getByRole("heading", { name: "Видимость мастеров" }),
  ).toBeVisible();
  await expect(page.getByText("Загружаем…", { exact: true })).toHaveCount(0);
  if ((await item.count()) === 0)
    await page.getByRole("link", { name: "Далее →", exact: true }).click();
  await item.getByRole("button", { name: "Изменить", exact: true }).click();
  await item.getByLabel("Профиль опубликован").uncheck();
  await item.getByRole("button", { name: "Сохранить изменения" }).click();
  await expect(item.getByRole("heading")).toContainText("Скрыт");
  expect((await request.get(`${api}/masters/${master.id}`)).status()).toBe(404);
  await item.getByRole("button", { name: "Изменить", exact: true }).click();
  await item.getByLabel("Профиль опубликован").check();
  await item.getByRole("button", { name: "Сохранить изменения" }).click();
  await expect(item.getByRole("heading")).toContainText("Опубликован");
  const tokenResponse = await request.post(`${api}/auth/token`, {
    headers: writeHeaders,
    data: client,
  });
  expect(tokenResponse.status()).toBe(200);
  const token = (await tokenResponse.json()).access_token;
  const target = await fixtureMaster(request, "06");
  const tomorrow = new Date();
  tomorrow.setUTCDate(tomorrow.getUTCDate() + 1);
  const slots = await request.get(
    `${api}/masters/${target.master.id}/availability?master_service_id=${target.offer.id}&date=${tomorrow.toISOString().slice(0, 10)}`,
  );
  const start = (await slots.json()).slots[0].starts_at;
  const created = await request.post(`${api}/bookings`, {
    headers: {
      ...writeHeaders,
      Authorization: `Bearer ${token}`,
      "Idempotency-Key": randomUUID(),
    },
    data: { master_service_id: target.offer.id, starts_at: start },
  });
  expect(created.status()).toBe(201);
  const booking = await created.json();
  await page.goto(`/bookings/${booking.id}`);
  await page
    .getByRole("button", { name: "Отменить запись", exact: true })
    .click();
  await page.getByRole("button", { name: "Подтвердить", exact: true }).click();
  await expect(page.locator(".booking-status")).toHaveText("Подтверждена");
  await page
    .getByRole("textbox", { name: /Причина отмены/ })
    .fill("Отмена администратором по обращению клиента");
  await page.getByRole("button", { name: "Подтвердить", exact: true }).click();
  await expect(page.locator(".booking-status")).toHaveText("Отменена");
  await expect(
    page.getByText("Отмена администратором по обращению клиента", {
      exact: true,
    }),
  ).toBeVisible();
  await page.goto("/admin?tab=users");
  for (const width of [320, 375, 768, 1440]) {
    await page.setViewportSize({ width, height: 1000 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth,
      ),
    ).toBe(false);
    if ([375, 1440].includes(width))
      await page.screenshot({
        path: testInfo.outputPath(`admin-users-${width}.png`),
        fullPage: true,
      });
  }
});
