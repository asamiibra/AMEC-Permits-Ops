import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import App from "../src/App";

vi.stubGlobal("fetch", vi.fn((url:string) => Promise.resolve({ok:true,json:async()=>url.endsWith("/projects")?[]:url.endsWith("/applications")?[]:{}})));

describe("ProposalOps shell", () => {
  it("renders the Owner command center with the active business module cards", () => {
    window.history.replaceState({}, "", "/home");
    render(<App />);
    expect(screen.getAllByRole("img", { name: "AMEC — Art Mark Engineering Consultant" })).toHaveLength(2);
    expect(screen.getAllByText("AMEC System").length).toBeGreaterThan(0);
    expect(screen.getByText("AMEC Engineering")).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Work across the active ProposalOps modules." })).toBeTruthy();
    expect(screen.getAllByTestId("home-module-card")).toHaveLength(12);
    expect(screen.getByRole("button", { name: "Home" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Opportunities & Proposals" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Contracts & Mobilization" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Billing & Receivables" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Content Library" })).toBeTruthy();
    expect(screen.queryByText("Inputs & Go-Live")).toBeNull();
    expect(screen.getByRole("button", { name: "Administration" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Notifications" })).toBeNull();
    expect(screen.queryByText("SA", { exact: true })).toBeNull();
  });

  it("provides the same five-module navigation on mobile", () => {
    window.history.replaceState({}, "", "/home");
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Open navigation" }));
    const mobileNavigation = screen.getByRole("navigation", { name: "Mobile primary navigation" });
    expect(mobileNavigation.querySelectorAll("button")).toHaveLength(13);
    expect(screen.getByRole("button", { name: "Close navigation" })).toBeTruthy();
  });
});
