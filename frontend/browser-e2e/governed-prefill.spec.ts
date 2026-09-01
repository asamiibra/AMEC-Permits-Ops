import { expect, test } from "@playwright/test";

test("AuthorityCase Forms exposes explicit cited preview without retrieval side effects", async ({ page }) => {
  await page.addInitScript(() => sessionStorage.setItem("proposalops-role", "SYSTEM_ADMIN"));
  let assistCalls = 0;
  let retrievalCalls = 0;
  await page.route("**/api/**", async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.includes("/retrieval/query")) retrievalCalls += 1;
    if (url.pathname === "/api/governed-prefill/preview") {
      assistCalls += 1;
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ preview_status: "READY", staleness_state: "CURRENT", master_content_ref: "LG-F-001", document_version_id: "template-v1", mapping_release_id: "release-1", fields: [{ mapping_rule_id: "rule-1", target_field: "authority_reference", proposal_status: "READY", proposed_value: "QAT-001", citations: [{ canonical_entity_type: "DocumentVersion", canonical_entity_id: "evidence-v1", locator: "DocumentVersion:evidence-v1", document_version_id: "evidence-v1" }] }] }) });
      return;
    }
    if (url.pathname === "/api/permit-ux/cases/case-1") {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ case: { case_reference: "CASE-001" }, project: { project_name: "Synthetic project" }, forms: [], status: { system_status: "ON_TRACK" } }) });
      return;
    }
    if (url.pathname === "/api/master-content") {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([{ id: "form-1", ref: "LG-F-001", title: "Permit application form", owner_status: "Current", current_version_id: "template-v1" }]) });
      return;
    }
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({}) });
  });
  await page.goto("/permits/case-1/forms");
  await expect(page.getByRole("heading", { name: "Forms" })).toBeVisible();
  await page.getByRole("button", { name: "Assist with Form" }).click();
  await expect(page.getByText("LG-F-001 · Permit application form")).toBeVisible();
  await page.getByRole("button", { name: "Review suggestion" }).click();
  await expect(page.getByText("GOVERNED PREFILL PREVIEW")).toBeVisible();
  await expect(page.getByText("QAT-001")).toBeVisible();
  expect(assistCalls).toBe(1);
  expect(retrievalCalls).toBe(0);
});
