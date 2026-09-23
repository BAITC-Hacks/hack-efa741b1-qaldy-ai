export type AuthIdentity = { role: "hr" | "employee"; employee_id: string | null };

export const AUTH_CHANGE_EVENT = "career-quest-auth-change";
const TOKEN_KEY = "career-quest-demo-token";
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(TOKEN_KEY);
}

export function setAuthToken(token: string): void {
  window.sessionStorage.setItem(TOKEN_KEY, token.trim());
  window.dispatchEvent(new Event(AUTH_CHANGE_EVENT));
}

export function clearAuthToken(): void {
  window.sessionStorage.removeItem(TOKEN_KEY);
  window.dispatchEvent(new Event(AUTH_CHANGE_EVENT));
}

export function getAuthHeaders(): Record<string, string> {
  const token = getAuthToken();
  return { Accept: "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) };
}

export async function verifyAuthToken(token: string, signal?: AbortSignal): Promise<AuthIdentity> {
  const response = await fetch(`${API_URL}/api/v1/auth/me`, {
    signal,
    headers: { Accept: "application/json", Authorization: `Bearer ${token.trim()}` },
  });
  if (!response.ok) throw new Error("Токен недействителен или API недоступен");
  return response.json() as Promise<AuthIdentity>;
}

export async function fetchAuthIdentity(signal?: AbortSignal): Promise<AuthIdentity> {
  const token = getAuthToken();
  if (!token) throw new Error("Введите демо-токен через меню профиля");
  return verifyAuthToken(token, signal);
}
