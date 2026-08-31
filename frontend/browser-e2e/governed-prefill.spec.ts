import { expect, test } from "@playwright/test";

test("AuthorityCase Forms exposes explicit cited preview and keeps Dashboard search isolated", async ({ page }) => {
  await page.addInitScript(() => sessionStorage.setItem("proposalops-role", "SYSTEM_ADMIN"));
  let assistCalls = 0;
  let applyCalls = 0;
  let retrievalCalls = 0;
  await page.route("**/api/**", async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.includes("/retrieval/query")) retrievalCalls += 1;
    if (url.pathname === "/api/governed-prefill/preview") {
      assistCalls += 1;
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ preview_status: "READY", staleness_state: "CURRENT", master_content_ref: "S3-FORM-001", document_version_id: "version-1", mapping_release_id: "release-1", form_instance_id: "form-instance-1", draft_revision: 0, preview_fingerprint: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", fields: [{ mapping_rule_id: "rule-1", logical_field_key: "authority.reference", target_field: "authority_reference", proposal_status: "READY", proposed_value: "QAT-001", citations: [{ canonical_entity_type: "DocumentVersion", canonical_entity_id: "evidence-version-1", locator: "DocumentVersion:evidence-version-1", document_version_id: "evidence-version-1" }, { canonical_entity_type: "AuthorityCase", canonical_entity_id: "case-1", locator: "AuthorityCase:case-1", document_version_id: null }] }] }) });
      return;
    }
    if (url.pathname === "/api/governed-prefill/apply") {
      applyCalls += 1;
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ apply_status: "APPLIED", applied_field_keys: ["authority.reference"], form_instance_id: "form-instance-1", form_instance: { draft_revision: 1 } }) });
      return;
    }
    if (url.pathname === "/api/permit-ux/cases/case-1") {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ case: { case_reference: "CASE-001" }, project: { project_name: "Test project" }, forms: [{ id: "form-instance-1", form: { id: "form-instance-1", context_type: "AuthorityCase", status: "DRAFT" }, generated_artifacts: [] }], status: { system_status: "ON_TRACK" } }) });
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
  await expect(page.getByText(/FORM VERSION \(TEMPLATE\) version-1/)).toBeVisible();
  await expect(page.getByText("QAT-001")).toBeVisible();
  await page.locator("details").first().locator("summary").click();
  await expect(page.getByText(/DocumentVersion evidence-version-1/)).toBeVisible();
  await expect(page.getByText(/structured source \(no document version\)/)).toBeVisible();
  await expect(page.locator("body")).not.toContainText("undefined");
  await page.getByRole("button", { name: "Apply eligible fields to draft" }).click();
  await expect(page.getByText(/Draft updated successfully at revision 1/)).toBeVisible();
  expect(assistCalls).toBe(1);
  expect(applyCalls).toBe(1);
  expect(retrievalCalls).toBe(0);
});
