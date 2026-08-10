import { expect, test } from "@playwright/test";

test("Proposal and Contract routes preserve backend identity and lineage", async ({ page }) => {
  await page.goto("/proposals-contracts");
  const register = await page.evaluate(async () => (await (await fetch("/api/proposals-main")).json()));
  const proposal = register.rows.find((item: any) => item.has_contract) || register.rows[0];
  const contract = register.contract_rows[0];

  await page.getByRole("button", { name: proposal.proposal_description }).first().click();
  await expect(page).toHaveURL(new RegExp(`/proposals/${proposal.id}$`));
  await expect(page.getByText(/PROPOSAL DETAIL/)).toBeVisible();
  await page.goto("/proposals-contracts");

  await page.goto(`/proposals/${proposal.id}/preparation`);
  await expect(page.getByText("ENGINEERING-OWNED WORKSPACE", { exact: true })).toBeVisible();

  await page.goto(`/proposals/${proposal.id}`);
  await expect(page.getByText(/PROPOSAL DETAIL/)).toBeVisible();
  await expect(page.getByText("Source evidence", { exact: true })).toBeVisible();
  await expect(page.getByText(String(proposal.source_count), { exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByText(/PROPOSAL DETAIL/)).toBeVisible();

  await page.goto("/proposals-contracts");
  await page.getByRole("button", { name: proposal.proposal_description }).first().click();
  await expect(page).toHaveURL(new RegExp(`/proposals/${proposal.id}$`));

  await page.goto(`/contracts/${contract.id}`);
  await expect(page.getByText(/CONTRACT DETAIL/)).toBeVisible();
  await expect(page.getByText(contract.contract_reference, { exact: true })).toBeVisible();
  await expect(page.getByText("Related Proposal", { exact: true }).first()).toBeVisible();
  await page.getByRole("button", { name: proposal.proposal_description }).first().click();
  await expect(page).toHaveURL(new RegExp(`/proposals/${proposal.id}$`));
});

test("contextual source cards expose controlled validation", async ({ page }) => {
  await page.goto("/proposals-contracts");
  await expect(page.getByRole("heading", { name: "Proposals & Contracts", level: 2 })).toBeVisible();
  await page.getByRole("button", { name: /Client List/ }).click();
  await expect(page.getByRole("heading", { name: "Client List", level: 3 })).toBeVisible();
  await page.getByRole("button", { name: "Save Client Source" }).click();
  await expect(page.getByText(/Select an existing client master context before upload\./)).toBeVisible();
});
