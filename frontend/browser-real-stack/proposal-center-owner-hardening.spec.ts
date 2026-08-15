import { expect, test } from "@playwright/test";

test("Proposal Center Engineering stage is progressive and owner-safe", async ({ page, request }) => {
  const owner = { "X-Dev-Role": "SYSTEM_ADMIN" };
  const proposals = await request.get("/api/bd/proposals?q=SYN-OPP-0002", { headers: owner });
  expect(proposals.ok()).toBeTruthy();
  const body = await proposals.json();
  const golden = body.items.find((item: any) => item.proposal_reference === "SYN-OPP-0002");
  expect(golden).toBeTruthy();
  const detail = await request.get(`/api/bd/proposals/${golden.id}`, { headers: owner });
  expect(detail.ok()).toBeTruthy();
  const payload = await detail.json();
  expect(payload.stage).toBe("PROPOSAL_PREPARATION");
  expect(payload.stage_gate.intake.state).toBe("COMPLETED");

  await page.goto(`/opportunities/${golden.id}`);
  await expect(page.getByRole("link", { name: /Engineering Preparation/ })).toBeVisible();
  await expect(page.locator('[aria-current="step"]')).toContainText("Engineering Preparation");
  await expect(page.getByText("Intake complete", { exact: true })).toBeVisible();
  await expect(page.getByText("Complete intake before Engineering", { exact: true })).toHaveCount(0);
  await expect(page.getByText("Upstream Intake reconciliation required", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "AMEC technical preparation", level: 3 })).toBeVisible();
  await expect(page.getByRole("button", { name: "Save Engineering Preparation" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Record response" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Record outcome" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: /Accept Proposal/ })).toBeDisabled();
  await expect(page.getByText("LEGACY_UNSPECIFIED", { exact: true })).toHaveCount(0);
  await expect(page.getByText("{}", { exact: true })).toHaveCount(0);
  await expect(page.getByText("＋ Add source", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Stakeholders", level: 3 })).toBeVisible();
  await expect(page.getByText("QAR 98,000 QAR", { exact: true })).toHaveCount(0);

  await page.reload();
  await expect(page.locator('[aria-current="step"]')).toContainText("Engineering Preparation");
  await page.screenshot({ path: "../artifacts/proposal-center-final-owner-hardening/browser-engineering-stage.png", fullPage: true });
});
