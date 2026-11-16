import { randomUUID } from 'node:crypto';
import { test, expect } from '@playwright/test';

for (const role of ['CLIENT', 'MASTER']) {
  test(`${role}: registration, login, reload, own profile and logout`, async ({ page, context }, testInfo) => {
    const email = `${role.toLowerCase()}-${randomUUID()}@example.com`;
    const password = `Test-${randomUUID()}`; // Generated per disposable CI account, never production.
    const name = role === 'CLIENT' ? 'Тестовый клиент' : 'Тестовый мастер';
    const path = role === 'CLIENT' ? '/dashboard' : '/master/dashboard';
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto('/register');
    if (role === 'MASTER') await page.getByRole('radio', { name: 'Я мастер' }).check();
    await page.getByLabel('Ваше имя', { exact: true }).fill(name);
    await page.getByLabel('Email', { exact: true }).fill(email);
    await page.getByLabel('Пароль', { exact: true }).fill(password);
    await page.getByLabel('Повторите пароль', { exact: true }).fill(password);
    await page.getByRole('button', { name: 'Создать аккаунт', exact: true }).click();
    await expect(page).toHaveURL('/login');
    await expect(page.getByRole('status')).toContainText('Аккаунт создан');
    await page.getByLabel('Пароль', { exact: true }).fill(password);
    await page.getByRole('button', { name: 'Войти', exact: true }).click();
    await expect(page).toHaveURL(path);
    await expect(page.getByRole('heading', { level: 1 })).toContainText(name);
    const cookies = await context.cookies();
    const refresh = cookies.find(cookie => cookie.name === 'masterly_refresh');
    expect(refresh?.httpOnly).toBe(true);
    expect(await page.evaluate(() => localStorage.length + sessionStorage.length)).toBe(0);
    await page.reload();
    await expect(page.getByRole('heading', { level: 1 })).toContainText(name);
    await page.getByRole('link', { name: /Изменить имя/ }).click();
    await page.getByLabel('Ваше имя', { exact: true }).fill(`${name} обновлен`);
    await page.getByRole('button', { name: 'Сохранить изменения' }).click();
    await expect(page.getByRole('status')).toHaveText('Имя сохранено.');
    await page.getByRole('link', { name: /В кабинет/ }).click();
    await expect(page.getByRole('heading', { level: 1 })).toContainText('обновлен');
    await page.screenshot({ path: testInfo.outputPath(`${role.toLowerCase()}-account.png`), fullPage: true });
    await page.goto('/admin');
    await expect(page).toHaveURL(path); // Role guard sends the user to their own account.
    await page.getByRole('button', { name: 'Выйти из аккаунта' }).click();
    await expect(page).toHaveURL('/login');
    expect((await context.cookies()).some(cookie => cookie.name === 'masterly_refresh')).toBe(false);
    await page.goto(path);
    await expect(page).toHaveURL('/login');
    expect(errors).toEqual([]);
  });
}

test('auth pages remain usable on small and desktop screens', async ({ page }, testInfo) => {
  for (const width of [320, 375, 768, 1440]) {
    await page.setViewportSize({ width, height: 1000 });
    for (const route of ['login', 'register']) {
      await page.goto(`/${route}`);
      await page.evaluate(() => document.fonts.ready);
      expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false);
      if ([375, 1440].includes(width)) await page.screenshot({ path: testInfo.outputPath(`${route}-${width}.png`), fullPage: true });
    }
  }
});
