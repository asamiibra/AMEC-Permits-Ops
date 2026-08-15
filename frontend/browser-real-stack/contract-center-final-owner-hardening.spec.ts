import { test, expect } from "@playwright/test";

test.describe("Contract Center final Owner hardening", () => {
  test("opens the Proposal-derived golden Contract with truthful gates and ordered sections", async ({ page }) => {
    await page.goto("/admin/contracts");
    const goldenRow = page.locator(".admin-owner-row").filter({ hasText: "SYN-CTR-0007" });
    await expect(goldenRow).toBeVisible();
    await goldenRow.getByRole("button", { name: "Open →" }).click();
    await expect(page).toHaveURL(/\/admin\/contracts\//);
    await expect(page.getByRole("heading", { name: "Accepted Proposal" })).toBeVisible();
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
    await page.goto("/admin/contracts");
    const legacyRow = page.locator(".admin-owner-row").filter({ hasText: "SYN-CTR-0001" });
    await expect(legacyRow).toBeVisible();
    await legacyRow.getByRole("button", { name: "Open →" }).click();
    await expect(page.getByRole("heading", { name: "Legacy Contract" })).toBeVisible();
    await expect(page.locator("#proposal-origin").getByText("Proposal origin requires reconciliation", { exact: true })).toBeVisible();
    await expect(page.locator("#commercial")).toContainText("Project Description");
    await expect(page.locator("#commercial")).not.toContainText("origin unresolved");
    await expect(page.getByRole("button", { name: "Accept Contract", exact: true })).toBeDisabled();
  });
});
