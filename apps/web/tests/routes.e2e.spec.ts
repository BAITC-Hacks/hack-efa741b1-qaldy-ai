import { test, expect } from "./support/app-test";
import { productRoutes } from "./support/routes";

test.describe("маршруты Career Quest", () => {
  for (const route of productRoutes) {
    test(`${route.path} открывается без browser errors`, async ({ page }) => {
      const errors: string[] = [];
      page.on("pageerror", (error) => errors.push(error.message));
      page.on("console", (message) => {
        if (message.type() === "error") errors.push(message.text());
      });

      const response = await page.goto(route.path, { waitUntil: "networkidle" });

      expect(response?.ok(), `${route.path} должен вернуть 2xx`).toBe(true);
      await expect(page.locator("main").first()).toBeVisible();
      await expect(page.locator("body")).not.toContainText("Application error");
      expect(errors, `Ошибки в console на ${route.path}`).toEqual([]);
    });
  }

  test("deep link, active navigation, reload и browser history согласованы", async ({
    page,
  }) => {
    await page.goto("/journey");

    const activeLink = page.locator('a[aria-current="page"]');
    await expect(activeLink).toHaveAttribute("href", "/journey");
    await page.reload();
    await expect(activeLink).toHaveAttribute("href", "/journey");

    await page.locator('a[href="/hr"]').first().click();
    await expect(page).toHaveURL(/\/hr$/);
    await expect(activeLink).toHaveAttribute("href", "/hr");

    await page.goBack();
    await expect(page).toHaveURL(/\/journey$/);
    await expect(activeLink).toHaveAttribute("href", "/journey");

    await page.goForward();
    await expect(page).toHaveURL(/\/hr$/);
  });

  test("ключевые страницы не создают горизонтальный overflow на mobile", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 390, height: 844 });

    for (const path of ["/journey", "/hr", "/import"]) {
      await page.goto(path);
      const sizes = await page.evaluate(() => ({
        viewport: document.documentElement.clientWidth,
        content: document.documentElement.scrollWidth,
      }));
      expect(sizes.content, `overflow на ${path}`).toBeLessThanOrEqual(sizes.viewport + 1);
    }
  });
});
