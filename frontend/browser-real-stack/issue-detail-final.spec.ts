import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("Issue list, detail, and Work share one canonical resolution path", async ({ page }) => {
  const issues = await page.request.get("http://127.0.0.1:8000/api/issues?persona=OWNER");
  expect(issues.ok()).toBeTruthy();
  const rows = (await issues.json()).issues;
  expect(rows.length).toBeGreaterThanOrEqual(4);
  expect(new Set(rows.map((row: any) => row.display_domain))).toEqual(new Set(["PROPOSAL", "CONTRACT", "PERMIT", "SYSTEM / DATA"]));
  for (const row of rows) {
    await page.goto(`/issues/${row.id}`);
    await expect(page.getByRole("heading", { name: row.title })).toBeVisible();
    await expect(page.getByRole("heading", { name: "What is wrong" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Why it matters" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "What needs to happen" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Evidence" })).toBeVisible();
    await expect(page.getByText(/quotation|open work/i)).toHaveCount(0);
    await expect(page.getByRole("link", { name: /Back to Issues/ })).toBeVisible();
  }
  const work = await page.request.get("http://127.0.0.1:8000/api/work");
  expect(work.ok()).toBeTruthy();
  const issueWork = (await work.json()).items.filter((item: any) => item.issue_id);
  expect(issueWork.length).toBeGreaterThan(0);
  await page.goto(issueWork[0].deep_link);
  await expect(page.getByRole("heading", { name: /What is wrong/ })).toBeVisible();
  await page.goto("/issues");
  const ownerIssue = page.locator(".persona-row").first();
  await ownerIssue.getByRole("link", { name: /Open Issue/ }).click();
  await expect(page.getByRole("link", { name: /Back to Issues/ })).toBeVisible();
  await page.goBack();
  await expect(page.getByRole("heading", { name: /Issues across AMEC work/ })).toBeVisible();
  await page.goForward();
  await expect(page.getByRole("heading", { name: /What is wrong/ })).toBeVisible();
});

test("Issue detail is role-aware, domain-relevant, accessible, and mobile-safe", async ({ page }) => {
  const response = await page.request.get("http://127.0.0.1:8000/api/issues?persona=OWNER");
  const rows = (await response.json()).issues;
  const proposal = rows.find((row: any) => row.display_domain === "PROPOSAL");
  expect(proposal).toBeTruthy();
  await page.goto(`/issues/${proposal.id}`);
  await expect(page.getByText("PROPOSAL", { exact: true }).first()).toBeVisible();
  const drawer = page.getByRole("button", { name: /Readiness|Go-live/ }).first();
  if (await drawer.count()) {
    await drawer.click();
    await expect(page.getByText(/Issue Detail/).first()).toBeVisible();
    await expect(page.getByText(/Permit type and first project/)).toHaveCount(0);
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload();
  await expect(page.getByRole("heading", { name: proposal.title })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBeTruthy();
  const axe = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
  expect(axe.violations.filter((item) => ["critical", "serious"].includes(item.impact || ""))).toEqual([]);
});
