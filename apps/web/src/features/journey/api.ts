import type { CompletionResult, EmployeeJourney, EmployeeListItem } from "./types";
import { getAuthHeaders } from "@/lib/auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(body?.detail ?? `API вернул статус ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function fetchEmployees(signal?: AbortSignal): Promise<EmployeeListItem[]> {
  const response = await fetch(`${API_URL}/api/v1/employees?limit=1000`, {
    signal,
    headers: getAuthHeaders(),
  });
  return readJson<EmployeeListItem[]>(response);
}

export async function fetchEmployeeJourney(
  employeeId: string,
  signal?: AbortSignal,
): Promise<EmployeeJourney> {
  const response = await fetch(`${API_URL}/api/v1/employees/${employeeId}/recommendations`, {
    method: "POST",
    signal,
    headers: getAuthHeaders(),
  });
  return readJson<EmployeeJourney>(response);
}

export async function completeActivity(
  employeeId: string,
  eventId: string,
  idempotencyKey: string,
): Promise<CompletionResult> {
  const response = await fetch(
    `${API_URL}/api/v1/employees/${employeeId}/activities/${eventId}/complete`,
    {
      method: "POST",
      headers: {
        ...getAuthHeaders(),
        "Idempotency-Key": idempotencyKey,
      },
    },
  );
  return readJson<CompletionResult>(response);
}
