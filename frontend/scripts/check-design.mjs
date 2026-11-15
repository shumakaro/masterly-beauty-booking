import { chromium } from "@playwright/test";
import { fileURLToPath } from "node:url";
import { mkdir, writeFile } from "node:fs/promises";

const output = new URL("../../docs/evidence/", import.meta.url);
await mkdir(output, { recursive: true });
const browser = await chromium.launch({ channel: "msedge", headless: true });
const report = [];
const errors = [];
const page = await browser.newPage();
page.on("pageerror", (error) => errors.push(error.message));
for (const width of [320, 375, 430, 768, 1024, 1440, 1920]) {
  await page.setViewportSize({ width, height: 1000 });
  await page.goto("http://127.0.0.1:5174/", { waitUntil: "networkidle" });
  await page.evaluate(() => document.fonts.ready);
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > innerWidth,
  );
  const imagesLoaded = await page
    .locator("main img")
    .evaluateAll((images) =>
      images.every((image) => image.complete && image.naturalWidth > 0),
    );
  report.push({ width, overflow, imagesLoaded });
  if (overflow || !imagesLoaded)
    throw new Error(`Layout/assets failed at ${width}`);
  if ([375, 1440].includes(width))
    await page.screenshot({
      path: fileURLToPath(new URL(`home-${width}.png`, output)),
      fullPage: true,
    });
}
await page.setViewportSize({ width: 375, height: 900 });
await page.goto("http://127.0.0.1:5174/");
await page.getByRole("button", { name: "Открыть меню" }).click();
await page
  .getByRole("navigation")
  .getByRole("link", { name: /Стиль MASTERLY/ })
  .click();
await page.getByRole("heading", { name: /Тихая уверенность/ }).waitFor();
await page.goto("http://127.0.0.1:5174/brand", { waitUntil: "networkidle" });
await page.screenshot({
  path: fileURLToPath(new URL("brand-375.png", output)),
  fullPage: true,
});
await page.setViewportSize({ width: 1440, height: 1000 });
await page.screenshot({
  path: fileURLToPath(new URL("brand-1440.png", output)),
  fullPage: true,
});
await page.goto("http://127.0.0.1:5174/missing");
await page.getByRole("link", { name: /Вернуться на главную/ }).click();
await page.getByRole("heading", { level: 1, name: /Красота/ }).waitFor();
await page.emulateMedia({ reducedMotion: "reduce" });
const animation = await page
  .locator(".hero-copy")
  .evaluate((element) => getComputedStyle(element).animationName);
if (animation !== "none") throw new Error("Reduced motion is not respected");
if (errors.length) throw new Error(errors.join("\n"));
const result = {
  browser: "Microsoft Edge headless",
  report,
  navigation: "passed",
  reducedMotion: "passed",
  errors,
};
await writeFile(
  new URL("design-browser-check.json", output),
  JSON.stringify(result, null, 2),
);
console.log(JSON.stringify(result, null, 2));
await browser.close();
