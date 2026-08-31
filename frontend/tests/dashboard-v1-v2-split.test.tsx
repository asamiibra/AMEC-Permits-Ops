import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CurrentDashboard } from "../src/Dashboard";

const form = {
  id: "shared-form-1",
  ref: "F-0001",
  content_type: "FORM",
  title: "Shared synthetic form",
  category: { id: "general", label: "General" },
  description: "One canonical record shown by the current Dashboard.",
  used_in: ["BD"],
  owner_status: "Current",
  version: 1,
  version_status: "CURRENT",
};

beforeEach(() => {
  const fetchMock = vi.fn((input: string | URL) => {
    const path = new URL(String(input), window.location.origin).pathname;
    const body = path === "/api/master-content"
      ? [form]
      : path === "/api/master-content/shared-form-1"
        ? form
      : path === "/api/definitions"
        ? []
        : path === "/api/master-content/categories"
          ? []
          : path === "/api/dashboard-v2/catalogs"
            ? { external_bodies: [], jurisdictions: [], service_types: [], lifecycle_phases: [] }
            : {};
    return Promise.resolve({ ok: true, headers: { get: (name: string) => name === "content-type" ? "application/json" : null }, text: async () => JSON.stringify(body) });
  });
  vi.stubGlobal("fetch", fetchMock);
});

describe("Owner content library surface", () => {
  it("mounts one simple Dashboard surface with four libraries", async () => {
    render(<CurrentDashboard role="SYSTEM_ADMIN" />);
    expect(screen.getByTestId("current-dashboard")).toHaveAttribute("data-dashboard-root", "content-library");
    expect(screen.getByTestId("dashboard-library-navigation")).toBeVisible();
    await waitFor(() => expect(screen.getByRole("heading", { name: "Dashboard", level: 2 })).toBeVisible());
    await waitFor(() => expect(screen.getByText("Shared synthetic form")).toBeVisible());
    for (const name of ["Forms", "Reports", "Engineering Works", "Definitions"]) {
      expect(screen.getByRole("heading", { name })).toBeVisible();
    }
    for (const forbidden of ["GOVERNANCE OVERVIEW", "Canonical control plane", "Advanced governance filters", "Content ownership", "SOURCE / VERSION", "Governed discovery", "Purpose bindings"]) {
      expect(screen.queryByText(forbidden, { exact: false })).not.toBeInTheDocument();
    }
    expect(screen.getByRole("link", { name: "Inputs & Go-Live" })).toHaveAttribute("href", "/dashboard/inputs-go-live");
    expect(screen.getByRole("cell", { name: "Current" })).toBeVisible();
    expect(screen.getByRole("cell", { name: "Business Development" })).toBeVisible();
  });

  it("keeps Dashboard search on canonical reads and opens a simple Form detail", async () => {
    render(<CurrentDashboard role="SYSTEM_ADMIN" />);
    await waitFor(() => expect(screen.getByText("Shared synthetic form")).toBeVisible());
    const search = screen.getByLabelText("Search master content");
    fireEvent.change(search, { target: { value: "Shared" } });
    await waitFor(() => expect(screen.getAllByText("Shared synthetic form").length).toBeGreaterThan(0));
    const requests = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls.map(([input]) => String(input));
    expect(requests.some((input) => input.includes("/api/retrieval/query"))).toBe(false);
    expect(requests.some((input) => input.includes("/api/governed-prefill/preview"))).toBe(false);
    fireEvent.click(screen.getByRole("button", { name: "Open" }));
    await waitFor(() => expect(screen.getByRole("heading", { name: /F-0001 · Shared synthetic form/ })).toBeVisible());
    expect(screen.getByText("Current source file")).toBeVisible();
    expect(screen.getByText("Version History")).toBeVisible();
    expect(screen.getByRole("link", { name: "Download current source" })).toBeVisible();
    expect(screen.queryByText("Source & Authority", { exact: false })).not.toBeInTheDocument();
    expect(screen.queryByText("Form automation governance", { exact: false })).not.toBeInTheDocument();
  });

  it("renders one canonical item through one active Dashboard surface", async () => {
    render(<CurrentDashboard role="SYSTEM_ADMIN" />);
    await waitFor(() => expect(screen.getByText("Shared synthetic form")).toBeVisible());
    expect(screen.getAllByText("F-0001", { exact: true })).toHaveLength(1);
  });
});
