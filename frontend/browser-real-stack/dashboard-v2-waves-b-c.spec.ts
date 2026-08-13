import { expect, test } from "@playwright/test";

test("Dashboard V2 exposes the canonical Waves B+C governance facade and detail surface", async ({ page, request }) => {
  const owner = { "X-Dev-Role": "SYSTEM_ADMIN" };
  const health = await request.get("/health");
  expect(health.ok()).toBeTruthy();
  const healthBody = await health.json();
  expect(healthBody.database_dialect).toBe("postgresql");
  expect(healthBody.alembic_versions).toContain("0042_bd_proposal_forms_driven_v2");

  const catalogs = await request.get("/api/dashboard-v2/catalogs", { headers: owner });
  expect(catalogs.ok()).toBeTruthy();
  const catalogBody = await catalogs.json();
  expect(Array.isArray(catalogBody.external_bodies)).toBeTruthy();
  expect(Array.isArray(catalogBody.service_types)).toBeTruthy();
  expect(catalogBody.release_statuses).toContain("RELEASED");

  const formsResponse = await request.get("/api/dashboard-v2/forms", { headers: owner });
  expect(formsResponse.ok()).toBeTruthy();
  const forms = await formsResponse.json();
  expect(Array.isArray(forms)).toBeTruthy();

  await page.goto("/dashboard-v2");
  await expect(page.getByRole("heading", { name: "Dashboard V2", level: 2 })).toBeVisible();
  await expect(page.getByText("Advanced governance filters")).toBeVisible();
  await page.getByText("Advanced governance filters").click();
  await expect(page.getByLabel("External body")).toBeVisible();
  await expect(page.getByLabel("Automation readiness")).toBeVisible();

  if (forms.length) {
    const formsSection = page.getByTestId("dashboard-v2-forms");
    await formsSection.getByRole("button", { name: "Open" }).first().click();
    await expect(page.getByRole("heading", { name: "Regulatory applicability", level: 3 })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Policy and technical source lineage", level: 3 })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Form automation governance", level: 3 })).toBeVisible();
    await page.screenshot({ path: "../artifacts/dashboard-v2-waves-b-c/v2-governance-detail.png", fullPage: true });
  }
});
