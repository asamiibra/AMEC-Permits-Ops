import { expect, test } from "@playwright/test";

test("AuthorityCase Forms exposes explicit cited preview and keeps Dashboard search isolated", async ({ page }) => {
  await page.addInitScript(() => sessionStorage.setItem("proposalops-role", "SYSTEM_ADMIN"));
  let assistCalls = 0;
  let retrievalCalls = 0;
  await page.route("**/api/**", async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.includes("/retrieval/query")) retrievalCalls += 1;
    if (url.pathname === "/api/governed-prefill/preview") {
      assistCalls += 1;
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ preview_status: "READY", staleness_state: "CURRENT", master_content_ref: "S3-FORM-001", document_version_id: "version-1", mapping_release_id: "release-1", fields: [{ mapping_rule_id: "rule-1", target_field: "authority_reference", proposal_status: "READY", proposed_value: "QAT-001", citations: [{ canonical_entity_type: "SemanticValueAssertion", canonical_entity_id: "assertion-1", locator: "SemanticValueAssertion:assertion-1", document_version_id: "version-1" }] }] }) });
      return;
    }
    if (url.pathname === "/api/permit-ux/cases/case-1") {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ case: { case_reference: "CASE-001" }, project: { project_name: "Test project" }, forms: [], status: { system_status: "ON_TRACK" } }) });
      return;
    }
    if (url.pathname === "/api/master-content") {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([{ id: "form-1", ref: "S3-FORM-001", title: "Permit application form", owner_status: "Current", current_version_id: "version-1" }]) });
      return;
    }
    await route.fulfill({ status: 200, contentType: "application/json", body: "{}" });
  });

  await page.goto("/permits/case-1/forms");
  await expect(page.getByRole("heading", { name: "Forms" })).toBeVisible();
  await page.getByRole("button", { name: "Assist with Form" }).click();
  await expect(page.getByText("S3-FORM-001 · Permit application form")).toBeVisible();
  await page.getByRole("button", { name: "Review suggestion" }).click();
  await expect(page.getByText("GOVERNED PREFILL PREVIEW")).toBeVisible();
  await expect(page.getByText("QAT-001")).toBeVisible();
  await page.locator("details").first().locator("summary").click();
  await expect(page.getByText(/SemanticValueAssertion assertion-1/)).toBeVisible();
  expect(assistCalls).toBe(1);
  expect(retrievalCalls).toBe(0);
});
