import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { HomePage } from "../src/Home";

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn((input: string | URL) => {
    const path = new URL(String(input), window.location.origin).pathname;
    const body = path === "/api/work/summary"
      ? { summary: { needs_action: 3, waiting_review: 2, blocked: 1 }, projection: [] }
      : { summary: { open_issues: 4, blocking_issues: 1, overdue_unassigned: 0 } };
    return Promise.resolve({ ok: true, headers: { get: () => "application/json" }, text: async () => JSON.stringify(body) });
  }));
});

describe("Home navigation workspace", () => {
  it("shows all seven stages, the parallel Finance lane, and canonical summaries", async () => {
    render(<HomePage role="SYSTEM_ADMIN" />);
    expect(screen.getByRole("heading", { name: "Home" })).toBeVisible();
    expect(screen.getAllByTestId("home-stage-card")).toHaveLength(7);
    expect(screen.getByRole("link", { name: /Finance workspace/ })).toHaveAttribute("href", "/billing");
    await waitFor(() => expect(screen.getByText("Needs action")).toBeVisible());
    expect(screen.getByText("Open issues")).toBeVisible();
    expect(screen.getByText(/Activity remains in the canonical stage workspaces/)).toBeVisible();
  });
});
