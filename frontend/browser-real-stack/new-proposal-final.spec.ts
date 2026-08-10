import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("Business Development can create one source-driven New Proposal and refresh its detail", async ({ page }) => {
  await page.addInitScript(() => sessionStorage.setItem("proposalops-role", "COMMERCIAL_APPROVER"));
  await page.goto("/proposals/new");
  await expect(page.getByRole("heading", { name: "New Proposal", level: 2 })).toBeVisible();
  await expect(page.getByRole("heading", { name: "1. Proposal details", level: 3 })).toBeVisible();
  await expect(page.getByRole("button", { name: "Create Proposal & Save Sources" })).toBeVisible();
  await page.getByLabel("Proposal Description").fill("BD browser New Proposal source-driven proof");
  await page.locator("input[type=file]").nth(1).setInputFiles({ name: "bd-tender-document.txt", mimeType: "text/plain", buffer: Buffer.from("Tender document evidence") });
  await page.getByRole("button", { name: "Create Proposal & Save Sources" }).click();
  await expect(page).toHaveURL(/\/proposals\/[^/]+$/);
  await expect(page.getByText("PROPOSAL DETAIL", { exact: false })).toBeVisible();
  await expect(page.getByText("TENDER DOCUMENT SOURCE", { exact: false })).toBeVisible();
  await expect(page.getByText("READ_BACK_VERIFIED", { exact: false })).toBeVisible();
  await page.reload();
  await expect(page.getByText("PROPOSAL DETAIL", { exact: false })).toBeVisible();
  await expect(page.getByText(/Sources\s+\d+/)).toBeVisible();
});

test("Engineering gets a controlled New Proposal access state and typed API denial", async ({ page }) => {
  await page.addInitScript(() => sessionStorage.setItem("proposalops-role", "RESPONSIBLE_ENGINEER"));
  await page.goto("/proposals/new");
  await expect(page.getByText("New Proposal intake is handled by Business Development.", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Back to Proposals & Contracts" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Create Proposal & Save Sources" })).toHaveCount(0);
  await expect(page.getByText("ENGINEERING_NEW_PROPOSAL_BLANK_PAGE_ZERO", { exact: true })).toHaveCount(0);
  const denied = await page.evaluate(async () => {
    const form = new FormData();
    form.append("action", "TENDER_DOCUMENT");
    form.append("proposal_description", "Denied Engineering intake");
    form.append("create_new_proposal", "true");
    form.append("file", new Blob(["source"], { type: "text/plain" }), "engineering-denied.txt");
    const response = await fetch("/api/proposals-main/intake", { method: "POST", headers: { "X-Dev-Role": "RESPONSIBLE_ENGINEER" }, body: form });
    return { status: response.status, body: await response.json() };
  });
  expect(denied.status).toBe(403);
  expect(denied.body.detail.code).toBe("CAPABILITY_DENIED");
});

test("New Proposal source cards preserve intent and the readiness drawer is route-aware", async ({ page }) => {
  await page.addInitScript(() => sessionStorage.setItem("proposalops-role", "COMMERCIAL_APPROVER"));
  for (const label of ["Tender Email", "Tender Document", "Tender Photo / Image", "Client Information"]) {
    await page.goto("/proposals-contracts");
    await page.getByRole("button", { name: new RegExp(`^${label}`) }).click();
    await expect(page.getByRole("heading", { name: `New Proposal from ${label}`, level: 3 })).toBeVisible();
    await expect(page.getByText(`Selected source · ${label}`, { exact: true })).toBeVisible();
    await page.getByRole("dialog").getByRole("button", { name: "Close", exact: true }).first().click();
  }
  await page.goto("/proposals/new");
  await page.getByRole("button", { name: "Inputs & Go-Live" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByRole("dialog").getByRole("heading", { name: "New Proposal", level: 2 })).toBeVisible();
  await expect(page.getByText("Start a Proposal from tender/client information and establish the controlled intake record before or alongside final Project setup.", { exact: true })).toBeVisible();
  await expect(page.getByText("Tender / RFQ source evidence", { exact: true })).toBeVisible();
  await expect(page.getByText("Municipality application reference", { exact: true })).toHaveCount(0);
  await expect(page.getByText("Permit type and first project", { exact: true })).toHaveCount(0);
  await expect(page.getByText(/Demo ready · \d+ go-live inputs remaining/)).toBeVisible();
  await expect(page.getByText(/NO PORTAL WRITES|HUMAN SUBMISSION REQUIRED/)).toHaveCount(0);
});

test("Owner capability truth, accessibility, and mobile layout hold on New Proposal", async ({ page }) => {
  await page.addInitScript(() => sessionStorage.setItem("proposalops-role", "SYSTEM_ADMIN"));
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/proposals/new");
  await expect(page.getByRole("heading", { name: "New Proposal", level: 2 })).toBeVisible();
  await expect(page.getByRole("button", { name: "Create Proposal & Save Sources" })).toBeVisible();
  const horizontalOverflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
  expect(horizontalOverflow).toBe(false);
  const axe = await new AxeBuilder({ page }).analyze();
  expect(axe.violations).toEqual([]);
});
