import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { AboutPermitOpsPage } from "../src/AboutPermitOps";

beforeEach(() => localStorage.clear());

describe("Operating Guide explainer", () => {
  it("renders the current Proposal to Contract to Permit story", () => {
    render(<AboutPermitOpsPage onNavigate={vi.fn()} />);
    expect(screen.getByRole("heading", { name: "The AMEC workflow" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Proposal → Contract → Permit" })).toBeTruthy();
    expect(screen.getByText(/move work from tender and proposal through contract and permit/)).toBeTruthy();
    expect(screen.getByText("Proceed means Proposal Intake has enough verified information to move into Engineering Proposal Preparation.")).toBeTruthy();
    expect(screen.getByText("AMEC Work")).toBeTruthy();
    expect(screen.getByText("Notifications")).toBeTruthy();
    expect(document.querySelectorAll(".about-lifecycle-step")).toHaveLength(7);
  });

  it("switches to ar-EG with a true RTL root and isolated English terms", () => {
    render(<AboutPermitOpsPage onNavigate={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "العربي" }));
    const root = document.querySelector(".about-page");
    expect(root?.getAttribute("lang")).toBe("ar-EG");
    expect(root?.getAttribute("dir")).toBe("rtl");
    expect(screen.getByRole("heading", { name: "دورة عمل AMEC" })).toBeTruthy();
    expect(document.querySelector('bdi[dir="ltr"]')?.textContent).toBeTruthy();
    expect(document.querySelectorAll('bdi[dir="ltr"]').length).toBeGreaterThan(10);
    expect(localStorage.getItem("permitops.operatingGuide.locale")).toBe("ar-EG");
  });

  it("keeps the lifecycle in semantic order and removes retired guide language", () => {
    render(<AboutPermitOpsPage onNavigate={vi.fn()} />);
    const steps = [...document.querySelectorAll(".about-lifecycle-step .about-step-number")].map((node) => node.textContent);
    expect(steps).toEqual(["1", "2", "3", "4", "5", "6", "7"]);
    expect(document.querySelector(".about-page")?.textContent).not.toMatch(/PermitOps|Permit Preparer|four assistants|Resume permit work|E7|persona projection|HUMAN_SEND|MISSING_DOCUMENT/);
  });
});
