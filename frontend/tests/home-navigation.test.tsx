import { render, screen } from "@testing-library/react";
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
  it("shows the four active modules in the Owner command center", () => {
    render(<HomePage role="SYSTEM_ADMIN" />);
    expect(screen.getByRole("heading", { name: "Keep work moving from source to cash." })).toBeVisible();
    expect(screen.getAllByTestId("home-module-card")).toHaveLength(3);
    const billingCard = screen.getAllByTestId("home-module-card").find((card) => card.getAttribute("href") === "/billing");
    expect(billingCard).toBeTruthy();
    expect(screen.getByRole("link", { name: /Content Library/ })).toHaveAttribute("href", "/content-library");
    expect(screen.getByText("Human review remains required")).toBeVisible();
    expect(screen.getByRole("heading", { name: "From Proposal to Billing" })).toBeVisible();
  });
});
