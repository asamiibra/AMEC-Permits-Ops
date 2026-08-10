import { expect, test } from "@playwright/test";

test.describe("owner-directed proposals and contracts main page", () => {
  test("owner sees orange manual actions and blue derived KPI filters", async ({ page }) => {
    await page.goto("/proposals-contracts");
    await expect(page.getByRole("heading", { name: "Proposals & Contracts", level: 2 })).toBeVisible();
    await expect(page.getByRole("button", { name: "Client List" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Proposal Form" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Contract Form" })).toBeVisible();
    await expect(page.locator("button.proposal-new-button")).toBeVisible();
    for (const label of ["Open Proposals", "Open Contracts", "Proposal Handover", "Contract Handover", "Proposals In Process", "Contracts In Process"]) {
      await expect(page.getByRole("button", { name: new RegExp(label) })).toBeVisible();
    }
    await page.getByRole("button", { name: "Open Proposals" }).click();
    await expect(page.getByRole("button", { name: "Open Proposals" })).toHaveClass(/selected/);
    await expect(page.getByRole("columnheader", { name: "Proposal Description" })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Project Ref." })).toBeVisible();
  });

  test("orange upload drawer requires project and manually selected file", async ({ page }) => {
    await page.goto("/proposals-contracts");
    await page.getByRole("button", { name: "Client List" }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await expect(page.getByText("HUMAN INPUT / UPLOAD")).toBeVisible();
    await page.getByRole("button", { name: "Save Client Source" }).click();
    await expect(page.getByText("Select an existing client master context before upload.")).toBeVisible();
    const projectSelect = page.getByRole("dialog").locator("select").first();
    await expect(projectSelect).toBeVisible();
    await projectSelect.selectOption({ index: 1 });
    await page.getByRole("button", { name: "Save Client Source" }).click();
    await expect(page.getByText("Select the source file before upload.", { exact: true })).toBeVisible();
  });

  test("engineering sees proposal-form input only and no commercial amount column", async ({ page }) => {
    await page.goto("/proposals-contracts");
    await page.evaluate(() => sessionStorage.setItem("proposalops-role", "RESPONSIBLE_ENGINEER"));
    await page.reload();
    await expect(page.getByRole("button", { name: "Proposal Form" })).toBeVisible();
    await expect(page.locator("button.proposal-new-button")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Client List" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Contract Form" })).toHaveCount(0);
    await expect(page.getByRole("columnheader", { name: "Amount" })).toHaveCount(0);
  });

  test("material detail routes render their exact business context and survive direct navigation", async ({ page }) => {
    await page.goto("/proposals-contracts");
    const register = await page.evaluate(async () => (await fetch("/api/proposals-main?persona=SYSTEM_ADMIN")).json());
    const proposalId = register.rows[0].id;
    const contractId = register.contract_rows[0].id;
    await page.goto("/proposals/new");
    await expect(page.getByRole("heading", { name: "New Proposal", level: 2 })).toBeVisible();
    await expect(page.getByRole("heading", { name: "1. Proposal details", level: 3 })).toBeVisible();
    await expect(page.getByRole("button", { name: "Create Proposal & Save Sources" })).toBeVisible();
    await page.goto(`/proposals/${proposalId}`);
    await expect(page.getByText("PROPOSAL DETAIL", { exact: false })).toBeVisible();
    await expect(page.getByText("Source evidence", { exact: true })).toBeVisible();
    await page.reload();
    await expect(page.getByText("PROPOSAL DETAIL", { exact: false })).toBeVisible();
    await page.goto(`/proposals/${proposalId}/preparation`);
    await expect(page.getByRole("heading", { name: "Proposal Preparation", level: 3 })).toBeVisible();
    await page.goto(`/contracts/${contractId}`);
    await expect(page.getByText("CONTRACT DETAIL", { exact: false })).toBeVisible();
    await expect(page.getByText("Contract Form / revisions", { exact: true })).toBeVisible();
    await page.goto("/proposals/does-not-exist");
    await expect(page.getByRole("heading", { name: "Proposal not found" })).toBeVisible();
    await page.goto("/contracts/does-not-exist");
    await expect(page.getByRole("heading", { name: "Contract not found" })).toBeVisible();
  });
});
