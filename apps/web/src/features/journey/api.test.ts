import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { completionFixture, employeeFixture, journeyFixture } from "@/test/fixtures";
import { server } from "@/test/server";
import {
  completeActivity,
  fetchEmployeeJourney,
  fetchEmployees,
} from "./api";

describe("journey API adapter", () => {
  it("loads the deterministic employee list", async () => {
    await expect(fetchEmployees()).resolves.toEqual([employeeFixture]);
  });

  it("loads a journey without a real backend", async () => {
    await expect(fetchEmployeeJourney(employeeFixture.employee_id)).resolves.toEqual(
      journeyFixture,
    );
  });

  it("sends completion as an idempotent POST", async () => {
    let receivedKey: string | null = null;

    server.use(
      http.post(
        "http://localhost:8000/api/v1/employees/:employeeId/activities/:eventId/complete",
        ({ request }) => {
          receivedKey = request.headers.get("Idempotency-Key");
          return HttpResponse.json(completionFixture);
        },
      ),
    );

    await expect(
      completeActivity(employeeFixture.employee_id, "quest-strategy", "attempt-1"),
    ).resolves.toEqual(completionFixture);
    expect(receivedKey).toBe("attempt-1");
  });

  it("surfaces the API detail message", async () => {
    server.use(
      http.get("http://localhost:8000/api/v1/employees", () =>
        HttpResponse.json({ detail: "Данные временно недоступны" }, { status: 503 }),
      ),
    );

    await expect(fetchEmployees()).rejects.toThrow("Данные временно недоступны");
  });

  it("falls back to the HTTP status when an error body is not JSON", async () => {
    server.use(
      http.get(
        "http://localhost:8000/api/v1/employees",
        () => new HttpResponse("upstream unavailable", { status: 502 }),
      ),
    );

    await expect(fetchEmployees()).rejects.toThrow("API вернул статус 502");
  });
});
