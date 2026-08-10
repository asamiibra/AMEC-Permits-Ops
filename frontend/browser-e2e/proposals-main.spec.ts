import { expect, test } from "@playwright/test";

test.describe("ProposalOps Proposals and Contracts registers", () => {
  test("owner sees the three manual controls, shared KPI strip, and proposal register", async ({ page }) => {
    await page.goto("/proposals-contracts?view=proposals");
    await expect(page.getByRole("heading", { name: "Proposals & Contracts", level: 2 })).toBeVisible();
    for (const label of ["Client List", "Proposal Form", "Contract Form", "Open Proposals", "Open Contracts", "Proposal Handover", "Contract Handover", "Proposals In Process", "Contracts In Process"]) await expect(page.getByRole("button", { name: new RegExp(label) })).toBeVisible();
    await expect(page.getByRole("tab", { name: "Proposals" })).toHaveAttribute("aria-selected", "true");
    for (const label of ["Proposal / Proposal Description", "Project Ref.", "Stage / Status", "Amount", "Last Activity", "Actions", "Contract"]) await expect(page.getByRole("columnheader", { name: label })).toBeVisible();
  });

  test("contract tab is a separate stable register with related proposal and permit action", async ({ page }) => {
    await page.goto("/proposals-contracts?view=proposals");
    await page.getByRole("tab", { name: "Contracts" }).click();
    await expect(page).toHaveURL(/\/proposals-contracts\?view=contracts/);
    await expect(page.getByRole("tab", { name: "Contracts" })).toHaveAttribute("aria-selected", "true");
    for (const label of ["Contract Description", "Contract Reference", "Related Proposal", "Amount", "Last Activity", "End Date", "Actions", "Permit"]) await expect(page.getByRole("columnheader", { name: label })).toBeVisible();
    await expect(page.getByRole("button", { name: /Permit|Open Permit/ }).first()).toBeVisible();
  });

  test("manual upload drawer requires a project and manually selected file", async ({ page }) => {
    await page.goto("/proposals-contracts");
    await page.getByRole("button", { name: "Client List" }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await page.getByRole("button", { name: "Upload to Project Record" }).click();
    await expect(page.getByText("Select a project before upload.", { exact: true })).toBeVisible();
    await page.getByRole("dialog").locator("select").first().selectOption({ index: 1 });
    await page.getByRole("button", { name: "Upload to Project Record" }).click();
    await expect(page.getByText("Manual file selection is required.", { exact: true })).toBeVisible();
  });

  test("commercial collection root redirects while nested Permit Workspace remains available", async ({ page }) => {
    const register = await page.request.get("http://127.0.0.1:8000/api/proposals-main?persona=SYSTEM_ADMIN").then((response) => response.json());
    const projectId = register.rows[0].project_id;
    await page.goto("/permits");
    await expect(page).toHaveURL(/\/proposals-contracts\?view=proposals/);
    await page.goto(`/permits/${projectId}/project-and-sources`);
    await expect(page).toHaveURL(new RegExp(`/permits/${projectId}/project-and-sources`));
    await expect(page.getByText(/Permit Workspace|Permit Application|Project & Sources/).first()).toBeVisible();
  });

  test("proposal and contract detail routes preserve current lineage", async ({ page }) => {
    const register = await page.request.get("/api/proposals-main?persona=SYSTEM_ADMIN&view=proposals").then((response) => response.json());
    const proposal = register.proposals?.[0] || register.rows?.[0];
    const contracts = await page.request.get("/api/proposals-main?persona=SYSTEM_ADMIN&view=contracts").then((response) => response.json());
    const contract = contracts.contracts?.[0] || contracts.rows?.[0];
    expect(proposal?.id).toBeTruthy();
    expect(contract?.id).toBeTruthy();
    await page.goto(`/proposals/${proposal.id}`);
    await expect(page.getByText(/PROPOSAL DETAIL/)).toBeVisible();
    await expect(page.getByText("Source evidence", { exact: true })).toBeVisible();
    await page.goto(`/contracts/${contract.id}`);
    await expect(page.getByText(/CONTRACT DETAIL/)).toBeVisible();
    await expect(page.getByText("Related Proposal", { exact: true }).first()).toBeVisible();
  });
});
