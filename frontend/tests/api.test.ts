import { afterEach, describe, expect, it, vi } from "vitest";
import { api, responseError, validateApiOrigin } from "../src/api";

function response(status: number, contentType: string, body: string) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: { get: (name: string) => name.toLowerCase() === "content-type" ? contentType : null },
    text: async () => body,
  };
}

afterEach(() => vi.unstubAllGlobals());

describe("API client", () => {
  it("requires a canonical HTTPS origin outside development", () => {
    expect(() => validateApiOrigin(undefined)).toThrow("VITE_API_URL");
    expect(() => validateApiOrigin("http://api.example.com")).toThrow("HTTPS");
    expect(() => validateApiOrigin("https://api.example.com/v1")).toThrow("origin");
    expect(() => validateApiOrigin("https://user:pass@api.example.com")).toThrow("credentials");
    expect(validateApiOrigin("https://www.amecidsystem.com/")).toBe("https://www.amecidsystem.com");
  });

  it("uses the same-origin /api path and parses JSON responses", async () => {
    const fetchMock = vi.fn().mockResolvedValue(response(200, "application/json", '{"status":"ok"}'));
    vi.stubGlobal("fetch", fetchMock);

    await expect(api<{ status: string }>("/api/dashboard")).resolves.toEqual({ status: "ok" });
    expect(fetchMock).toHaveBeenCalledWith("/api/dashboard", expect.objectContaining({
      headers: expect.objectContaining({ "Content-Type": "application/json", "X-Dev-Role": "SYSTEM_ADMIN" }),
    }));
  });

  it("surfaces a JSON FastAPI error with its status and endpoint", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(500, "application/json", '{"detail":"Database not initialized"}')));

    await expect(api("/api/dashboard")).rejects.toMatchObject({ message: "The service could not complete the request. Please try again.", status: 500, path: "/api/dashboard", technicalDetail: "Database not initialized" });
  });

  it("preserves structured blocker and support context without rendering an object", () => {
    const error = responseError({ detail: { code: "TIMING_FACT_REVISION_MISMATCH", reason: "STALE_REVISION" } }, 409, "/api/admin/contracts/c/timing-facts/CONTRACT_DURATION_START", "support-1");
    expect(error.message).toContain("controlling Contract revision changed");
    expect(error).toMatchObject({ code: "TIMING_FACT_REVISION_MISMATCH", blockingReason: "Stale revision", correlationId: "support-1", status: 409 });
    expect(error.message).not.toContain("[object Object]");
  });

  it("does not report a non-JSON Vercel response as a JSON parse error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(404, "text/plain; charset=utf-8", "The page could not be found")));

    await expect(api("/api/dashboard")).rejects.toThrow("API returned 404 text/plain; charset=utf-8 for /api/dashboard");
    await expect(api("/api/dashboard")).rejects.not.toThrow("Unexpected token");
  });
});
