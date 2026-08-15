import { render, screen, waitFor } from "@testing-library/react";
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

describe("current Dashboard V2 root identity", () => {
  it("mounts the evolved V2 root with canonical forms", async () => {
    render(<CurrentDashboard role="SYSTEM_ADMIN" />);
    expect(screen.getByTestId("current-dashboard")).toHaveAttribute("data-dashboard-root", "v2-evolution");
    expect(screen.getByTestId("dashboard-governance-overview")).toBeVisible();
    expect(screen.getByTestId("dashboard-library-navigation")).toBeVisible();
    expect(screen.getByTestId("dashboard-source-authority-panel")).toBeVisible();
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
    render(<CurrentDashboard role="SYSTEM_ADMIN" />);
    await waitFor(() => expect(screen.getByText("Shared synthetic form")).toBeVisible());
    expect(screen.getAllByText("F-0001", { exact: true })).toHaveLength(1);
  });
});
