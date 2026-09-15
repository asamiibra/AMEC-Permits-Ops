import { expect, test } from "@playwright/test";

test("Proposal Intelligence runs through the real module API and stays review-only", async ({ page, request }) => {
  const headers = { "X-Dev-Role": "SYSTEM_ADMIN" };
  const register = await request.get("/api/bd/proposals", { headers });
  expect(register.ok()).toBeTruthy();
  const body = await register.json();
  expect(body.items.length).toBeGreaterThan(0);

  const proposalId = body.items[0].id;
  const detail = await request.get(`/api/bd/proposals/${proposalId}`, { headers });
  expect(detail.ok()).toBeTruthy();
  const proposal = await detail.json();
  expect(proposal.current_revision?.id).toBeTruthy();

  await page.addInitScript(() => sessionStorage.setItem("proposalops-role", "SYSTEM_ADMIN"));
  await page.goto(`/opportunities/${proposalId}`);
  await expect(page.getByRole("heading", { name: "Proposal Intelligence", level: 3 })).toBeVisible();
  await page.getByLabel("Proposal Intelligence operation").selectOption("readiness-explanation");
  await page.getByRole("button", { name: "Run Proposal Intelligence" }).click();
  await expect(page.getByText("Synthetic governed Proposal readiness explanation.", { exact: true })).toBeVisible();
  await expect(page.getByText("human review required", { exact: false }).first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Accept review" }).first()).toBeVisible();
  await expect(page.getByText("no protected Proposal action was taken", { exact: false })).toBeVisible();
});
