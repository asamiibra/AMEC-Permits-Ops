import { expect, test } from "@playwright/test";

test("the product shell and Contract register use the live synthetic API", async ({ page, request }) => {
  const health = await request.get("/health");
  expect(health.ok()).toBe(true);
  const healthBody = await health.json();
  expect(healthBody.environment).toBe("TEST");
  expect(healthBody.synthetic_only).toBe(true);

  const contracts = await request.get("/api/admin/contracts?filter=ALL", {
    headers: { "X-Dev-Role": "SYSTEM_ADMIN" },
  });
  expect(contracts.ok()).toBe(true);
  const contractBody = await contracts.json();
  expect(contractBody.items?.length ?? 0).toBeGreaterThan(0);

  await page.goto("/contract-mobilization");
  await expect(page.getByRole("heading", { name: "Contract & Mobilization", level: 2 })).toBeVisible({ timeout: 45_000 });
  await expect(page.getByRole("table")).toBeVisible({ timeout: 45_000 });
  await expect(page.getByText("Synthetic workspace")).toBeVisible({ timeout: 45_000 });

  const firstContractId = contractBody.items[0].id;
  await page.getByRole("button", { name: /Open/ }).first().click();
  await expect(page).toHaveURL(new RegExp(`/contract-mobilization/contracts/${firstContractId}`));
  await expect(page.getByText("CONTRACT WORKSPACE", { exact: true })).toBeVisible({ timeout: 45_000 });
  await page.getByRole("button", { name: "Mobilization & Start" }).click();
  await expect(page).toHaveURL(/#mobilization$/);
  await expect(page.getByRole("heading", { name: "Mobilization", level: 2 })).toBeVisible();

  const bodyText = await page.locator("body").innerText();
  expect(bodyText).not.toMatch(/Traceback|Internal Server Error|<html>/i);
});
