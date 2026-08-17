import { expect, test } from "@playwright/test";

test.describe.configure({ mode: "serial" });

test("Owner Contract detail exposes the six owner-sketch delta surfaces", async ({ page }) => {
  await page.addInitScript(() => sessionStorage.setItem("proposalops-role", "OWNER_SPONSOR"));
  const apiBase = process.env.API_BASE_URL || process.env.BASE_URL || "";
  const response = await page.request.get(`${apiBase}/api/admin/contracts`, { headers: { "X-Dev-Role": "OWNER_SPONSOR" } });
  expect(response.ok()).toBeTruthy();
  const contracts = await response.json();
  const contract = contracts.items?.[0];
  expect(contract?.id).toBeTruthy();
  await page.goto(`/admin/contracts/${contract.id}`);
  await expect(page.getByRole("heading", { name: /SYN-CTR-|Contract/, level: 3 }).first()).toBeVisible();
  for (const label of ["Client Document", "LPO", "Client Name", "Client Company", "CR No.", "Mobile No.", "PIN No.", "Client Email", "Project Description", "Client Inputs & Documents Needed", "Deliverables / Contracted Works", "Contract Documents & Sources", "Accept Contract", "Project Activation", "Finance summary"]) {
    await expect(page.getByText(label, { exact: true }).first()).toBeVisible();
  }
  await expect(page.getByText("Owner definition required", { exact: false })).toBeVisible();
  await expect(page.getByRole("button", { name: "Accept Contract", exact: true })).toHaveCount(1);
  await expect(page.getByRole("button", { name: "Activate Project", exact: true })).toBeDisabled();
  await expect(page.locator("body")).not.toContainText(/CONTRACT WORKBENCH|Mark Ready \/ Close|Authority policy and readiness seam|IMPLEMENTATION_DEFERRED|BLOCKED_EXTERNAL|OWNER_REVIEW_REQUIRED/);
});

test("Owner Contract detail remains usable at narrow width", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const apiBase = process.env.API_BASE_URL || process.env.BASE_URL || "";
  const response = await page.request.get(`${apiBase}/api/admin/contracts`, { headers: { "X-Dev-Role": "OWNER_SPONSOR" } });
  const contracts = await response.json();
  await page.goto(`/admin/contracts/${contracts.items?.[0]?.id}`);
  await expect(page.getByRole("heading", { name: /SYN-CTR-|Contract/, level: 3 }).first()).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)).toBeFalsy();
});
