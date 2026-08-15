import { expect, test } from "@playwright/test";

test("BD Proposal Forms-Driven v2 exposes the governed owner workspace", async ({ page, request }) => {
  const owner = { "X-Dev-Role": "SYSTEM_ADMIN" };
  await page.addInitScript(() => sessionStorage.setItem("proposalops-role", "SYSTEM_ADMIN"));
  const health = await request.get("/health");
  expect(health.ok()).toBeTruthy();
  const healthBody = await health.json();
  expect(healthBody.database_dialect).toBe("postgresql");
  expect(healthBody.alembic_versions).toContain("0054_bd_proposal_stage1_reconciliation");

  let proposals = await request.get("/api/bd/proposals", { headers: owner });
  expect(proposals.ok()).toBeTruthy();
  let proposalBody = await proposals.json();
  if (!proposalBody.items?.length) {
    const created = await request.post("/api/bd/proposals", {
      headers: { ...owner, "Content-Type": "application/json" },
      data: {
        proposal_description: "Synthetic BD Forms-Driven v2 browser proposal",
        project_reference: "BD-V2-BROWSER-001",
        client_name: "Synthetic Browser Client",
      },
    });
    expect(created.ok()).toBeTruthy();
    proposals = await request.get("/api/bd/proposals", { headers: owner });
    proposalBody = await proposals.json();
  }
  expect(proposalBody.items?.length).toBeGreaterThan(0);

  await page.goto("/bd/proposals");
  await expect(page.getByRole("heading", { name: "Proposal Intake", level: 2 })).toBeVisible();
  await page.getByRole("button", { name: /Open Proposal/ }).first().click();
  await expect(page.getByText("CLIENT & CONTACTS")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Site / Property context", level: 3 })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Known / Candidate Stakeholders", level: 3 })).toBeVisible();
  await expect(page.getByText("REGULATORY SCOPING · COMMERCIAL PLANNING")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Expected Client Inputs — Preliminary", level: 3 })).toBeVisible();
  await expect(page.getByText("No canonical Property has been fabricated from free text.")).toBeVisible();
  await page.screenshot({ path: "../artifacts/bd-proposal-forms-driven-v2/proposal-workspace.png", fullPage: true });
});
