import { expect, test } from "@playwright/test";

test("Owner can navigate the business Administration surface and persist a setting", async ({ page }) => {
  await page.addInitScript(() => sessionStorage.setItem("proposalops-role", "SYSTEM_ADMIN"));
  await page.goto("/admin");
  await expect(page.getByRole("heading", { name: "Administration", level: 2 }).filter({ hasText: /^Administration$/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Contracts", level: 3 })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Invoices", level: 3 })).toBeVisible();
  await expect(page.getByRole("button", { name: "Billing / Invoice", exact: true })).toHaveCount(0);
  await expect(page.getByText("Business Record", { exact: true })).toHaveCount(1);
  await expect(page.locator(".admin-operational-preview-lanes").first()).toContainText("All");
  await page.getByRole("button", { name: /Setup & Controls/ }).click();
  for (const label of ["People & Access", "Data & Connections", "Project & Folder Setup", "Proposal Setup", "Contract Setup", "Permit Workflow Setup", "Templates & Documents", "Notifications & Follow-up", "Data, Security & Retention", "Integration Health", "Audit History", "Advanced Diagnostics"]) {
    await expect(page.getByRole("button", { name: new RegExp(label) })).toBeVisible();
  }
  await page.getByRole("button", { name: /Notifications & Follow-up/ }).click();
  await expect(page.getByRole("heading", { name: "Notification audiences and follow-up", level: 3 })).toBeVisible();
  // The card navigation starts an async projection load; reload once the
  // route is reached so the controlled input cannot be overwritten by that
  // first response while the browser types.
  await page.reload();
  await expect(page.getByRole("heading", { name: "Notification audiences and follow-up", level: 3 })).toBeVisible();
  await page.getByLabel("Follow-up reminder timing").fill("36");
  await page.getByRole("button", { name: "Save setting" }).click();
  await expect(page.getByText(/Follow-up timing saved and audited/)).toBeVisible();
  await page.reload();
  await expect(page.getByLabel("Follow-up reminder timing")).toHaveValue("36");
});

test("Owner Administration exposes the sketch workspaces and backend-derived lanes", async ({ page }) => {
  await page.goto("/admin");
  await page.getByRole("button", { name: "View all Contracts" }).click();
  await expect(page.getByRole("heading", { name: "Contracts", level: 3 })).toBeVisible();
  for (const label of ["All", "Need Action", "Authority Review", "Ready / Close"]) {
    await expect(page.getByRole("tab", { name: new RegExp(label) })).toBeVisible();
  }
  await page.getByRole("button", { name: /Administration/ }).first().click();
  await page.getByRole("button", { name: "View all Invoices" }).click();
  await expect(page.getByRole("heading", { name: "Invoices", level: 2 }).first()).toBeVisible();
  await expect(page.getByRole("tab", { name: /Need Action/ })).toBeVisible();
});

test("Owner Administration sections load real backend projections", async ({ page }) => {
  await page.goto("/admin/data-connections");
  await expect(page.getByRole("heading", { name: "Source Connections", level: 3 })).toBeVisible();
  await expect(page.getByText("Synthetic connector", { exact: false }).first()).toBeVisible();
  await page.getByRole("button", { name: "Test connection" }).first().click();
  await expect(page.getByRole("status")).toContainText("Simulator Ready");
  await page.goto("/admin/project-folder-setup");
  await expect(page.getByRole("heading", { name: "References and project identity", level: 3 })).toBeVisible();
  await page.reload();
  await expect(page.getByText("Canonical Project Reference", { exact: true })).toBeVisible();
});

test("BD and Engineering cannot retain privileged Administration access", async ({ page }) => {
  await page.goto("/work");
  await page.getByLabel("Persona").selectOption("COMMERCIAL_APPROVER");
  await expect(page.getByRole("button", { name: "Administration", exact: true })).toHaveCount(0);
  await page.goto("/admin");
  await expect(page).toHaveURL(/\/home$/);
  await page.getByLabel("Persona").selectOption("RESPONSIBLE_ENGINEER");
  await expect(page.getByRole("button", { name: "Administration", exact: true })).toHaveCount(0);
  await page.goto("/admin/people-access");
  await expect(page).toHaveURL(/\/home$/);
});

test("Administration remains usable on a narrow viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/admin");
  await expect(page.getByRole("heading", { name: "Administration", level: 2 }).filter({ hasText: /^Administration$/ })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
  expect(overflow).toBeFalsy();
});
