import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

async function waitForContractRef(page: import("@playwright/test").Page, contractRef: string) {
  await expect.poll(async () => {
    const response = await page.request.get("/api/admin/contracts?filter=ALL");
    if (!response.ok()) return [];
    const body = await response.json();
    return (body.items || []).map((item: { contract_ref?: string }) => item.contract_ref);
  }, { timeout: 45_000 }).toContain(contractRef);
}

test.describe("Contract Center final Owner hardening", () => {
  test.describe.configure({ timeout: 90_000 });

  test("opens the Proposal-derived golden Contract with truthful gates and ordered sections", async ({ page }) => {
    await waitForContractRef(page, "SYN-CTR-0007");
    await page.goto("/contract-mobilization");
    await expect(page.getByRole("heading", { name: "Contracts", level: 3 })).toBeVisible({ timeout: 45_000 });
    const goldenRow = page.locator(".admin-owner-row").filter({ hasText: "SYN-CTR-0007" });
    await expect(goldenRow).toBeVisible({ timeout: 45_000 });
    await goldenRow.getByRole("button", { name: "Open", exact: true }).click();
    await expect(page).toHaveURL(/\/contract-mobilization\/contracts\//);
    await expect(page.getByRole("heading", { name: "Accepted Proposal" })).toBeVisible({ timeout: 45_000 });
    await expect(page.locator("#proposal-origin").getByText("SYN-OPP-0007", { exact: false })).toBeVisible();
    await expect(page.locator("#proposal-origin")).toContainText("Synthetic Engineering Advisory Proposal");
    await expect(page.getByText("Requirement not configured", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("NEEDED", { exact: true })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Accept Contract", exact: true })).toBeEnabled();
    await expect(page.getByRole("textbox", { name: "Project Code" })).toBeDisabled();
    await expect(page.getByRole("button", { name: "Activate Project", exact: true })).toBeDisabled();
    await expect(page.getByText("Locked until Contract acceptance", { exact: true })).toBeVisible();
    await expect(page.locator("#billing")).toBeVisible();
    await expect(page.locator("#activation").evaluate((node) => Boolean(node.compareDocumentPosition(document.querySelector("#billing")!) & Node.DOCUMENT_POSITION_FOLLOWING))).toBeTruthy();
    await expect(page.locator(".contract-section-nav")).toHaveCSS("position", "sticky");
    await expect(page.locator('.contract-section-nav a[href="#overview"]')).toHaveAttribute("href", "#overview");
    await expect(page.getByRole("button", { name: "+ Add Payment Term", exact: true })).toBeVisible();
    await expect(page.getByRole("textbox", { name: "Payment Term name" })).toHaveCount(0);
  });

  test("keeps the legacy Contract safe and separate", async ({ page }) => {
    await waitForContractRef(page, "SYN-CTR-0001");
    await page.goto("/contract-mobilization");
    await expect(page.getByRole("heading", { name: "Contracts", level: 3 })).toBeVisible({ timeout: 45_000 });
    const legacyRow = page.locator(".admin-owner-row").filter({ hasText: "SYN-CTR-0001" });
    await expect(legacyRow).toBeVisible({ timeout: 45_000 });
    await legacyRow.getByRole("button", { name: "Open", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Legacy Contract" })).toBeVisible({ timeout: 45_000 });
    await expect(page.locator("#proposal-origin").getByText("Proposal origin requires reconciliation", { exact: true })).toBeVisible();
    await expect(page.locator("#commercial")).toContainText("Project Description");
    await expect(page.locator("#commercial")).not.toContainText("origin unresolved");
    await expect(page.getByRole("button", { name: "Accept Contract", exact: true })).toBeDisabled();
  });

  test("converges the historical Contract detail route on the canonical workspace", async ({ page }) => {
    await waitForContractRef(page, "SYN-CTR-0007");
    const response = await page.request.get("/api/admin/contracts?filter=ALL");
    const body = await response.json();
    const contractId = (body.items || []).find((item: { contract_ref?: string }) => item.contract_ref === "SYN-CTR-0007")?.id;
    expect(contractId).toBeTruthy();
    await page.goto(`/contracts/${contractId}`);
    await expect(page).toHaveURL(new RegExp(`/contract-mobilization/contracts/${contractId}$`));
    await expect(page.getByRole("heading", { name: "Assistance rail", exact: true })).toBeVisible({ timeout: 45_000 });
  });

  test("keeps the canonical workspace accessible and usable on mobile", async ({ page }) => {
    await waitForContractRef(page, "SYN-CTR-0007");
    const response = await page.request.get("/api/admin/contracts?filter=ALL");
    const body = await response.json();
    const contractId = (body.items || []).find((item: { contract_ref?: string }) => item.contract_ref === "SYN-CTR-0007")?.id;
    expect(contractId).toBeTruthy();
    await page.goto(`/contract-mobilization/contracts/${contractId}`);
    await expect(page.getByRole("heading", { name: "Assistance rail", exact: true })).toBeVisible({ timeout: 45_000 });
    await expect(page.getByRole("tablist", { name: "Contract workspace sections" })).toBeVisible();
    await expect(page.getByRole("tab")).toHaveCount(8);
    const axe = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
    expect(axe.violations.filter((item) => ["serious", "critical"].includes(item.impact || ""))).toEqual([]);

    await page.setViewportSize({ width: 390, height: 844 });
    await page.reload();
    await expect(page.getByRole("heading", { name: "Assistance rail", exact: true })).toBeVisible({ timeout: 45_000 });
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBeTruthy();
    await page.locator(".contract-section-nav button").first().focus();
    await expect(page.locator(":focus")).toBeVisible();
  });
});
