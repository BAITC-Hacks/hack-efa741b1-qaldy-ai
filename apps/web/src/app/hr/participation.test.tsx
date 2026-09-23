import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { I18nProvider } from "@/lib/i18n";
import { server } from "@/test/server";
import HrPage from "./page";

vi.mock("@/lib/auth", () => ({
  AUTH_CHANGE_EVENT: "career-quest-auth-change",
  getAuthHeaders: () => ({ Accept: "application/json" }),
  fetchAuthIdentity: async () => ({ role: "hr", employee_id: null }),
}));

const participationResponse = {
  dataset_version: "test-1",
  as_of_date: "2026-10-01",
  filters: { department: null, role: null, grade: null },
  employee_count: 4,
  items: [],
  total_records: 5,
  participating_employees: 4,
  statuses: { completed: 3, no_show: 1, declined: 1 },
  by_type: [{ key: "workshop", total: 5 }],
  by_event: [
    { key: "QA_EVENT_1", title: "Design Workshop", total: 5, completed: 3, completion_rate: 0.6, statuses: { completed: 3, no_show: 1, declined: 1 } },
  ],
};

async function openParticipation(payload: unknown = participationResponse) {
  server.use(
    http.get("http://localhost:8000/api/v1/hr/skill-gaps", () =>
      HttpResponse.json({ items: [{ skill_id: "QA_SKILL", name: "Design skill", total_gap: 2 }] }),
    ),
    http.get("http://localhost:8000/api/v1/hr/participation", () => HttpResponse.json(payload as never)),
  );
  const user = userEvent.setup();
  render(<I18nProvider><HrPage /></I18nProvider>);
  await screen.findByRole("cell", { name: "Design skill" });
  await user.click(screen.getByRole("tab", { name: "Участие" }));
  return user;
}

describe("HR participation API contract", () => {
  it("displays per-event participation when the shared items array is empty", async () => {
    await openParticipation();
    const title = await screen.findByRole("cell", { name: "Design Workshop" });
    const row = title.closest("tr")!;
    expect(within(row).getByRole("cell", { name: "QA_EVENT_1" })).toBeVisible();
    expect(within(row).getByRole("cell", { name: "5" })).toBeVisible();
    expect(within(row).getByRole("cell", { name: "3" })).toBeVisible();
    expect(within(row).getByRole("cell", { name: "0.6" })).toBeVisible();
    expect(within(row).getByRole("cell", { name: '{"completed":3,"no_show":1,"declined":1}' })).toBeVisible();
    expect(screen.queryByText("Данных пока нет")).not.toBeInTheDocument();
  });

  it("shows the empty state when there are no participation records", async () => {
    await openParticipation({ ...participationResponse, employee_count: 0, total_records: 0, participating_employees: 0, statuses: {}, by_type: [], by_event: [] });
    expect(await screen.findByText("Данных пока нет")).toBeVisible();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("keeps the items-based skill-gap view working after changing tabs", async () => {
    const user = await openParticipation();
    await screen.findByRole("cell", { name: "Design Workshop" });
    await user.click(screen.getByRole("tab", { name: "Дефициты навыков" }));
    expect(await screen.findByRole("cell", { name: "Design skill" })).toBeVisible();
    expect(screen.queryByRole("cell", { name: "Design Workshop" })).not.toBeInTheDocument();
  });
});
