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
  await expect(page.getByRole("heading", { name: "Contract inputs, source lineage, and acceptance", level: 3 })).toBeVisible();
  for (const label of ["Client Document", "LPO", "Client Name", "Client Company", "CR No.", "Mobile No.", "PIN No.", "Client Email", "Project Description", "Documents Needed", "Deliverables", "Contract Documents & Sources", "Accept Contract", "Explicit Project Activation"]) {
    await expect(page.getByText(label, { exact: true }).first()).toBeVisible();
  }
  await expect(page.getByText("Owner definition required", { exact: false })).toBeVisible();
});

test("Owner Contract detail remains usable at narrow width", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const apiBase = process.env.API_BASE_URL || process.env.BASE_URL || "";
  const response = await page.request.get(`${apiBase}/api/admin/contracts`, { headers: { "X-Dev-Role": "OWNER_SPONSOR" } });
  const contracts = await response.json();
  await page.goto(`/admin/contracts/${contracts.items?.[0]?.id}`);
  await expect(page.getByRole("heading", { name: "Contract inputs, source lineage, and acceptance", level: 3 })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)).toBeFalsy();
});
