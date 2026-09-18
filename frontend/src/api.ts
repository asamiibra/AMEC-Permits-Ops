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

/** Resolve a backend route for non-JSON consumers such as source downloads. */
export function apiUrl(path: string): string {
  return `${API}${path}`;
}

export class ApiError extends Error {
  readonly status: number;
  readonly path: string;
  readonly code?: string;
  readonly blockingReason?: string;
  readonly correlationId?: string;
  readonly technicalDetail?: unknown;

  constructor(message: string, status: number, path: string, detail: { code?: string; blockingReason?: string; correlationId?: string; technicalDetail?: unknown } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.path = path;
    Object.assign(this, detail);
  }
}

// Durable production operations can include managed-identity and verified
// Azure Blob read-back latency. Keep one shared, cancellable upper bound while
// allowing those operations to complete instead of reporting a false failure.
const API_REQUEST_TIMEOUT_MS = 45_000;
function humanErrorCode(code: string): string {
  const messages: Record<string, string> = {
    CONTRACT_FINALIZED_REVISION_IMMUTABLE: "This revision is finalized. Create a prospective revision to change its terms.",
    TIMING_FACT_REVISION_MISMATCH: "The controlling Contract revision changed. Refresh before recording this date.",
    TIMING_FACT_AUTHORITY_MISMATCH: "The timing clause or policy changed. Refresh and review the governing requirement.",
    TIMING_SOURCE_LINEAGE_INVALID: "This document does not belong to the required Contract context. Select current supporting evidence.",
    TIMING_REQUIREMENT_ALREADY_RECORDED: "This timing requirement is already recorded on the revision.",
    CONTRACT_ACCEPTANCE_REQUIRED: "Accept the governing Contract revision before recording this event.",
  };
  return messages[code] || code.toLowerCase().replaceAll("_", " ").replace(/^./, c => c.toUpperCase());
}

export function responseError(payload: unknown, status: number, path: string, correlationId?: string): ApiError {
  const envelope = payload && typeof payload === "object" ? payload as Record<string, unknown> : {};
  const detail = envelope.detail ?? envelope;
  const record = detail && typeof detail === "object" && !Array.isArray(detail) ? detail as Record<string, unknown> : {};
  const code = typeof record.code === "string" ? record.code : typeof envelope.code === "string" ? envelope.code : undefined;
  const blockingReason = typeof record.reason === "string" ? humanErrorCode(record.reason) : undefined;
  const fallback = status === 403 ? "You do not have permission to perform this action." : status === 401 ? "Sign in again to continue." : status === 404 ? "This record could not be found." : status === 422 ? "Check the required fields and try again." : status >= 500 ? "The service could not complete the request. Please try again." : "The request could not be completed.";
  const message = typeof record.message === "string" ? record.message : code ? humanErrorCode(code) : typeof detail === "string" && status < 500 ? humanErrorCode(detail) : fallback;
  return new ApiError(message, status, path, { code, blockingReason, correlationId: correlationId || (typeof envelope.correlation_id === "string" ? envelope.correlation_id : undefined), technicalDetail: detail });
}

/** Convert transport/provider failures into safe, human-facing UI copy. */
export function userFacingError(cause: unknown, fallback: string): string {
  if (cause instanceof ApiError) {
    if (cause.status === 401 || cause.status === 403) {
      return "Your current session is not authorized for this action.";
    }
    if (cause.status >= 500) {
      return "This action is temporarily unavailable. No canonical state was changed. Try again later.";
    }
    return "The request could not be completed. Review the current item and try again.";
  }
  return cause instanceof Error && cause.message ? cause.message : fallback;
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
  // backend remains authoritative, but this client guard prevents accidental
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

  const requestController = new AbortController();
  const callerSignal = init?.signal;
  const abortFromCaller = () => requestController.abort(callerSignal?.reason);
  callerSignal?.addEventListener("abort", abortFromCaller, { once: true });
  const timeoutId = setTimeout(() => requestController.abort(), API_REQUEST_TIMEOUT_MS);
  let response: Response;
  try {
    response = await fetch(
      endpoint,
      {
        ...init,
        signal: requestController.signal,
        headers: fetchHeaders,
      },
    );
  } catch (cause) {
    if (requestController.signal.aborted && !callerSignal?.aborted) {
      throw new ApiError(`API request timed out after ${API_REQUEST_TIMEOUT_MS / 1000}s for ${path}`, 0, path);
    }
    throw cause;
  } finally {
    clearTimeout(timeoutId);
    callerSignal?.removeEventListener("abort", abortFromCaller);
  }

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

    throw responseError(payload, response.status, path, response.headers.get("x-correlation-id") || undefined);
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

/** Fetch a binary API response with the same auth ownership as api(). */
export async function apiBlob(path: string, init?: RequestInit): Promise<Blob> {
  const headers = new Headers(init?.headers);
  const mode = browserAuthMode();
  if (mode === "DEV_HEADER") {
    const demoRole = typeof sessionStorage !== "undefined" ? (sessionStorage.getItem("proposalops-role") || "SYSTEM_ADMIN") : "SYSTEM_ADMIN";
    headers.delete("Authorization");
    headers.set("X-Dev-Role", demoRole);
  } else {
    const token = (await getApiAccessToken()).trim();
    if (!token) throw new Error("Authenticated API token is unavailable");
    headers.delete("X-Dev-Role");
    headers.set("Authorization", `Bearer ${token}`);
  }
  const response = await fetch(apiUrl(path), { ...init, headers });
  if (!response.ok) {
    let payload: unknown;
    try { payload = await response.json(); } catch { payload = undefined; }
    throw responseError(payload, response.status, path, response.headers.get("x-correlation-id") || undefined);
  }
  return response.blob();
}
