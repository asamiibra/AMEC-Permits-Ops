import { expect, test } from "@playwright/test";

const owner = { "X-Dev-Role": "OWNER_SPONSOR" };

test("Construction post-approval surface enforces the human start gate", async ({ page }) => {
  const suffix = Date.now().toString();
  const projectResponse = await page.request.post("/api/projects", {
    headers: owner,
    data: { project_number: `CON-${suffix}`, project_name: "Construction control fixture", municipality: "Doha", permit_type: "Building" },
  });
  expect(projectResponse.ok()).toBeTruthy();
  const project = await projectResponse.json();
  const executionResponse = await page.request.post("/api/construction/executions", {
    headers: owner,
    data: { project_id: project.id, execution_ref: `CX-${suffix}`, title: "Post-approval construction scope", scope_description: "Synthetic browser evidence scope" },
  });
  expect(executionResponse.ok()).toBeTruthy();
  const execution = await executionResponse.json();

  const blockedStart = await page.request.post(`/api/construction/executions/${execution.id}/work-events`, {
    headers: owner,
    data: { event_type: "START", idempotency_key: `browser-start-${suffix}` },
  });
  expect(blockedStart.status()).toBe(409);
  expect((await blockedStart.json()).detail).toContain("ConstructionStartAuthorization");

  const readiness = await page.request.post(`/api/construction/executions/${execution.id}/readiness`, { headers: owner, data: {} });
  expect(readiness.ok()).toBeTruthy();
  expect((await readiness.json()).result).toBe("NOT_READY");

  await page.goto("/construction");
  await expect(page.getByRole("heading", { name: "Construction execution", level: 1 })).toBeVisible();
  await expect(page.getByText("Human-gated boundary", { exact: true })).toBeVisible();
  await expect(page.getByText("CONSTRUCTION START GATE", { exact: true })).toBeVisible();
  await page.screenshot({ path: process.env.CONSTRUCTION_SCREENSHOT_PATH || "../artifacts/construction-post-approval-closure/construction-start-gate-closure.png", fullPage: true });
  await expect(page.locator("body")).not.toContainText(/financial settlement performed/i);
});
