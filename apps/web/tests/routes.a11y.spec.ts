import AxeBuilder from "@axe-core/playwright";
import { test, expect } from "./support/app-test";
import { productRoutes } from "./support/routes";

test.describe("WCAG smoke", () => {
  for (const route of productRoutes) {
    test(`${route.path} не имеет critical/serious нарушений axe`, async ({ page }) => {
      await page.goto(route.path, { waitUntil: "networkidle" });

      const report = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
        .analyze();
      const blocking = report.violations.filter(
        (violation) =>
          violation.impact === "critical" || violation.impact === "serious",
      );

      expect(blocking).toEqual([]);
    });
  }
});
