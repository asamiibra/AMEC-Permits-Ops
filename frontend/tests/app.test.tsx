import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import App from "../src/App";

vi.stubGlobal("fetch", vi.fn((url:string) => Promise.resolve({ok:true,json:async()=>url.endsWith("/projects")?[]:url.endsWith("/applications")?[]:{}})));

describe("ProposalOps shell", () => {
  it("renders the workflow-first operator shell", async () => {
    render(<App />);
    expect(screen.getAllByRole("img", { name: "AMEC — Art Mark Engineering Consultant" })).toHaveLength(2);
    expect(screen.getAllByText("AMEC Work").length).toBeGreaterThan(0);
    expect(screen.getByText("AMEC Engineering")).toBeTruthy();
    expect(screen.getByRole("heading", { name: "What needs attention" })).toBeTruthy();
    expect(screen.getByText("One prioritized worklist across proposals, contracts, permits, and handoffs.")).toBeTruthy();
    expect(screen.queryByText("WEEK 1 FOUNDATION")).toBeNull();
  });
});
