import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DashboardPage } from "../src/Dashboard";

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
  vi.stubGlobal("fetch", vi.fn((input: string | URL) => {
    const path = new URL(String(input), window.location.origin).pathname;
    const body = path === "/api/master-content"
      ? [form]
      : path === "/api/definitions"
        ? []
        : path === "/api/master-content/categories"
          ? []
          : path === "/api/dashboard-v2/catalogs"
            ? { external_bodies: [], jurisdictions: [], service_types: [], lifecycle_phases: [] }
            : {};
    return Promise.resolve({ ok: true, headers: { get: (name: string) => name === "content-type" ? "application/json" : null }, text: async () => JSON.stringify(body) });
  }));
});

describe("single current Dashboard", () => {
  it("shows the promoted governance-capable Dashboard with canonical forms", async () => {
    render(<DashboardPage role="SYSTEM_ADMIN" />);
    await waitFor(() => expect(screen.getByRole("heading", { name: "Dashboard", level: 2 })).toBeVisible());
    await waitFor(() => expect(screen.getByText("Shared synthetic form")).toBeVisible());
    expect(screen.getByText("Advanced governance filters")).toBeVisible();
    screen.getByText("Advanced governance filters").click();
    expect(screen.getByText("Content ownership")).toBeVisible();
    expect(screen.getByRole("link", { name: "Inputs & Go-Live" })).toHaveAttribute("href", "/dashboard/inputs-go-live");
    expect(screen.getByRole("cell", { name: "Current" })).toBeVisible();
    expect(screen.getByRole("cell", { name: "Business Development" })).toBeVisible();
  });

  it("renders one canonical item through one active Dashboard surface", async () => {
    render(<DashboardPage role="SYSTEM_ADMIN" />);
    await waitFor(() => expect(screen.getByText("Shared synthetic form")).toBeVisible());
    expect(screen.getAllByText("F-0001", { exact: true })).toHaveLength(1);
  });
});
