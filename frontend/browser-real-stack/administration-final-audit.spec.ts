import { expect, test } from "@playwright/test";

const routes = [
  ["/admin/people-access", "Users & Roles"],
  ["/admin/data-connections", "Source Connections"],
  ["/admin/project-folder-setup", "References and project identity"],
  ["/admin/proposal-setup", "Proposal workflow configuration"],
  ["/admin/contract-setup", "Contract reference and policy settings"],
  ["/admin/permit-setup", "Requirements and attachments"],
  ["/admin/templates", "Controlled template catalog"],
  ["/admin/notifications", "Notification audiences and follow-up"],
  ["/admin/security", "Safe operating configuration"],
  ["/admin/integration-health", "Cross-system health"],
  ["/admin/audit", "Owner-readable operational history"],
  ["/admin/advanced-diagnostics", "Technical evidence and diagnostics"],
] as const;

test("every Owner Administration route is directly reachable and uses current business language", async ({ page }) => {
  for (const [route, heading] of routes) {
    await page.goto(route);
    await expect(page.getByRole("heading", { name: heading, level: 3 })).toBeVisible();
    const body = (await page.locator("body").innerText()).toLowerCase();
    expect(body).not.toContain("persona");
    expect(body).not.toContain("quotation");
    expect(body).not.toContain("synthetic_standin");
    expect(body).not.toMatch(/\bsubmit\b/);
    expect(body).not.toContain("administration unavailable");
  }
});

test("Owner Administration cards and bounded actions remain wired", async ({ page }) => {
  await page.goto("/admin");
  for (const [route] of routes) {
    await page.goto(route);
    await expect(page.getByRole("button", { name: "Admin", exact: true }).first()).toBeVisible();
  }
  await page.goto("/admin/data-connections");
  await page.getByRole("button", { name: "Test connection" }).first().click();
  await expect(page.getByRole("status")).toContainText("Simulator Ready");
  await page.goto("/admin/notifications");
  await page.getByLabel("Follow-up reminder timing").fill("48");
  await page.getByRole("button", { name: "Save setting" }).click();
  await expect(page.getByRole("status")).toContainText("saved and audited");
  await page.reload();
  await expect(page.getByLabel("Follow-up reminder timing")).toHaveValue("48");
});

test("Owner Administration stays usable on mobile and role changes re-evaluate direct routes", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/admin/people-access");
  await expect(page.getByRole("heading", { name: "Users & Roles", level: 3 })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)).toBeFalsy();
  await page.goto("/work");
  await page.getByLabel("Persona").selectOption("COMMERCIAL_APPROVER");
  await page.goto("/admin/permit-setup");
  await expect(page).toHaveURL(/\/home$/);
  await page.getByLabel("Persona").selectOption("RESPONSIBLE_ENGINEER");
  await page.goto("/admin/advanced-diagnostics");
  await expect(page).toHaveURL(/\/home$/);
});
