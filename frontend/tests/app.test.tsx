import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import App from "../src/App";

vi.stubGlobal("fetch", vi.fn((url:string) => Promise.resolve({ok:true,json:async()=>url.endsWith("/projects")?[]:url.endsWith("/applications")?[]:{}})));

describe("ProposalOps shell", () => {
  it("renders the Owner command center and complete primary navigation", () => {
    window.history.replaceState({}, "", "/home");
    render(<App />);
    expect(screen.getAllByRole("img", { name: "AMEC — Art Mark Engineering Consultant" })).toHaveLength(2);
    expect(screen.getAllByText("AMEC System").length).toBeGreaterThan(0);
    expect(screen.getByText("AMEC Engineering")).toBeTruthy();
    expect(screen.getAllByRole("heading", { name: "Home" })).toHaveLength(2);
    expect(screen.getAllByRole("link", { name: /Open workspace/ })).toHaveLength(7);
    expect(screen.getByRole("button", { name: "Home" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "My Work" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Opportunities & Proposals" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Contract & Mobilization" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Projects & Delivery" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Billing & Finance" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Content Library" })).toBeTruthy();
    expect(screen.queryByText("Inputs & Go-Live")).toBeNull();
    expect(screen.queryByRole("button", { name: "Admin" })).toBeNull();
    expect(screen.getByRole("link", { name: "Notifications" })).toBeTruthy();
    expect(screen.queryByText("SA", { exact: true })).toBeNull();
  });

  it("provides the same primary navigation on mobile", () => {
    window.history.replaceState({}, "", "/home");
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Open navigation" }));
    const mobileNavigation = screen.getByRole("navigation", { name: "Mobile primary navigation" });
    expect(mobileNavigation.querySelectorAll("button")).toHaveLength(7);
    expect(screen.getByRole("button", { name: "Close navigation" })).toBeTruthy();
  });
});
