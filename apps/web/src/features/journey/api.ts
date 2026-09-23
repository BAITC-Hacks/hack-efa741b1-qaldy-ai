import type { EmployeeJourney } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function fetchEmployeeJourney(signal?: AbortSignal): Promise<EmployeeJourney> {
  const response = await fetch(`${API_URL}/api/v1/demo/employee-journey`, {
    signal,
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    throw new Error(`API вернул статус ${response.status}`);
  }

  return response.json() as Promise<EmployeeJourney>;
}
