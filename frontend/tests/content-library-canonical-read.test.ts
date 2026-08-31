import { afterEach, describe, expect, it, vi } from "vitest";
import { readCanonicalForms } from "../src/contentLibraryApi";

afterEach(() => vi.unstubAllGlobals());

describe("canonical Content Library data access", () => {
  it("composes base and governance filters through one canonical endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      headers: { get: () => "application/json" },
      text: async () => "[]",
    });
    vi.stubGlobal("fetch", fetchMock);

    await readCanonicalForms({
      q: "authority",
      category_label: "Permit",
      owner_status: "Needs Review",
      module: "BD",
      wave_a_readiness: "MANUAL_USE_READY",
      automation_readiness: "AUTOMATED_USE_READY",
      external_body_id: "body-1",
      service_type_id: "service-1",
      applicability_status: "ACTIVE",
    });

    const endpoint = String(fetchMock.mock.calls[0][0]);
    expect(endpoint).toContain("/api/master-content?");
    expect(endpoint).toContain("content_type=FORM");
    expect(endpoint).toContain("owner_status=Needs+Review");
    expect(endpoint).toContain("wave_a_readiness=MANUAL_USE_READY");
    expect(endpoint).toContain("automation_readiness=AUTOMATED_USE_READY");
    expect(endpoint).toContain("external_body_id=body-1");
    expect(endpoint).not.toContain("dashboard-v2/forms");
  });
});
