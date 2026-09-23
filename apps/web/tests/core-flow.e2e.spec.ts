import { expect, test, type Page } from "@playwright/test";
import { completionFixture, employeeFixture, journeyFixture } from "../src/test/fixtures";

async function useDemoIdentity(page: Page, role: "employee" | "hr") {
  await page.addInitScript(() => {
    window.sessionStorage.setItem("career-quest-demo-token", "playwright-demo-token");
  });
  await page.route("**/api/v1/auth/me", (route) => route.fulfill({
    json: { role, employee_id: role === "employee" ? employeeFixture.employee_id : null },
  }));
}

test("employee opens recommendations, completes a step and sees recalculated progress", async ({ page }) => {
  await useDemoIdentity(page, "employee");
  await page.route("**/api/v1/employees?**", (route) => route.fulfill({ json: [employeeFixture] }));
  await page.route("**/api/v1/employees/*/recommendations", (route) => route.fulfill({ json: journeyFixture }));
  await page.route("**/api/v1/employees/*/activities/*/complete", (route) => route.fulfill({ json: completionFixture }));

  await page.goto("/journey");
  await expect(page.getByRole("heading", { name: /Марат/ })).toBeVisible();
  await expect(page.getByTestId("current-skills").getByText("SQL", { exact: true })).toBeVisible();
  await expect(page.getByTestId("completed-activities").getByText("Customer Discovery Lab")).toBeVisible();
  await expect(page.getByText("Сформировать стратегию продукта")).toBeVisible();
  await expect(page.getByText("72%", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Завершить" }).click();
  await expect(page.getByText("Прогресс обновлён")).toBeVisible();
  await expect(page.getByText("80%", { exact: true })).toBeVisible();
});

test("static journey interface switches between ru, kk and en", async ({ page }) => {
  await useDemoIdentity(page, "employee");
  await page.route("**/api/v1/employees?**", (route) => route.fulfill({ json: [employeeFixture] }));
  await page.route("**/api/v1/employees/*/recommendations", (route) => route.fulfill({ json: journeyFixture }));
  await page.goto("/journey");

  const language = page.getByLabel("Язык");
  await language.selectOption("en");
  await expect(page.getByRole("heading", { name: /Hello, Марат/ })).toBeVisible();
  await expect(page.getByRole("button", { name: "Complete" })).toBeVisible();
  await page.getByLabel("Language").selectOption("kk");
  await expect(page.getByRole("heading", { name: /Қайырлы күн, Марат/ })).toBeVisible();
});

test("HR dashboard loads API metrics and changes module", async ({ page }) => {
  await useDemoIdentity(page, "hr");
  await page.route("**/api/v1/employees?**", (route) => route.fulfill({ json: [employeeFixture] }));
  await page.route("**/api/v1/employees/*/recommendations", (route) => route.fulfill({ json: journeyFixture }));
  await page.route("**/api/v1/hr/**", async (route) => {
    const id = new URL(route.request().url()).pathname.split("/").at(-1);
    await route.fulfill({ json: { items: [{ metric: id, employees_count: 12, critical_count: 3 }] } });
  });
  await page.goto("/hr");
  await expect(page.getByTestId("hr-dashboard")).toBeVisible();
  await expect(page.getByRole("cell", { name: "12" })).toBeVisible();
  await page.getByRole("tab", { name: "Участие" }).click();
  await expect(page.getByRole("cell", { name: "participation" })).toBeVisible();
  await page.goto("/journey");
  await expect(page.getByText("Сформировать стратегию продукта")).toBeVisible();
  await expect(page.getByRole("button", { name: "Завершить" })).toHaveCount(0);
});

test("import performs validate then apply", async ({ page }) => {
  await useDemoIdentity(page, "hr");
  await page.route("**/api/v1/import/validate", (route) => route.fulfill({ json: { valid: true, validation_token: "dry-1", package_hash: "a".repeat(64), rows: 1 } }));
  await page.route("**/api/v1/import/apply", (route) => route.fulfill({ json: { applied: true, imported: 1 } }));
  await page.goto("/import");
  await page.getByTestId("import-file").setInputFiles({ name: "profiles.json", mimeType: "application/json", buffer: Buffer.from('{"items":[]}') });
  await page.getByRole("button", { name: "Проверить" }).click();
  await expect(page.getByRole("heading", { name: "Dry-run завершён" })).toBeVisible();
  await page.getByRole("button", { name: "Применить" }).click();
  await expect(page.getByRole("heading", { name: "Импорт применён" })).toBeVisible();
});
