import { expect, test } from "@playwright/test";

test("Home exposes the seven-stage business flow and cross-functional lanes", async ({ page }) => {
  await page.goto("/home");
  await expect(page.getByRole("heading", { name: "Home", level: 2 })).toBeVisible();
  for (const label of ["Intake & Opportunity", "Contract & Mobilization", "Design & Technical Delivery", "Regulatory & Submissions", "Construction & Post-Approval", "Completion & As-Built", "Handover & Closeout"]) {
    await expect(page.getByRole("link", { name: new RegExp(label) })).toBeVisible();
  }
  await expect(page.getByRole("link", { name: /Finance workspace/ })).toHaveAttribute("href", "/billing");
  await expect(page.getByTestId("amec-work-widget")).toBeVisible();
  await expect(page.getByTestId("issues-widget")).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Primary navigation" })).not.toContainText("Notifications");
});

test("Content Library keeps the old route and the renamed owner-facing identity", async ({ page }) => {
  await page.goto("/dashboard");
  await expect(page.getByRole("heading", { name: "Content Library", level: 2 })).toBeVisible();
  await expect(page.getByText("Master Forms, Reports, Engineering Works & Definitions")).toBeVisible();
  await page.goto("/dashboard-v2?source=legacy");
  await expect(page).toHaveURL(/\/dashboard\?source=legacy$/);
  await expect(page.getByRole("heading", { name: "Content Library", level: 2 })).toBeVisible();
});

test("Header bell opens a notification drawer without creating a sidebar module", async ({ page }) => {
  await page.goto("/home");
  await page.getByRole("button", { name: "Notifications" }).click();
  await expect(page.getByRole("dialog", { name: "Notification drawer" })).toBeVisible();
  await expect(page.getByRole("link", { name: /View all notifications/ })).toHaveAttribute("href", "/notifications");
  await expect(page.getByRole("navigation", { name: "Primary navigation" })).not.toContainText("Notifications");
});

test("Persona navigation keeps system Admin separate from business roles", async ({ page }) => {
  await page.goto("/home");
  await page.getByLabel("Persona").selectOption("COMMERCIAL_APPROVER");
  await expect(page.getByRole("button", { name: "Finance" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Admin" })).toHaveCount(0);
  await page.getByLabel("Persona").selectOption("RESPONSIBLE_ENGINEER");
  await expect(page.getByRole("button", { name: "Design & Technical Delivery" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Finance" })).toHaveCount(0);
});
