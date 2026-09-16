import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const emptyBillingCapabilities = {
  role: "SYSTEM_ADMIN",
  capabilities: { billing_read: true },
  authority_source: "SERVER_MUTATION_POLICY",
  frontend_only_authority_grants: 0,
  unresolved_owner_decisions: [],
};

async function mockCurrentProductApis(route: any) {
  const url = new URL(route.request().url());
  const path = url.pathname;
  let body: unknown = {};
  if (path === "/api/projects" || path === "/api/applications" || path === "/api/retrieval/query") body = [];
  else if (path === "/api/bd/proposals/clients") body = { items: [] };
  else if (path === "/api/bd/proposals") body = { items: [], lane_counts: { ALL: 0, NEED_ACTION: 0, AUTHORITY_REVIEW: 0, READY_CLOSE: 0 }, count: 0 };
  else if (path === "/api/admin/contracts") body = { items: [], count: 0, synthetic_only: true };
  else if (path === "/api/billing/capabilities") body = emptyBillingCapabilities;
  else if (path === "/api/billing/command-center") body = {
    metrics: { ready_to_invoice: 0, draft_review_required: 0, issued_outstanding: 0, overdue: 0, payments_to_verify: 0, unallocated_client_credit: 0 },
    work_items: [], open_receivables: [], payments: [], source_of_truth: "canonical Billing records", system_insights_only: true, ai_assisted: false, unresolved_owner_decisions: [],
  };
  else if (path === "/api/master-content" || path === "/api/master-content/categories" || path === "/api/definitions") body = [];
  else if (path === "/api/dashboard-v2/catalogs") body = { external_bodies: [], jurisdictions: [], service_types: [], lifecycle_phases: [] };
  else if (path === "/api/dashboard-inputs") body = { summary: { confirmed: 0, remaining: 0, technical_remaining: 0, ready: true }, groups: [], items: [] };
  else if (path.startsWith("/api/billing/")) body = { items: [], total: 0 };
  await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
}

test.describe("current-product whole-app UX acceptance", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => sessionStorage.setItem("proposalops-role", "SYSTEM_ADMIN"));
    await page.route("**/api/**", mockCurrentProductApis);
  });

  test("renders the current route census at desktop and records visual evidence", async ({ page }, testInfo) => {
    await page.setViewportSize({ width: 1440, height: 1000 });
    const screens = [
      ["home", "/home", "Keep work moving from source to cash."],
      ["proposal-register", "/proposals", "Proposal worklist"],
      ["proposal-intake", "/proposals/new", "New Proposal"],
      ["contract-register", "/contract-mobilization", "Contract & Mobilization"],
      ["billing-command-center", "/billing", "Command Center"],
      ["content-library", "/dashboard", "Content Library"],
    ] as const;

    for (const [id, path, heading] of screens) {
      await page.goto(path, { waitUntil: "domcontentloaded" });
      await expect(page.getByRole("heading", { name: heading, exact: true }).first()).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
      const axe = await new AxeBuilder({ page }).analyze();
      expect(axe.violations.filter((item) => ["critical", "serious"].includes(item.impact || "")), `${id} accessibility`).toEqual([]);
      await page.screenshot({ path: testInfo.outputPath(`census-${id}.png`), fullPage: true });
    }
  });

  test("intake, contract, and billing states expose human action boundaries", async ({ page }) => {
    await page.goto("/proposals/new");
    await page.getByRole("button", { name: "Client Information" }).click();
    await expect(page.getByLabel("Proposal contact")).toBeVisible();
    await page.getByRole("button", { name: "Tender Photo / Image" }).click();
    await expect(page.getByLabel("Tender Photo / Image file")).toHaveAttribute("accept", "image/*");
    await page.goto("/contract-mobilization");
    await expect(page.getByRole("heading", { name: "Contracts", level: 3 })).toBeVisible();
    await expect(page.getByText("No Contracts in this lane.", { exact: true })).toBeVisible();
    await page.goto("/billing");
    await expect(page.getByRole("heading", { name: "Authority and policy", level: 3 })).toBeVisible();
    await expect(page.getByText("AI canonical write authority: ZERO", { exact: false })).toBeVisible();
    await expect(page.getByText("Coming soon", { exact: false })).toHaveCount(0);
  });

  test("Billing permission failure is actionable and does not leak raw API text", async ({ page }) => {
    await page.unroute("**/api/**");
    await page.route("**/api/**", mockCurrentProductApis);
    await page.route("**/api/billing/capabilities", async (route) => {
      await route.fulfill({ status: 403, contentType: "application/json", body: JSON.stringify({ detail: "raw forbidden detail" }) });
    });
    await page.goto("/billing");
    await expect(page.getByRole("alert")).toContainText("Your role does not have Billing access");
    await expect(page.getByRole("alert")).not.toContainText("raw forbidden detail");
  });
});
