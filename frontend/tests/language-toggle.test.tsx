import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "../src/App";
import { LOCALE_STORAGE_KEY, LocaleProvider, normalizeLocale } from "../src/i18n";

const project = { id: "p-0142", project_number: "GHCE-2026-0142", project_name: "Al Noor Villa", municipality: "Doha", permit_type: "Building Permit", status: "ACTIVE", assigned_engineer: "Omar Haddad" };

beforeEach(() => {
  localStorage.clear();
  window.history.pushState({}, "", "/about");
  document.documentElement.lang = "en";
  document.documentElement.dir = "ltr";
  document.body.dir = "ltr";
  document.body.className = "";
  vi.stubGlobal("fetch", vi.fn((input: string | URL) => {
    const path = new URL(String(input), window.location.origin).pathname;
    const body = path === "/api/projects" ? [project] : path === "/api/applications" ? [{ id: "a-0142", project_id: project.id, external_request_number: "GHCE-APP-0142", application_status: "DRAFT", repetition_count: 0 }] : path === "/api/reconciliation/governance" ? { environment_badge: "SYNTHETIC PROTOTYPE" } : {};
    return Promise.resolve({ ok: true, json: async () => body });
  }));
});

function renderApp() {
  return render(<LocaleProvider><App /></LocaleProvider>);
}

async function expectLocale(locale: "en" | "ar-EG") {
  await waitFor(() => {
    expect(document.documentElement.lang).toBe(locale);
    expect(document.documentElement.dir).toBe(locale === "ar-EG" ? "rtl" : "ltr");
    expect(document.getElementById("root") || document.body.firstElementChild).toHaveAttribute("dir", locale === "ar-EG" ? "rtl" : "ltr");
    expect(localStorage.getItem(LOCALE_STORAGE_KEY)).toBe(locale);
  });
}

function toggleGlobalLanguage() {
  const button = document.querySelector<HTMLButtonElement>(".global-language-switch");
  if (!button) throw new Error("Global language switch was not rendered");
  fireEvent.click(button);
}

describe("global language toggle persistence", () => {
  it("normalizes supported legacy values and rejects unknown locale values", () => {
    expect(normalizeLocale("ar")).toBe("ar-EG");
    expect(normalizeLocale("arabic")).toBe("ar-EG");
    expect(normalizeLocale("en-US")).toBe("en");
    expect(normalizeLocale("english")).toBe("en");
    expect(normalizeLocale("fr-FR")).toBe("en");
  });

  it.each([
    ["en", "ar-EG", "en"],
    ["ar-EG", "en", "ar-EG"],
    ["en", "ar-EG", "en", "ar-EG", "en"],
  ])("supports reversible toggle cycle %s", async (...cycle: string[]) => {
    localStorage.setItem(LOCALE_STORAGE_KEY, cycle[0]);
    renderApp();
    await expectLocale(cycle[0] as "en" | "ar-EG");
    for (const expected of cycle.slice(1)) {
      toggleGlobalLanguage();
      await expectLocale(expected as "en" | "ar-EG");
    }
    expect(document.documentElement.dir).toBe(cycle[cycle.length - 1] === "ar-EG" ? "rtl" : "ltr");
  });

  it("persists Arabic and English across a provider remount", async () => {
    const first = renderApp();
    await expectLocale("en");
    toggleGlobalLanguage();
    await expectLocale("ar-EG");
    first.unmount();

    renderApp();
    await expectLocale("ar-EG");
    toggleGlobalLanguage();
    await expectLocale("en");
    expect(localStorage.getItem(LOCALE_STORAGE_KEY)).toBe("en");
  });

  it("keeps About and the open Inputs & Go-Live drawer on the shared locale", async () => {
    renderApp();
    await expectLocale("en");
    toggleGlobalLanguage();
    await expectLocale("ar-EG");
    expect(document.querySelector("main.about-page")).toHaveAttribute("lang", "ar-EG");
    expect(screen.getByRole("heading", { name: "PermitOps بيشتغل إزاي؟" })).toBeTruthy();
    toggleGlobalLanguage();
    await expectLocale("en");
    expect(document.querySelector("main.about-page")).toHaveAttribute("lang", "en");
    expect(screen.getByRole("heading", { name: "How PermitOps works" })).toBeTruthy();

    window.history.pushState({}, "", "/work");
    window.dispatchEvent(new PopStateEvent("popstate"));
    await waitFor(() => expect(screen.getByRole("heading", { name: "Resume permit work" })).toBeVisible());
    fireEvent.click(screen.getByRole("button", { name: "Inputs & Go-Live" }));
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Switch to Arabic" }));
    await expectLocale("ar-EG");
    expect(screen.getByRole("dialog")).toHaveAttribute("dir", "rtl");
    toggleGlobalLanguage();
    await expectLocale("en");
    expect(screen.getByRole("dialog")).toHaveAttribute("lang", "en");
    expect(screen.getByRole("dialog")).toHaveAttribute("dir", "ltr");
    expect(within(screen.getByRole("dialog")).getByRole("button", { name: "Switch to Arabic" })).toBeTruthy();
  });

  it("preserves the current route while switching language", async () => {
    window.history.pushState({}, "", "/notifications");
    renderApp();
    await expectLocale("en");
    toggleGlobalLanguage();
    await expectLocale("ar-EG");
    toggleGlobalLanguage();
    await expectLocale("en");
    expect(window.location.pathname).toBe("/notifications");
  });
});
