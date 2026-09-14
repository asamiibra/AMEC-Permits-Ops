import {
  browserAuthMode,
  getApiAccessToken,
} from "./auth";

// Development uses the Vite same-origin proxy. Every staged or production
// build must name the canonical API explicitly so it cannot silently route to
// a frontend host or an obsolete backend proxy.
export function validateApiOrigin(value: string | undefined): string {
  const raw = (value || "").trim();
  if (!raw) {
    throw new Error("VITE_API_URL is required outside development");
  }

  let parsed: URL;
  try {
    parsed = new URL(raw);
  } catch {
    throw new Error("VITE_API_URL must be an absolute HTTPS origin");
  }

  const hostname = parsed.hostname.toLowerCase();
  if (
    parsed.protocol !== "https:"
    || parsed.username
    || parsed.password
    || parsed.search
    || parsed.hash
    || !["", "/"].includes(parsed.pathname)
    || ["localhost", "127.0.0.1", "::1"].includes(hostname)
    || hostname.includes("*")
  ) {
    throw new Error(
      "VITE_API_URL must be an absolute HTTPS origin without credentials, query, fragment, path, wildcard, or localhost",
    );
  }

  return parsed.origin;
}

const API = import.meta.env.DEV
  ? ""
  : validateApiOrigin(import.meta.env.VITE_API_URL);

export async function api<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const endpoint = `${API}${path}`;
  const isFormData =
    typeof FormData !== "undefined"
    && init?.body instanceof FormData;

  const headers = new Headers(
    init?.headers,
  );

  if (
    !isFormData
    && !headers.has("Content-Type")
  ) {
    headers.set(
      "Content-Type",
      "application/json",
    );
  }

  const mode = browserAuthMode();

  if (mode === "DEV_HEADER") {
    const demoRole =
      typeof sessionStorage !== "undefined"
        ? (
            sessionStorage.getItem(
              "proposalops-role",
            )
            || "SYSTEM_ADMIN"
          )
        : "SYSTEM_ADMIN";

    // DEV owns its authentication header. A caller cannot smuggle a
    // bearer token through RequestInit while the backend is in DEV_HEADER.
    headers.delete(
      "Authorization",
    );
    headers.set(
      "X-Dev-Role",
      demoRole,
    );
  } else {
    const token = (
      await getApiAccessToken()
    ).trim();

    if (!token) {
      throw new Error(
        "Authenticated API token is unavailable",
      );
    }

    // ENTRA owns its authentication header. Never forward the development
    // role header and never allow caller-supplied Authorization to win.
    headers.delete(
      "X-Dev-Role",
    );
    headers.set(
      "Authorization",
      `Bearer ${token}`,
    );
  }

  const fetchHeaders: Record<string, string> = {};

  headers.forEach(
    (value, name) => {
      fetchHeaders[name] = value;
    },
  );

  for (
    const canonicalName of [
      "Content-Type",
      "Authorization",
      "X-Dev-Role",
    ]
  ) {
    const value =
      headers.get(
        canonicalName,
      );

    delete fetchHeaders[
      canonicalName.toLowerCase()
    ];

    if (value !== null) {
      fetchHeaders[canonicalName] =
        value;
    }
  }

  const response = await fetch(
    endpoint,
    {
      ...init,
      headers:
        fetchHeaders,
    },
  );

  const contentType =
    response.headers.get(
      "content-type",
    )
    || "";

  const body =
    await response.text();

  let payload: unknown;

  if (
    body
    && contentType
      .toLowerCase()
      .includes(
        "application/json",
      )
  ) {
    try {
      payload = JSON.parse(
        body,
      );
    } catch {
      payload = undefined;
    }
  }

  if (!response.ok) {
    if (
      !contentType
        .toLowerCase()
        .includes(
          "application/json",
        )
    ) {
      throw new Error(
        `API returned ${response.status} `
        + `${contentType || "unknown content type"} `
        + `for ${path}`,
      );
    }

    const detail =
      payload
      && typeof payload === "object"
      && "detail" in payload
        ? String(
            payload.detail,
          )
        : "Request failed";

    throw new Error(
      `${detail} [${response.status} ${path}]`
      + (
        contentType
          ? ` (${contentType})`
          : ""
      ),
    );
  }

  if (
    !contentType
      .toLowerCase()
      .includes(
        "application/json",
      )
  ) {
    throw new Error(
      `API returned ${response.status} `
      + `${contentType || "unknown content type"} `
      + `for ${path}`,
    );
  }

  try {
    return JSON.parse(
      body,
    ) as T;
  } catch {
    throw new Error(
      `API returned invalid JSON for ${path} `
      + `[${response.status}]`,
    );
  }
}
