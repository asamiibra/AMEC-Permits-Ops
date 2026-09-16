import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const record = {
  id: "ui-contract", contract: { name: "Villa Design Services", reference: "C-UI-001", stage: "DRAFT", authority_state: "PENDING" },
  current_revision: { id: "revision-1", revision_number: 1, accepted: false, status: "DRAFT" },
  readiness: { blockers: [{ code: "CHECKER_REQUIRED", label: "Independent checker review required" }] },
  operations: { lifecycle_milestones: [], readiness_states: { states: {} } },
  client: { name: "Synthetic Client" }, evidence: [], payment_terms: [], deliverables: [], client_inputs: [], history: [],
};

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => { sessionStorage.setItem("proposalops-role", "SYSTEM_ADMIN"); localStorage.setItem("locale", "ar"); });
  await page.route("**/health", route => route.fulfill({ json: { environment: "TEST", synthetic_only: true } }));
  await page.route("**/api/admin/contracts/ui-contract", route => route.fulfill({ json: record }));
  await page.route("**/api/admin/contracts/ui-contract/start-prerequisites", route => route.fulfill({ json: { contract_revision_id: "revision-1", status: "BLOCKED", facts: [{ fact: "CLIENT_ARCHITECTURE_APPROVED", applicable: false, state: "NOT_APPLICABLE", required_for: [], source_clause: "No clause", evidence_ids: [] }], blockers: [], blockers_by_transition: {}, policy_version: "v2" } }));
});

test("legacy links, history, locale and current section survive navigation", async ({ page }) => {
  await page.goto("/admin/contracts/ui-contract");
  await expect(page).toHaveURL(/\/contract-mobilization\/contracts\/ui-contract$/);
  await expect(page.getByRole("heading", { name: "Villa Design Services" })).toBeVisible();
  expect(await page.evaluate(() => localStorage.getItem("locale"))).toBe("ar");
  await page.getByRole("button", { name: "Mobilization & Start", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Timing requirements & facts" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Review & Acceptance", exact: true })).toHaveCount(0);
  await page.reload();
  await expect(page.getByRole("heading", { name: "Timing requirements & facts" })).toBeVisible();
  await page.goBack();
  await expect(page.getByRole("heading", { name: "What needs attention" })).toBeVisible();
});

test("a failed detail read can recover through Retry", async ({ page }) => {
  let fail = true;
  await page.route("**/api/admin/contracts/ui-contract", route => fail ? route.fulfill({ status: 503, json: { detail: "Database not available" } }) : route.fulfill({ json: record }));
  await page.goto("/contract-mobilization/contracts/ui-contract");
  await expect(page.getByRole("heading", { name: "Contract workspace unavailable" })).toBeVisible();
  await expect(page.getByText("Database not available", { exact: true })).toHaveCount(0);
  fail = false;
  await page.getByRole("button", { name: "Retry", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Villa Design Services" })).toBeVisible();
});

for (const width of [1440, 1280, 1024, 768, 430, 390, 320]) {
  test(`Contract overview reflows at ${width}px`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 960 });
    await page.goto("/contract-mobilization/contracts/ui-contract");
    await expect(page.getByRole("heading", { name: "What needs attention" })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
    const result = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze();
    expect(result.violations.map(item => ({ id: item.id, nodes: item.nodes.map(node => node.target) }))).toEqual([]);
    await page.screenshot({ path: testInfo.outputPath(`contract-${width}.png`), fullPage: true });
  });
}
