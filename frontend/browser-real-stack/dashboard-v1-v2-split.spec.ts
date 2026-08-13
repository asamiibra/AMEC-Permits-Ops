import { expect, test } from "@playwright/test";

test("home exposes the legacy Dashboard and Owner-only Dashboard V2 destinations", async ({ page }) => {
  await page.goto("/work");
  await expect(page.getByRole("heading", { name: "What needs attention", level: 2 })).toBeVisible();
  await expect(page.getByRole("link", { name: /Open Dashboard →/ })).toHaveAttribute("href", "/dashboard");
  await expect(page.getByRole("link", { name: /Open Dashboard V2 →/ })).toHaveAttribute("href", "/dashboard-v2");

  await page.getByRole("link", { name: /Open Dashboard →/ }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("heading", { name: "Dashboard", level: 2 })).toBeVisible();
  await expect(page.getByText("Advanced governance filters")).toHaveCount(0);

  await page.goto("/dashboard-v2");
  await expect(page).toHaveURL(/\/dashboard-v2$/);
  await expect(page.getByRole("heading", { name: "Dashboard V2", level: 2 })).toBeVisible();
  await expect(page.getByText("Advanced governance filters")).toBeVisible();
  await page.getByRole("link", { name: "Inputs & Go-Live" }).click();
  await expect(page).toHaveURL(/\/dashboard-v2\/inputs-go-live$/);
  await expect(page.getByRole("heading", { name: "Master Content Setup & Go-Live", level: 2 })).toBeVisible();
});

test("non-owner direct navigation is redirected away from Dashboard V2", async ({ page }) => {
  await page.goto("/work");
  await page.getByLabel("Persona").selectOption("COMMERCIAL_APPROVER");
  await page.goto("/dashboard-v2");
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("heading", { name: "Dashboard", level: 2 })).toBeVisible();
  await expect(page.getByText("Advanced governance filters")).toHaveCount(0);
  await expect(page.getByRole("link", { name: /Open Dashboard V2 →/ })).toHaveCount(0);
});

test("captures sanitized visual evidence for the split surfaces", async ({ page }) => {
  await page.goto("/work");
  await expect(page.getByRole("heading", { name: "What needs attention", level: 2 })).toBeVisible();
  await page.screenshot({ path: "../artifacts/dashboard-v1-v2-split/home-dual-dashboards.png", fullPage: true });

  await page.goto("/dashboard");
  await expect(page.getByRole("heading", { name: "Dashboard", level: 2 })).toBeVisible();
  await page.screenshot({ path: "../artifacts/dashboard-v1-v2-split/dashboard-v1.png", fullPage: true });

  await page.goto("/dashboard-v2");
  await expect(page.getByRole("heading", { name: "Dashboard V2", level: 2 })).toBeVisible();
  await page.screenshot({ path: "../artifacts/dashboard-v1-v2-split/dashboard-v2.png", fullPage: true });
});
