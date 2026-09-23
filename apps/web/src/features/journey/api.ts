import type { CompletionResult, EmployeeJourney, EmployeeListItem } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function demoHeaders(role: "employee" | "hr", employeeId?: string): HeadersInit {
  return {
    Accept: "application/json",
    "X-Demo-Role": role,
    ...(employeeId ? { "X-Employee-Id": employeeId } : {}),
  };
}

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(body?.detail ?? `API вернул статус ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function fetchEmployees(signal?: AbortSignal): Promise<EmployeeListItem[]> {
  const response = await fetch(`${API_URL}/api/v1/employees?limit=200`, {
    signal,
    headers: demoHeaders("hr"),
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
    headers: demoHeaders("employee", employeeId),
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
        ...demoHeaders("employee", employeeId),
        "Idempotency-Key": idempotencyKey,
      },
    },
  );
  return readJson<CompletionResult>(response);
}
