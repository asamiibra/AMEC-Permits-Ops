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
    expect(screen.getByRole("heading", { name: "Work across the active ProposalOps modules." })).toBeVisible();
    expect(screen.getAllByTestId("home-module-card")).toHaveLength(12);
    expect(screen.getByRole("link", { name: /Billing & Receivables/ })).toHaveAttribute("href", "/billing");
    expect(screen.getByRole("link", { name: /Content Library/ })).toHaveAttribute("href", "/content-library");
    expect(screen.getByText("OWNER SHELL")).toBeVisible();
    expect(screen.queryByTestId("home-stage-card")).toBeNull();
  });
});
