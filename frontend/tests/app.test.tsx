import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../src/App";

vi.stubGlobal("fetch", vi.fn((url:string) => Promise.resolve({ok:true,json:async()=>url.endsWith("/projects")?[]:url.endsWith("/applications")?[]:{}})));

describe("ProposalOps shell", () => {
  it("renders the Home operator shell", async () => {
    render(<App />);
    expect(screen.getAllByRole("img", { name: "AMEC — Art Mark Engineering Consultant" })).toHaveLength(2);
    expect(screen.getByRole("button", { name: /^Home$/ })).toBeTruthy();
    expect(screen.getByText("AMEC Engineering")).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Home", level: 2 })).toBeTruthy();
    expect(screen.getByText("Prioritized work and lifecycle exceptions")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Intake & Opportunity" })).toBeTruthy();
    expect(screen.queryByText("WEEK 1 FOUNDATION")).toBeNull();
  });

  it("provides a mobile navigation disclosure", async () => {
    render(<App />);
    const trigger = screen.getByRole("button", { name: "Open navigation" });
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(trigger);
    await waitFor(() => {
      expect(screen.getByRole("navigation", { name: "Mobile primary navigation" })).toBeTruthy();
      expect(screen.getAllByRole("button", { name: "Close navigation" })).toHaveLength(2);
    });
  });
});
