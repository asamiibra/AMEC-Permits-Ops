import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../src/App";
import { CurrentDashboard } from "../src/Dashboard";

function response(body: unknown) {
  return Promise.resolve({
    ok: true,
    headers: { get: () => "application/json" },
    text: async () => JSON.stringify(body),
  });
}

beforeEach(() => {
  window.history.replaceState({}, "", "/home");
  vi.stubGlobal("fetch", vi.fn((input: string | URL) => {
    const url = new URL(String(input), window.location.origin);
    if (url.pathname === "/api/master-content" && url.searchParams.get("content_type") === "FORM") return response([{ id: "form-1" }]);
    if (url.pathname === "/api/master-content") return response([]);
    if (url.pathname === "/api/master-content/categories") return response([]);
    if (url.pathname === "/api/definitions") return response([]);
    if (url.pathname === "/api/projects" || url.pathname === "/api/applications") return response([]);
    if (url.pathname === "/api/dashboard-inputs") return response({
      summary: { remaining: 0, confirmed: 0, technical_remaining: 0, ready: true },
      groups: [],
      items: [],
    });
    return response({});
  }));
});

afterEach(() => {
  window.history.replaceState({}, "", "/home");
  vi.restoreAllMocks();
});

describe("Content Library first-class route contract", () => {
  it("exposes one shared Content Library navigation entry to every visible persona", async () => {
    render(<App />);
    const persona = screen.getByLabelText("Persona");
    for (const role of ["SYSTEM_ADMIN", "COMMERCIAL_APPROVER", "RESPONSIBLE_ENGINEER"]) {
      fireEvent.change(persona, { target: { value: role } });
      expect(screen.getAllByRole("button", { name: "Content Library" })).toHaveLength(1);
    }
    fireEvent.click(screen.getByRole("button", { name: "Content Library" }));
    await waitFor(() => expect(window.location.pathname).toBe("/content-library"));
  });

  it.each(["/dashboard", "/dashboard-v2", "/library", "/master-content"])("normalizes legacy alias %s to the canonical feature", async (alias) => {
    window.history.replaceState({}, "", alias);
    render(<App />);
    await waitFor(() => expect(window.location.pathname).toBe("/content-library"));
    expect(screen.getByRole("heading", { name: "Content Library", level: 2 })).toBeTruthy();
  });

  it("keeps specialized go-live routes outside the Content Library alias", async () => {
    window.history.replaceState({}, "", "/dashboard/inputs-go-live");
    render(<App />);
    await waitFor(() => expect(window.location.pathname).toBe("/dashboard/inputs-go-live"));
  });

  it.each([
    ["/content-library/forms", "Forms"],
    ["/content-library/reports", "Reports"],
    ["/content-library/engineering-works", "Engineering Works"],
    ["/content-library/definitions", "Definitions"],
  ])("renders the selected library for a direct deep link: %s", async (path, heading) => {
    window.history.replaceState({}, "", path);
    render(<CurrentDashboard role="SYSTEM_ADMIN" />);
    await waitFor(() => expect(screen.getByRole("heading", { name: heading, level: 3 })).toBeVisible());
    const link = screen.getByRole("link", { name: new RegExp(heading) });
    expect(link).toHaveAttribute("href", path);
    expect(link).toHaveAttribute("aria-current", "page");
  });
});
