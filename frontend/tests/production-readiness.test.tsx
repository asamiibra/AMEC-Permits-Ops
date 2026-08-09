import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { ReadinessDrawer, customerProductionRequirements, getScreenDefinition, getScreenUnresolvedCount, screenReadinessRegistry, statusLabel } from "../src/ProductionReadiness";

describe("central production-readiness registry", () => {
  it("covers every screen with unique identity, inputs, outputs, and valid requirement references", () => {
    const screenIds = screenReadinessRegistry.map((screen) => screen.screenId);
    expect(new Set(screenIds).size).toBe(screenIds.length);
    expect(screenReadinessRegistry.length).toBeGreaterThan(40);
    for (const screen of screenReadinessRegistry) {
      expect(screen.purpose.length).toBeGreaterThan(10);
      expect(screen.runtimeInputs.length).toBeGreaterThan(0);
      expect(screen.runtimeOutputs.length).toBeGreaterThan(0);
      for (const id of screen.customerRequirementIds) expect(customerProductionRequirements.some((item) => item.id === id)).toBe(true);
    }
    expect(customerProductionRequirements.every((item) => item.appliesToScreenIds.length > 0 || item.status === "NOT_APPLICABLE")).toBe(true);
  });

  it("uses business-friendly status labels and separates unresolved from not-needed requirements", () => {
    expect(statusLabel.en.NOT_REQUESTED).toBe("Needed");
    expect(statusLabel.en.NOT_APPLICABLE).toBe("Not Needed");
    expect(getScreenUnresolvedCount(getScreenDefinition("FINAL_REVIEW"))).toBeGreaterThan(0);
    expect(getScreenDefinition("go-live-readiness").pageKey).toBe("go-live-readiness");
    expect(getScreenDefinition("go-live-readiness").routePatterns).toContain("/admin/go-live-readiness");
  });
});

describe("contextual readiness drawer", () => {
  it("shows English purpose, inputs, outputs, customer asks, and the fixed LTR boundary", () => {
    render(<ReadinessDrawer screenId="S10" role="PERMIT_PREPARER" onNavigate={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Inputs & Go-Live" }));
    expect(screen.getByRole("dialog")).toHaveAttribute("lang", "en");
    expect(screen.getByRole("dialog")).toHaveAttribute("dir", "ltr");
    expect(screen.getByText("What this screen uses")).toBeTruthy();
    expect(screen.getByText("What this screen produces")).toBeTruthy();
    expect(screen.getByText("What we need from AMEC")).toBeTruthy();
    expect(screen.getAllByText(/human-only|human/i).length).toBeGreaterThan(0);
    expect(screen.queryByRole("button", { name: "Switch to Arabic" })).toBeNull();
    expect(document.body.textContent).not.toMatch(/[\u0600-\u06FF]/);
    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});
