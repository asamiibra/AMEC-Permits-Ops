import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "../src/api";

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

    await expect(api("/api/dashboard")).rejects.toThrow("Database not initialized [500 /api/dashboard]");
  });

  it("does not report a non-JSON Vercel response as a JSON parse error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(404, "text/plain; charset=utf-8", "The page could not be found")));

    await expect(api("/api/dashboard")).rejects.toThrow("API returned 404 text/plain; charset=utf-8 for /api/dashboard");
    await expect(api("/api/dashboard")).rejects.not.toThrow("Unexpected token");
  });
});
