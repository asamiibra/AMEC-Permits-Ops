const API = (import.meta.env.VITE_API_URL || "").replace(/\/+$/, "");

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const endpoint = `${API}${path}`;
  const response = await fetch(endpoint, { ...init, headers: { "Content-Type": "application/json", "X-Dev-Role": "SYSTEM_ADMIN", ...(init?.headers || {}) } });
  const contentType = response.headers.get("content-type") || "";
  const body = await response.text();
  let payload: unknown;

  if (body && contentType.toLowerCase().includes("application/json")) {
    try {
      payload = JSON.parse(body);
    } catch {
      payload = undefined;
    }
  }

  if (!response.ok) {
    if (!contentType.toLowerCase().includes("application/json")) {
      throw new Error(`API returned ${response.status} ${contentType || "unknown content type"} for ${path}`);
    }
    const detail = payload && typeof payload === "object" && "detail" in payload ? String(payload.detail) : "Request failed";
    throw new Error(`${detail} [${response.status} ${path}]${contentType ? ` (${contentType})` : ""}`);
  }

  if (!contentType.toLowerCase().includes("application/json")) {
    throw new Error(`API returned ${response.status} ${contentType || "unknown content type"} for ${path}`);
  }

  try {
    return JSON.parse(body) as T;
  } catch {
    throw new Error(`API returned invalid JSON for ${path} [${response.status}]`);
  }
}
