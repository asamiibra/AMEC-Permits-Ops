const API = import.meta.env.VITE_API_URL || "";
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, { ...init, headers: { "Content-Type": "application/json", "X-Dev-Role": "SYSTEM_ADMIN", ...(init?.headers || {}) } });
  if (!response.ok) throw new Error((await response.json()).detail || "Request failed");
  return response.json();
}
