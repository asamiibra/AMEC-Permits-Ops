import { test, expect } from "@playwright/test";

const summary = {
  categories: [
    { key: "people-access", label: "People & Access", route: "/admin/people-access", status: "Configured" },
    { key: "data-connections", label: "Data & Connections", route: "/admin/data-connections", status: "Configured" },
    { key: "audit", label: "Audit", route: "/admin/audit", status: "Configured" },
    { key: "contract-setup", label: "Contract Configuration", route: "/admin/contract-setup", status: "Configured" },
  ],
  go_live: { route: "/admin/go-live-readiness" },
};

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => sessionStorage.setItem("permitops-role", "SYSTEM_ADMIN"));
  await page.route("**/api/**", async (route) => {
    const url = new URL(route.request().url());
    let body: any = {};
    if (url.pathname === "/api/reconciliation/governance") body = { environment_badge: "SYNTHETIC PROTOTYPE" };
    else if (url.pathname === "/api/projects") body = [];
    else if (url.pathname === "/api/applications") body = [];
    else if (url.pathname === "/api/admin/summary") body = summary;
    else if (url.pathname === "/api/admin/contracts") body = { items: [], count: 0 };
    else if (url.pathname === "/api/bd/proposals") body = { items: [] };
    else if (url.pathname === "/api/billing/invoices") body = { items: [], total: 0, lanes: { all: 0, need_action: 0, authority_review: 0, ready_close: 0 } };
    else if (url.pathname === "/api/billing/summary") body = { plans: 0, milestones: 0, invoices: 0, payment_receipts: 0 };
    else if (url.pathname === "/api/master-content") body = { items: [] };
    await route.fulfill({ json: body });
  });
});

test("Admin is system-only while Contract & Mobilization owns the Contract register", async ({ page }) => {
  await page.goto("/admin");
  await expect(page.getByRole("heading", { name: "Admin", level: 2 })).toBeVisible();
  await expect(page.getByText("Admin owns configuration, not business records")).toBeVisible();
  await expect(page.locator(".admin-operational-register")).toHaveCount(0);
  await expect(page.locator(".billing-page")).toHaveCount(0);

  await page.goto("/contract-mobilization?view=contracts");
  await expect(page.getByRole("heading", { name: "Contract & Mobilization", level: 2 })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Contracts", level: 3 })).toBeVisible();
  await expect(page.getByText("One canonical Contract register sourced from the accepted Proposal revision")).toBeVisible();
});

test("legacy Admin business links redirect to their owning workspaces", async ({ page }) => {
  await page.goto("/admin/contracts");
  await expect(page).toHaveURL(/\/contract-mobilization\?view=contracts$/);
  await expect(page.getByRole("heading", { name: "Contracts", level: 3 })).toBeVisible();

  await page.goto("/admin/invoices");
  await expect(page).toHaveURL(/\/billing$/);
  await expect(page.getByRole("heading", { name: /Finance · Billing & Invoice/ })).toBeVisible();
  await expect(page.getByText("ADMINISTRATION / INVOICES")).toHaveCount(0);

  await page.goto("/admin/project-activation");
  await expect(page).toHaveURL(/\/contract-mobilization\?view=activation$/);
  await expect(page.getByRole("heading", { name: "Contract & Mobilization", level: 2 })).toBeVisible();
});

test("role visibility remains bounded while direct business routes remain available", async ({ page }) => {
  await page.goto("/home");
  await expect(page.getByRole("button", { name: "Admin", exact: true })).toBeVisible();
  await page.getByLabel("Persona").selectOption("COMMERCIAL_APPROVER");
  await expect(page.getByRole("button", { name: "Admin", exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Contract & Mobilization", exact: true })).toBeVisible();
  await page.goto("/contract-mobilization");
  await expect(page.getByRole("heading", { name: "Contract & Mobilization", level: 2 })).toBeVisible();
});
