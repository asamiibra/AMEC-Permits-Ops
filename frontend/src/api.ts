import {
  browserAuthMode,
  getApiAccessToken,
} from "./auth";

// Development uses the Vite same-origin proxy so a browser opened on any local
// port cannot fail the API preflight just because the backend allow-list names
// a different frontend origin. Non-DEV builds use the explicitly configured API.
const API = (
  import.meta.env.DEV
    ? ""
    : import.meta.env.VITE_API_URL || ""
).replace(/\/+$/, "");

export class ApiError extends Error {
  readonly status: number;
  readonly path: string;

  constructor(message: string, status: number, path: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.path = path;
  }
}

export async function api<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const endpoint = `${API}${path}`;
  const isFormData =
    typeof FormData !== "undefined"
    && init?.body instanceof FormData;

  // Production bundles must never submit synthetic governance evidence. The
  // backend remains the authority, but this client guard prevents accidental
  // fixture payloads from being emitted by any production UI surface.
  if (import.meta.env.PROD && !isFormData && typeof init?.body === "string") {
    const body = init.body.toUpperCase();
    if (["AMEC-SYN", "SYNTHETIC://", "SYN-CAPABILITY", "SYN-POLICY", "X-DEV-ROLE"].some((marker) => body.includes(marker))) {
      throw new Error("SYNTHETIC_GOVERNANCE_EVIDENCE_FORBIDDEN_IN_PRODUCTION");
    }
  }

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
      throw new ApiError(
        `API returned ${response.status} `
        + `${contentType || "unknown content type"} `
        + `for ${path}`,
        response.status,
        path,
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

    throw new ApiError(
      `${detail} [${response.status} ${path}]`
      + (
        contentType
          ? ` (${contentType})`
          : ""
      ),
      response.status,
      path,
    );
  }

  if (
    !contentType
      .toLowerCase()
      .includes(
        "application/json",
      )
  ) {
    throw new ApiError(
      `API returned ${response.status} `
      + `${contentType || "unknown content type"} `
      + `for ${path}`,
      response.status,
      path,
    );
  }

  try {
    return JSON.parse(
      body,
    ) as T;
  } catch {
    throw new ApiError(
      `API returned invalid JSON for ${path} `
      + `[${response.status}]`,
      response.status,
      path,
    );
  }
}
