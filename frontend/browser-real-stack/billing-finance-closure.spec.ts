import { expect, test } from "@playwright/test";

const owner = { "X-Dev-Role": "OWNER_SPONSOR" };

test("Billing closure detail routes render their own workspace", async ({ page }) => {
  const projects = await page.request.get("/api/projects", { headers: owner });
  expect(projects.ok()).toBeTruthy();
  const project = (await projects.json())[0];
  expect(project?.id).toBeTruthy();

  await page.goto(`/billing/projects/${project.id}`);
  await expect(page.getByRole("heading", { name: "PROJECT FINANCE WORKSPACE" })).toHaveCount(0);
  await expect(page.getByText("PROJECT FINANCE WORKSPACE")).toBeVisible();
  await expect(page.getByRole("heading", { name: /Milestone financial ledger/ })).toBeVisible();
  await expect(page.getByText("Billing completion", { exact: true })).toBeVisible();
  await expect(page.getByText("Financial completion", { exact: true })).toBeVisible();
});

test("Billing detail paths fail in their own loader instead of falling back to registers", async ({ page }) => {
  await page.goto("/billing/plans/closure-route-probe");
  await expect(page.getByText("Billing Plan unavailable")).toBeVisible();
  await expect(page.getByText("Billing Plans", { exact: true })).toHaveCount(0);

  await page.goto("/billing/payments/closure-route-probe");
  await expect(page.getByText("Payment unavailable")).toBeVisible();
  await expect(page.getByText("Payments & Credits", { exact: true })).toHaveCount(0);
});
