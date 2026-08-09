import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "../src/App";
import { AboutPermitOpsPage } from "../src/AboutPermitOps";

const project = { id: "p-0142", project_number: "GHCE-2026-0142", project_name: "Al Noor Villa", municipality: "Doha", permit_type: "Building Permit", status: "ACTIVE", assigned_engineer: "Omar Haddad" };

beforeEach(() => {
  localStorage.clear();
  window.history.pushState({}, "", "/work");
  document.documentElement.lang = "en";
  document.documentElement.dir = "ltr";
  document.body.dir = "ltr";
  vi.stubGlobal("fetch", vi.fn((input: string | URL) => {
    const path = new URL(String(input), window.location.origin).pathname;
    const body = path === "/api/projects" ? [project] : path === "/api/applications" ? [{ id: "a-0142", project_id: project.id, external_request_number: "GHCE-APP-0142", application_status: "DRAFT", repetition_count: 0 }] : path === "/api/reconciliation/governance" ? { environment_badge: "SYNTHETIC PROTOTYPE" } : {};
    return Promise.resolve({ ok: true, json: async () => body });
  }));
});

describe("operating-guide-only language boundary", () => {
  it("ignores stale global locale state and keeps the operational shell English/LTR", async () => {
    localStorage.setItem("permitops.locale", "ar-EG");
    render(<App />);
    await waitFor(() => expect(screen.getByRole("heading", { name: "Resume permit work" })).toBeVisible());
    expect(document.documentElement.lang).toBe("en");
    expect(document.documentElement.dir).toBe("ltr");
    expect(document.querySelector(".global-language-switch")).toBeNull();
    expect(localStorage.getItem("permitops.locale")).toBeNull();
    expect(document.body.textContent).not.toMatch(/[\u0600-\u06FF]/);
  });

  it("allows Arabic only inside the Operating Guide and persists its dedicated preference", () => {
    const onNavigate = vi.fn();
    render(<AboutPermitOpsPage onNavigate={onNavigate} />);
    fireEvent.click(screen.getByRole("button", { name: "العربي" }));
    expect(document.querySelector(".about-page")).toHaveAttribute("lang", "ar-EG");
    expect(document.querySelector(".about-page")).toHaveAttribute("dir", "rtl");
    expect(document.documentElement.lang).toBe("en");
    expect(document.documentElement.dir).toBe("ltr");
    expect(localStorage.getItem("permitops.operatingGuide.locale")).toBe("ar-EG");
    expect(document.querySelector(".app-shell")).toBeNull();
  });

  it("restores the guide preference without changing the global shell", () => {
    localStorage.setItem("permitops.operatingGuide.locale", "ar-EG");
    render(<AboutPermitOpsPage onNavigate={vi.fn()} />);
    expect(document.querySelector(".about-page")).toHaveAttribute("lang", "ar-EG");
    expect(document.querySelector(".about-page")).toHaveAttribute("dir", "rtl");
    expect(document.documentElement.lang).toBe("en");
    expect(document.documentElement.dir).toBe("ltr");
  });
});
