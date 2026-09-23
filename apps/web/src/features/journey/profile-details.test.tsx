import { render, screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { I18nProvider } from "@/lib/i18n";
import { server } from "@/test/server";
import { journeyFixture } from "@/test/fixtures";
import { EmployeeJourneyScreen } from "./employee-journey-screen";

vi.mock("@/lib/auth", () => ({
  AUTH_CHANGE_EVENT: "career-quest-auth-change",
  getAuthHeaders: () => ({ Accept: "application/json" }),
  fetchAuthIdentity: async () => ({ role: "employee", employee_id: "employee-demo" }),
}));

function show(data: unknown) {
  server.use(
    http.post("http://localhost:8000/api/v1/employees/:employeeId/recommendations", () =>
      HttpResponse.json(data as never),
    ),
  );
  render(
    <I18nProvider>
      <EmployeeJourneyScreen />
    </I18nProvider>,
  );
}

describe("complete employee profile", () => {
  it("shows actual tenure and hire date alongside role and grade", async () => {
    show({
      ...journeyFixture,
      employee: { ...journeyFixture.employee, tenure_months: 5, hire_date: "2026-05-01" },
    });
    expect(await screen.findByText("Стаж: 5 мес.")).toBeVisible();
    expect(screen.getByText("Дата приёма: 2026-05-01")).toBeVisible();
    expect(screen.getByRole("heading", { name: "Product Analyst" })).toBeVisible();
    expect(screen.getByText("Middle · Цифровые продукты")).toBeVisible();
  });

  it("distinguishes all recorded statuses without hiding non-completed history", async () => {
    const statuses = ["completed", "in_progress", "dropped", "no_show", "declined", "overdue"] as const;
    show({
      ...journeyFixture,
      activity_history: statuses.map((status, index) => ({
        ...journeyFixture.activity_history[0],
        record_id: String(index),
        status,
        title: `Activity ${status}`,
        activity_date: `2026-08-${14 + index}`,
      })),
    });
    const history = await screen.findByTestId("participation-history");
    for (const label of ["Завершено", "В процессе", "Прервано", "Пропуск", "Отказ", "Просрочено"]) {
      expect(within(history).getByText(label, { exact: true })).toBeVisible();
    }
    expect(within(history).getAllByRole("article")).toHaveLength(6);
    expect(within(history).getByText("customer-discovery · 2026-08-19")).toBeVisible();
  });

  it("renders every applicable skill gap", async () => {
    show({
      ...journeyFixture,
      skill_gaps: Array.from({ length: 9 }, (_, index) => ({
        ...journeyFixture.skill_gaps[0],
        skill_id: `gap-${index}`,
        name: `Required skill ${index + 1}`,
      })),
    });
    expect(await screen.findByRole("heading", { name: "Required skill 9" })).toBeVisible();
    expect(screen.getAllByRole("heading", { name: /Required skill/ })).toHaveLength(9);
  });

  it("does not invent tenure when source fields are absent", async () => {
    show({
      ...journeyFixture,
      employee: { ...journeyFixture.employee, tenure_months: null, hire_date: null },
    });
    expect(await screen.findByText("Стаж: —")).toBeVisible();
    expect(screen.queryByText(/Дата приёма:/)).not.toBeInTheDocument();
  });
});
