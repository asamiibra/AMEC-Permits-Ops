import { test, expect } from "@playwright/test";

test.describe("owner/client rehearsal against seeded FastAPI + PostgreSQL", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      if (!localStorage.getItem("permitops-locale")) localStorage.setItem("permitops-locale", "en");
      if (!sessionStorage.getItem("permitops-role")) sessionStorage.setItem("permitops-role", "PERMIT_PREPARER");
    });
  });

  test("traverses seeded My Work → permit workspace → Arabic and back", async ({ page }) => {
    const businessRequests: string[] = [];
    page.on("request", (request) => { if (request.url().includes("/api/")) businessRequests.push(`${request.method()} ${new URL(request.url()).pathname}`); });
    await page.goto("/work");
    await expect(page.getByRole("heading", { name: "Resume permit work" })).toBeVisible();
    await expect(page.getByText("SYNTHETIC PROTOTYPE", { exact: false }).first()).toBeVisible();
    await page.getByRole("button", { name: /Permits/ }).first().click();
    await expect(page.getByRole("heading", { name: "Permit portfolio" })).toBeVisible();
    await expect(page.getByText(/permit workspaces/)).toBeVisible();
    await page.getByRole("button", { name: "Open workspace" }).first().click();
    await expect(page.getByRole("heading", { name: /Establish the permit workspace|Verify the facts that drive the permit/ })).toBeVisible();
    await expect(page.getByRole("button", { name: "Project & Sources" })).toBeVisible();
    await page.locator(".global-language-switch").click();
    await expect(page.locator("html")).toHaveAttribute("lang", "ar-EG");
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
    await page.reload();
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
    await page.locator(".global-language-switch").click();
    await expect(page.locator("html")).toHaveAttribute("dir", "ltr");
    expect(businessRequests.some((request) => request.includes("/api/projects"))).toBeTruthy();
  });

  test("persists a real municipality preparation revision and reconciled simulator state", async ({ page }) => {
    await page.goto("/work");
    await expect(page.getByRole("heading", { name: "Resume permit work" })).toBeVisible();
    await page.getByLabel("Role").selectOption("SYSTEM_ADMIN");
    await expect(page.getByLabel("Role")).toHaveValue("SYSTEM_ADMIN");
    await page.waitForTimeout(100);
    await page.goto("/admin/municipality");
    await expect(page.getByRole("heading", { name: "Preparation operator" })).toBeVisible();
    await page.getByRole("button", { name: "Create preparation revision" }).click();
    await expect(page.getByText(/^Revision$/)).toBeVisible();
    await page.getByRole("button", { name: "Load portal contract" }).click();
    await expect(page.getByRole("heading", { name: "Portal contract" })).toBeVisible();
    await page.getByRole("button", { name: "Save / reopen / reconcile simulator state" }).click();
    await expect(page.getByText("Persisted simulator state matches intended state.")).toBeVisible();
    await page.reload();
    await expect(page.getByRole("heading", { name: "Preparation operator" })).toBeVisible();
    await expect(page.getByText("Create preparation revision")).toBeVisible();
  });

  test("preserves the final human-submit boundary and role restriction", async ({ page }) => {
    await page.goto("/work");
    await page.getByLabel("Role").selectOption("PERMIT_PREPARER");
    await page.goto("/admin");
    await expect(page).toHaveURL(/\/work$/);
    await expect(page.getByRole("button", { name: /Final Submit|Machine Submit|Submit application/i })).toHaveCount(0);
    await page.goto("/permits");
    await expect(page.getByRole("heading", { name: "Permit portfolio" })).toBeVisible();
    await expect(page.getByText("Open workspace").first()).toBeVisible();
  });
});
