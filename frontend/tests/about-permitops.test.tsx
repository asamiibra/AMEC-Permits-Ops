import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { AboutPermitOpsPage } from "../src/AboutPermitOps";

describe("About PermitOps explainer", () => {
  it("renders the English explainer with the complete lifecycle and evidence-aware catalog", () => {
    render(<AboutPermitOpsPage onNavigate={vi.fn()} />);
    expect(screen.getByRole("heading", { name: /How PermitOps works/i })).toBeTruthy();
    expect(screen.getByText("Capabilities available in the current MVP")).toBeTruthy();
    expect(document.querySelectorAll(".about-lifecycle-step")).toHaveLength(8);
    expect(screen.getAllByText("Implemented in prototype").length).toBeGreaterThan(0);
    expect(document.querySelector(".about-feature-list")?.textContent).not.toContain("Foundation only");
    expect(document.querySelector(".about-feature-list")?.textContent).not.toContain("Planned / pending scope");
    expect(document.querySelectorAll('bdi[dir="ltr"]').length).toBeGreaterThan(5);
  });

  it("switches to ar-EG with a true RTL root and isolated English terms", () => {
    render(<AboutPermitOpsPage onNavigate={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "العربي" }));
    const root = document.querySelector(".about-page");
    expect(root?.getAttribute("lang")).toBe("ar-EG");
    expect(root?.getAttribute("dir")).toBe("rtl");
    expect(screen.getByRole("heading", { name: "PermitOps بيشتغل إزاي؟" })).toBeTruthy();
    expect(document.querySelector('bdi[dir="ltr"]')?.textContent).toBeTruthy();
    expect(document.querySelectorAll('bdi[dir="ltr"]').length).toBeGreaterThan(10);
  });

  it("keeps the lifecycle in semantic order while allowing the feature groups to collapse", () => {
    render(<AboutPermitOpsPage onNavigate={vi.fn()} />);
    const steps = [...document.querySelectorAll(".about-lifecycle-step .about-step-number")].map((node) => node.textContent);
    expect(steps).toEqual(["1", "2", "3", "4", "5", "6", "7", "8"]);
    const group = screen.getByRole("button", { name: /Project & source control/i });
    expect(group.getAttribute("aria-expanded")).toBe("true");
    fireEvent.click(group);
    expect(group.getAttribute("aria-expanded")).toBe("false");
  });
});
