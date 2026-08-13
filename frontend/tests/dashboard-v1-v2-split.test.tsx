import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DashboardPage } from "../src/Dashboard";

const form = {
  id: "shared-form-1",
  ref: "F-0001",
  content_type: "FORM",
  title: "Shared synthetic form",
  category: { id: "general", label: "General" },
  description: "One canonical record shown by both dashboard surfaces.",
  used_in: ["BD"],
  version: 1,
  version_status: "CURRENT",
};

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn((input: string | URL) => {
    const path = new URL(String(input), window.location.origin).pathname;
    const body = path === "/api/master-content" ? [form] : path === "/api/definitions" ? [] : path === "/api/master-content/categories" ? [] : {};
    return Promise.resolve({ ok: true, headers: { get: (name: string) => name === "content-type" ? "application/json" : null }, text: async () => JSON.stringify(body) });
  }));
});

describe("parallel Dashboard V1/V2 presentation", () => {
  it("keeps governance controls out of the legacy Dashboard", async () => {
    render(<DashboardPage role="SYSTEM_ADMIN" />);
    await waitFor(() => expect(screen.getByRole("heading", { name: "Dashboard", level: 2 })).toBeVisible());
    await waitFor(() => expect(screen.getByText("Shared synthetic form")).toBeVisible());
    expect(screen.queryByText("Advanced governance filters")).toBeNull();
    expect(screen.queryByText("Content ownership")).toBeNull();
    expect(screen.getByText("Version 1")).toBeVisible();
  });

  it("exposes Wave A governance only in Dashboard V2", async () => {
    render(<DashboardPage role="SYSTEM_ADMIN" governanceMode />);
    await waitFor(() => expect(screen.getByRole("heading", { name: "Dashboard V2", level: 2 })).toBeVisible());
    expect(screen.getByText("Advanced governance filters")).toBeVisible();
    expect(screen.getByText("Content ownership")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Inputs & Go-Live" })).toHaveAttribute("href", "/dashboard-v2/inputs-go-live");
  });

  it("renders one canonical item through both presentation modes", async () => {
    render(<><DashboardPage role="SYSTEM_ADMIN" /><DashboardPage role="SYSTEM_ADMIN" governanceMode /></>);
    await waitFor(() => expect(screen.getAllByText("Shared synthetic form")).toHaveLength(2));
    expect(screen.getAllByText("F-0001", { exact: true })).toHaveLength(2);
  });
});
