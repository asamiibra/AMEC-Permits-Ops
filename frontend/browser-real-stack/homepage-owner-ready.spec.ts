import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("Owner AMEC Work is one canonical business worklist", async ({ page }) => {
  const requested: string[] = [];
  page.on("request", (request) => requested.push(new URL(request.url()).pathname));
  await page.goto("/work");
  await expect(page.getByRole("heading", { name: "What needs attention", level: 2 })).toBeVisible();
  await expect(page.getByText("One prioritized worklist across proposals, contracts, permits, and handoffs.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Needs Action" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Waiting for Review" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Blocked" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Overdue" })).toBeVisible();
  await expect(page.locator(".amec-work-kpi")).toHaveCount(4);
  await expect(page.locator("body")).not.toContainText(/E7|shared persona|all personas|all owner roles|HUMAN_SEND|MISSING_DOCUMENT/);
  await expect(page.locator("body")).not.toContainText(/WorkProjectionService|WorkflowTask|REVIEW_ISSUE|Open work|System \/ Other|quotation|quote/i);
  await expect(page.getByText("Review source integrity conflict")).toBeVisible();
  await expect(page.getByText("PROPOSAL • CONTRACT • PERMIT", { exact: true })).toBeVisible();
  expect(requested).not.toContain("/api/reconciliation/governance");
  await expect(page.getByText("Review missing-document email")).toBeVisible();
});

test("Owner filters compose with KPI and domain filters", async ({ page }) => {
  await page.goto("/work");
  await page.getByLabel("Team").selectOption("engineering");
  await page.getByRole("button", { name: "Waiting for Review" }).click();
  await expect(page).toHaveURL(/team=engineering/);
  await expect(page).toHaveURL(/kpi=waiting_review/);
  await page.getByLabel("Work", { exact: true }).selectOption("permit");
  await expect(page).toHaveURL(/domain=permit/);
  await expect(page.locator(".amec-work-card")).toHaveCount(0);
});

test("Business Development and Engineering receive scoped work without team impersonation", async ({ page }) => {
  await page.goto("/work");
  await page.getByLabel("Persona").selectOption("COMMERCIAL_APPROVER");
  await expect(page.getByLabel("Team")).toHaveCount(0);
  await expect(page.getByText("Review missing-document email")).toBeVisible();
  await page.getByLabel("Persona").selectOption("RESPONSIBLE_ENGINEER");
  await expect(page.getByLabel("Team")).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Confirm project & sources", level: 4 }).first()).toBeVisible();
});

test("AMEC Work remains readable on mobile", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/work");
  await expect(page.getByRole("heading", { name: "What needs attention", level: 2 })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)).toBeFalsy();
});

test("AMEC Work shows a controlled error and recovers without a fake empty state", async ({ page }) => {
  let fail = true;
  await page.route("**/api/work**", async (route) => {
    if (fail) return route.abort("failed");
    return route.continue();
  });
  await page.goto("/work");
  await expect(page.getByRole("alert")).toContainText("Some work data could not be loaded");
  await expect(page.getByRole("button", { name: "Retry" })).toBeVisible();
  await expect(page.getByText("You're caught up")).toHaveCount(0);
  fail = false;
  await page.getByRole("button", { name: "Retry" }).click();
  await expect(page.getByText("Review missing-document email")).toBeVisible();
  await page.unroute("**/api/work**");
});

test("AMEC Work has one summary row and no legacy duplicate dashboard", async ({ page }) => {
  await page.goto("/work");
  await expect(page.locator(".amec-work-kpi")).toHaveCount(4);
  await expect(page.getByText("Action required", { exact: true })).toHaveCount(0);
  await expect(page.getByText("Reviews waiting", { exact: true })).toHaveCount(0);
  await expect(page.getByText(/highest-impact permit|blocked permits|Delivery evidence/i)).toHaveCount(0);
});

test("AMEC Work has no critical or serious accessibility violations", async ({ page }) => {
  await page.goto("/work");
  const result = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
  expect(result.violations.filter((item) => ["critical", "serious"].includes(item.impact || ""))).toEqual([]);
});
