import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import App from "../src/App";

vi.stubGlobal("fetch", vi.fn((url:string) => Promise.resolve({ok:true,json:async()=>url.endsWith("/projects")?[]:url.endsWith("/applications")?[]:{}})));

describe("ProposalOps shell", () => {
  // STALE_PRE_OWNER_MODULE_SCOPE_EXPECTATION:
  // this replaces the former /work + seven-stage shell assertion because the
  // Owner decision makes Home + four active modules the canonical shell.
  it("renders the Owner command center with exactly four active module cards", () => {
    window.history.replaceState({}, "", "/home");
    render(<App />);
    expect(screen.getAllByRole("img", { name: "AMEC — Art Mark Engineering Consultant" })).toHaveLength(2);
    expect(screen.getAllByText("AMEC Works").length).toBeGreaterThan(0);
    expect(screen.getByText("AMEC Engineering")).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Work across the active ProposalOps modules." })).toBeTruthy();
    expect(screen.getAllByTestId("home-module-card")).toHaveLength(4);
    expect(screen.getByRole("button", { name: "Home" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Opportunity / Proposal / Client Tender" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Contract / Mobilization" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Billing / Invoice / Receivables / Collection" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Content Library" })).toBeTruthy();
    expect(screen.queryByText("Inputs & Go-Live")).toBeNull();
    expect(screen.queryByRole("button", { name: "Admin" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Notifications" })).toBeNull();
  });
});