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

describe("Content Library workspace", () => {
  it("mounts the unified library shell with canonical Forms", async () => {
    render(<CurrentDashboard role="SYSTEM_ADMIN" />);
    expect(screen.getByTestId("current-dashboard")).toHaveAttribute("data-dashboard-root", "content-library");
    expect(screen.getByTestId("dashboard-library-navigation")).toBeVisible();
    await waitFor(() => expect(screen.getByRole("heading", { name: "Content Library", level: 2 })).toBeVisible());
    await waitFor(() => expect(screen.getByText("Shared synthetic form")).toBeVisible());
    expect(screen.getByLabelText("Search content library")).toBeVisible();
    expect(screen.getByLabelText("Filter by status")).toBeVisible();
    expect(screen.queryByRole("link", { name: "Inputs & Go-Live" })).not.toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Current" })).toBeVisible();
    expect(screen.getByRole("cell", { name: "Business Development" })).toBeVisible();
    expect(screen.queryByText("AI Assist")).toBeNull();
  });

  it("renders one canonical item through one active Dashboard surface", async () => {
    render(<CurrentDashboard role="SYSTEM_ADMIN" />);
    await waitFor(() => expect(screen.getByText("Shared synthetic form")).toBeVisible());
    expect(screen.getAllByText("F-0001", { exact: true })).toHaveLength(1);
  });

  it("changes libraries without stacking four long sections", async () => {
    render(<CurrentDashboard role="SYSTEM_ADMIN" />);
    await waitFor(() => expect(screen.getByText("Shared synthetic form")).toBeVisible());
    screen.getByRole("button", { name: /Reports/ }).click();
    await waitFor(() => expect(screen.getByRole("heading", { name: "Reports" })).toBeVisible());
    expect(screen.queryByRole("heading", { name: "Definitions" })).not.toBeInTheDocument();
  });
});
