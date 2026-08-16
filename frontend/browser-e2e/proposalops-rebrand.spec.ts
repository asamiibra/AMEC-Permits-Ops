import { expect, test } from "@playwright/test";

const retiredVisibleTerms = /About PermitOps|Permit Preparer|My Work|\bPermits\b/;

test.describe("ProposalOps / AMEC final rebrand", () => {
  test("Owner shell exposes the canonical navigation and persona selector", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle("ProposalOps · Proposal & Contract Workflow");
    await expect(page.getByRole("button", { name: "Home", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Contract & Mobilization", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Operating Guide", exact: true })).toBeVisible();
    await expect(page.locator("nav")).not.toContainText("AMEC Work");
    await expect(page.locator("nav")).not.toContainText("Issues");
    await expect(page.locator("nav")).not.toContainText("Notifications");
    await expect(page.getByLabel("Persona")).toHaveValue("SYSTEM_ADMIN");
    await expect(page.getByLabel("Persona").locator("option").filter({ hasText: "Owner" })).toHaveCount(1);
    await expect(page.getByLabel("Persona").locator("option").filter({ hasText: "Engineering" })).toHaveCount(1);
    await expect(page.getByLabel("Persona").locator("option").filter({ hasText: "Business Development" })).toHaveCount(1);
    await expect(page.locator("body")).not.toContainText(retiredVisibleTerms);
  });

  test("Regulatory route remains a canonical business-flow entry point", async ({ page }) => {
    await page.goto("/permits");
    await expect(page).toHaveURL(/\/permits$/);
    await expect(page.getByRole("button", { name: "Regulatory & Submissions", exact: true })).toBeVisible();
  });

  test("Operating Guide retains the only bilingual surface", async ({ page }) => {
    await page.goto("/operating-guide");
    await expect(page.locator("main.about-page")).toHaveAttribute("lang", "en");
    await expect(page.locator("main.about-page")).toContainText("ProposalOps");
    await expect(page.locator("main.about-page")).toContainText("Owner");
    await expect(page.locator("main.about-page")).toContainText("Business Development");
    await expect(page.locator("main.about-page")).toContainText("Engineering");
    await expect(page.locator("body")).not.toContainText(retiredVisibleTerms);
    await page.getByRole("button", { name: "العربي" }).click();
    await expect(page.locator("main.about-page")).toHaveAttribute("lang", "ar-EG");
    await expect(page.locator("main.about-page")).toHaveAttribute("dir", "rtl");
  });
});
