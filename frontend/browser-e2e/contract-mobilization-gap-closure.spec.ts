import { test, expect } from "@playwright/test";

const contract = {
  id: "contract-gap-closure",
  contract: { reference: "C-GAP-001", amount: "100000", currency: "QAR" },
  client: { name: "Synthetic Client" },
  current_revision: {
    id: "revision-gap-001",
    revision_number: 1,
    accepted: true,
    authority_reviewed: true,
    maker_checker: { checker: "checker@example.test", proposal_reconciled: true },
  },
  origin: { proposal_id: "proposal-gap-001", proposal_reference: "P-GAP-001", title: "Synthetic Proposal", revision_number: 1, snapshot: { fields: { price: "100000 QAR" } } },
  executed_evidence: [{ id: "evidence-gap-001", source_reference: "synthetic://executed-contract", contract_revision_id: "revision-gap-001", document_version_id: "document-gap-001", content_hash: "sha256:synthetic", recorded_by: "owner@example.test" }],
  service_engagements: [{ id: "service-gap-001", service_ref: "SVC-GAP-001", status: "ACTIVE", description: "Synthetic service scope" }],
  operations: {
    status: "READY",
    source_of_record: "CANONICAL_CONTRACT_PROJECT_MOBILIZATION_READ_MODEL",
    schedule_state: "ON_TRACK",
    delay_state: "NO_DELAY_SIGNAL",
    risk_state: "NO_OPEN_RISK_SIGNAL",
    responsible_action: "Owner review",
    next_action: "Continue mobilization",
    dates: { project_start: "2026-09-01", contract_end: "2027-09-01" },
    mobilization: { project_activation: "ACTIVE", service_engagement_count: 1, service_engagements: [{ id: "service-gap-001", service_ref: "SVC-GAP-001", project_id: "project-gap-001", contract_revision_id: "revision-gap-001", status: "ACTIVE" }] },
    controls: { invoice_due_state: "NO_INVOICE_DUE_SIGNAL", earned_not_invoiced_state: "NO_EARNED_NOT_INVOICED_SIGNAL", open_blocking_findings: [] },
  },
  readiness: { blockers: [], origin_resolved: true },
  activation: { project_code: "PRJ-GAP-001", start_date: "2026-09-01", activated_by: "owner@example.test", activated_at: "2026-09-01T08:00:00Z" },
  payment_terms: [], documents_needed: [], deliverable_commitments: [], source_panel: [], client_fields: {}, client_contacts: [], my_work: [], issues: [], notifications: [], history: [],
};

test("shows executed evidence and canonical operations projection", async ({ page }) => {
  await page.route("**/api/admin/contracts/contract-gap-closure", route => route.fulfill({ json: contract }));
  await page.goto("/contract-mobilization/contracts/contract-gap-closure");

  await expect(page.getByRole("heading", { name: "Executed Contract Evidence" })).toBeVisible();
  await expect(page.getByText("synthetic://executed-contract", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Operations control surface" })).toBeVisible();
  await expect(page.getByText("CANONICAL_CONTRACT_PROJECT_MOBILIZATION_READ_MODEL", { exact: true })).toBeVisible();
  await expect(page.getByText(/NO_INVOICE_DUE_SIGNAL/)).toBeVisible();
  await expect(page.getByText("SVC-GAP-001", { exact: true }).last()).toBeVisible();
});
