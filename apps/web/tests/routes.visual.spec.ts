import { test, expect } from "./support/app-test";
import { productRoutes } from "./support/routes";

test.describe("desktop visual regression 1672x941", () => {
  for (const route of productRoutes) {
    test(`${route.name} matches approved baseline`, async ({ page }) => {
      await page.goto(route.path, { waitUntil: "networkidle" });
      await page.addStyleTag({
        content: `
          *, *::before, *::after {
            animation-duration: 0s !important;
            animation-delay: 0s !important;
            transition-duration: 0s !important;
            caret-color: transparent !important;
          }
        `,
      });
      await page.evaluate(() => document.fonts.ready);

      await expect(page).toHaveScreenshot(`${route.name}.png`, {
        fullPage: false,
      });
    });
  }
});
