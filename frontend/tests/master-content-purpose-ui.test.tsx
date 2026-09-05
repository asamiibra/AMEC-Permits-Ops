import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CanonicalFormsLibrary } from "../src/MasterContentForms";

const bindings = [
  { id: "available-1", module: "PROPOSAL", usage_type: "AVAILABLE", active: true },
];

const form = {
  id: "form-template-1",
  ref: "F-0002",
  content_type: "FORM" as const,
  title: "Synthetic Proposal Template",
  category: { id: "business-development", label: "Business Development" },
  description: "Synthetic commissioning form.",
  used_in: ["PROPOSAL"],
  purpose_bindings: bindings,
  owner_status: "Current" as const,
  version: 1,
  version_status: "CURRENT",
};

function response(body: unknown) {
  return {
    ok: true,
    headers: { get: (name: string) => name === "content-type" ? "application/json" : null },
    text: async () => JSON.stringify(body),
  };
}

describe("Owner purpose binding UI", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn((input: string | URL, init?: RequestInit) => {
      const url = new URL(String(input), window.location.origin);
      if (url.pathname === "/api/master-content" && !url.pathname.endsWith("/module-bindings")) return Promise.resolve(response([form]));
      if (url.pathname === "/api/master-content/categories") return Promise.resolve(response([{ id: "business-development", label: "Business Development", allowed_content_types: ["FORM"] }]));
      if (url.pathname === "/api/dashboard-v2/catalogs") return Promise.resolve(response({ external_bodies: [], jurisdictions: [], service_types: [], lifecycle_phases: [] }));
      if (url.pathname === "/api/master-content/form-template-1/module-bindings") {
        if (init?.method === "PUT") return Promise.resolve(response({ ...form, purpose_bindings: [{ module: "PROPOSAL", usage_type: "AVAILABLE", active: true }, { module: "BD", usage_type: "PROPOSAL_TEMPLATE", active: true }] }));
        return Promise.resolve(response(bindings));
      }
      if (url.pathname === "/api/master-content/form-template-1") return Promise.resolve(response(form));
      return Promise.resolve(response({}));
    });
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => vi.unstubAllGlobals());

  it("lets Owner select an explicit purpose through the existing API helper and reads it back", async () => {
    render(<CanonicalFormsLibrary role="OWNER_SPONSOR" />);
    await waitFor(() => expect(screen.getByText("Synthetic Proposal Template")).toBeVisible());
    fireEvent.click(screen.getByRole("button", { name: "Modify" }));
    const purpose = await screen.findByLabelText("Canonical Business Development purpose");
    fireEvent.change(purpose, { target: { value: "PROPOSAL_TEMPLATE" } });
    fireEvent.click(screen.getByRole("button", { name: "Save Changes" }));

    await waitFor(() => expect(fetchMock.mock.calls.some(([input, init]) => String(input).includes("/module-bindings") && init?.method === "PUT")).toBe(true));
    const [, init] = fetchMock.mock.calls.find(([input, request]) => String(input).includes("/module-bindings") && request?.method === "PUT") as [string, RequestInit];
    expect(JSON.parse(String(init.body))).toEqual([
      { module: "PROPOSAL", usage_type: "AVAILABLE", active: true },
      { module: "BD", usage_type: "PROPOSAL_TEMPLATE", active: true },
    ]);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("does not expose the purpose control to Business Development users", async () => {
    render(<CanonicalFormsLibrary role="BUSINESS_DEVELOPMENT" />);
    await waitFor(() => expect(screen.getByText("Synthetic Proposal Template")).toBeVisible());
    expect(screen.queryByRole("button", { name: "Modify" })).not.toBeInTheDocument();
  });
});
