import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { screenshot } from "./helpers.mjs";

test("catalog loads its bundled typefaces without falling back after failed font requests", async ({
  page,
}) => {
  const failedFonts = [];
  page.on("response", (response) => {
    const path = new URL(response.url()).pathname;
    if (/\.(woff2?|ttf)$/.test(path) && response.status() >= 400)
      failedFonts.push({
        file: path.split("/").at(-1),
        status: response.status(),
      });
  });
  await page.goto("/masters?search=" + encodeURIComponent("Амина Садыкова"));
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
  const loaded = await page.evaluate(() =>
    [...document.fonts]
      .filter((font) => font.status === "loaded")
      .map((font) => font.family),
  );
  expect(failedFonts).toEqual([]);
  expect(loaded.some((family) => family.includes("Manrope"))).toBe(true);
  expect(loaded.some((family) => family.includes("Cormorant Garamond"))).toBe(
    true,
  );
});

for (const width of [375, 768, 1440]) {
  test(`rich profile and demo reviews remain usable at ${width}px`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width, height: 950 });
    await page.goto("/masters?search=Амина%20Садыкова");
    await expect(page.locator(".master-card")).toHaveCount(1);
    await expect(
      page.getByText("Маникюр и дизайн ногтей", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByText("Опыт работы: 8 лет", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("img", { name: "Амина Садыкова", exact: true }),
    ).toBeVisible();
    await page
      .getByRole("link", { name: "Подробнее: Амина Садыкова", exact: true })
      .click();
    await expect(
      page.getByRole("heading", { name: "Амина Садыкова", exact: true }),
    ).toBeVisible();
    await expect(page.getByText(/Демонстрационный профиль. Имя/)).toBeVisible();
    await expect(
      page.getByText("Маникюр в естественном стиле", { exact: true }).first(),
    ).toBeVisible();
    await expect(
      page.getByRole("img", {
        name: "Фотография результата к отзыву",
        exact: true,
      }),
    ).toHaveCount(2);
    await expect(
      page.getByText("Пример отзыва · демонстрационные данные", {
        exact: true,
      }),
    ).toHaveCount(2);
    await page
      .getByRole("button", { name: /Увеличить:/ })
      .first()
      .click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).not.toBeVisible();
    const results = await new AxeBuilder({ page }).analyze();
    await testInfo.attach("profile-axe", {
      body: JSON.stringify(results),
      contentType: "application/json",
    });
    expect(results.violations).toEqual([]);
    await screenshot(page, {
      path: testInfo.outputPath(`rich-profile-${width}.png`),
      fullPage: true,
    });
  });
}
