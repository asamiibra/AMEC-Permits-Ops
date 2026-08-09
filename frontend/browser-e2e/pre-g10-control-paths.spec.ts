import { test, expect, Page } from "@playwright/test";

const fixture = {
  fixture_set: "PermitOps_Synthetic_MVP_Dataset_v1",
  fixture_version: "1.1.1",
  fixture_manifest_hash: "b3a5fbee1a968e3740801b0b696b31a39a3a907437f2377fcdfdfad3bb3546cb",
};

const projects = [
  { id: "p-0142", project_number: "GHCE-2026-0142", project_name: "Al Noor Villa", municipality: "Doha", permit_type: "Building Permit", status: "ACTIVE", assigned_engineer: "Omar Haddad" },
  { id: "p-0187", project_number: "GHCE-2026-0187", project_name: "West Bay Residence", municipality: "Doha", permit_type: "Building Permit", status: "ACTIVE", assigned_engineer: "Rana Faisal" },
];

async function canonicalRoutes(page: Page) {
  await page.route("**/api/**", async route => {
    const path = new URL(route.request().url()).pathname;
    let body: any = { fixture };
    if (path === "/api/projects") body = projects;
    else if (path === "/api/applications") body = projects.map((p, i) => ({ id: `a-${i}`, project_id: p.id, external_request_number: `GHCE-APP-${i ? "0187" : "0142"}`, application_status: i ? "RETURNED" : "DRAFT", repetition_count: i, municipality: p.municipality, permit_type: p.permit_type }));
    else if (path === "/api/reconciliation/governance") body = { environment_badge: "SYNTHETIC PROTOTYPE", evidence_class: "SYNTHETIC_IMPLEMENTATION_EVIDENCE" };
    else if (path.includes("requirement-matrix/coverage")) body = { coverage: { coverage_percent: 100, complete: 4, total_requirements: 4, unknown: 0 } };
    else if (path.includes("field-matrix/coverage")) body = { coverage: { complete_fields: 14, total_fields: 14, critical_fields: 6, result: "COMPLETE" } };
    else if (path === "/api/week10/kpi-review") body = { safety_metrics: { machine_final_submissions: 0, stale_package_readiness_escapes: 0, stale_precheck_readiness_escapes: 0, unresolved_blocking_finding_resubmission_escapes: 0 } };
    else if (path === "/api/week10/tier2-review") body = { items: [] };
    else if (path === "/api/submission-cycles") body = { cycles: [] };
    else if (path === "/api/monitoring/policies") body = { policies: [{ id: "policy-0142", application_id: "GHCE-APP-0142", environment: "TEST", adapter_id: "synthetic-authority", adapter_version: "W11-1.0", operations_allowed: ["READ_CURRENT_STATE", "READ_STATUS", "READ_COMMENTS"], status: "ACTIVE" }], production_read_approved: false };
    else if (path === "/api/monitoring/runs") body = { runs: [{ id: "run-1", result: "NO_CHANGE", application_id: "GHCE-APP-0142", correlation_id: "corr-no-change" }] };
    else if (path === "/api/portal-drift-events") body = { events: [{ id: "drift-1", drift_type: "STRUCTURE_FINGERPRINT_MISMATCH", operation: "READ_COMMENTS", expected_fingerprint: "expected-fingerprint", observed_fingerprint: "observed-fingerprint" }] };
    else if (path === "/api/notifications/observability") body = { attempts: [{ status: "FAILED" }], delivery_failure_rate: 1 };
    else if (path === "/api/week11/report") body = { report: { monitoring_runs_completed: 3, no_change_checks: 1, material_change_events: 1, drifted_adapters: 1, manual_fallbacks: 1, new_comments_detected: 1, duplicate_comments_suppressed: 1 } };
    else if (path === "/api/scenario-variants") body = { variants: [{ id: "v1", name: "Individual owner", variant_code: "INDIVIDUAL_OWNER", description: "Canonical variant", rule_set_version: "RULE-1", rendering_set_version: "RENDER-1", attachment_rule_set_version: "ATTACH-1", grid_rule_set_version: "GRID-1", signed_scope_basis: "Synthetic envelope" }, { id: "v2", name: "Company owner", variant_code: "COMPANY_OWNER", description: "In-envelope variant", rule_set_version: "RULE-1", rendering_set_version: "RENDER-1", attachment_rule_set_version: "ATTACH-1", grid_rule_set_version: "GRID-1", signed_scope_basis: "Synthetic envelope" }] };
    else if (path === "/api/rendering/coverage") body = { coverage: [{ id: "render-1", target_type: "FORM", variant_id: "v1", coverage_percent: 100, missing_fields: [] }] };
    else if (path === "/api/week12/report") body = { rendering: { coverage_percent: 100, missing_supported_mappings: 0 } };
    else if (path === "/api/week12/edge-coverage") body = { passed: 32, case_count: 32 };
    else if (path === "/api/recurrence/analysis") body = { items: [{ id: "rec-1", finding_code: "OFFICIAL_DRAWING_COMMENT", recurrence_key: "CODE_OBJECT:OFFICIAL_DRAWING_COMMENT:DRAWING_SET", classification: "RECURRENCE_AFTER_VERIFIED_CLOSURE", occurrence_count: 2 }] };
    else if (path === "/api/operations/report") body = { report: { monitoring: { active: 1, drifted: 1 }, support_cases: 0, p1_incidents: 0, evidence_class: "SYNTHETIC_IMPLEMENTATION_EVIDENCE" } };
    else if (path === "/api/recovery/manifests") body = { rehearsals: [{ id: "restore-1", rehearsal_type: "TEST_RESTORE_REHEARSAL", result: "PASS", not_formal_g10: true }] };
    else if (path === "/api/shadow-defects") body = [];
    else if (path === "/api/acceptance-rehearsals") body = { rehearsals: [{ id: "accept-1", result: "PASS" }] };
    else if (path === "/api/production-mode") body = { decision: { decision: "ASSISTED_G10_REVIEW_READY" } };
    else if (path === "/api/g10/evidence") body = { items: [{ id: "g10-1", criterion_id: "PERMISSION", requirement: "Permission authority", status: "READY_WITH_CONDITION" }] };
    else if (path === "/api/role-readiness") body = { matrix: [{ id: "role-1", role: "Responsible Engineer", competency_evidence: "Synthetic rehearsal", client_approved: false }] };
    await route.fulfill({ json: body });
  });
}

test.beforeEach(async ({ page }) => {
  await canonicalRoutes(page);
  await page.addInitScript(() => sessionStorage.setItem("permitops-role", "SYSTEM_ADMIN"));
  await page.goto("/");
  await expect(page.getByText("SYNTHETIC PROTOTYPE", { exact: true })).toBeVisible();
});

test("E2E-01 canonical project bootstrap uses the canonical fixture", async ({ page }) => {
  await page.getByRole("navigation").getByRole("button", { name: /Permits/ }).click();
  await expect(page.getByText("GHCE-2026-0142")).toBeVisible();
  await expect(page.getByText("GHCE-APP-0142")).toBeVisible();
  await expect(page.getByText("GHCE-2026-0187")).toBeVisible();
});

test("E2E-02 package blocked state exposes its exact blocker", async ({ page }) => {
  await page.goto("/admin/control-diagnostics");
  await expect(page.getByTestId("package-control")).toContainText("Package: BLOCKED");
  await expect(page.getByText("Current evidence requires human approval")).toBeVisible();
  await expect(page.getByText("STALE PACKAGE — re-evaluation required")).toBeVisible();
});

test("E2E-03 assisted municipality mismatch is visible", async ({ page }) => {
  await page.goto("/admin/control-diagnostics");
  await expect(page.getByText("PORTAL MISMATCH — exception requires correction")).toBeVisible();
  await expect(page.getByText("Assisted municipality value:")).toBeVisible();
  await expect(page.getByText("Doha", { exact: true })).toBeVisible();
});

test("E2E-04 Finding, task, and notification state remain visible", async ({ page }) => {
  await page.goto("/admin/control-diagnostics");
  await expect(page.getByText("Finding owner:")).toContainText("Responsible Engineer");
  await expect(page.getByText("Task:")).toContainText("Finding remediation");
  await expect(page.getByText("Notification FAILED — retry remains visible")).toBeVisible();
});

test("E2E-05 stale package and stale revision deny escape", async ({ page }) => {
  await page.goto("/admin/control-diagnostics");
  await expect(page.getByText("STALE PACKAGE — re-evaluation required")).toBeVisible();
  await expect(page.getByText("STALE PREPARATION REVISION — current state is not reusable")).toBeVisible();
});

test("E2E-06 Arabic control path preserves RTL text and LTR IDs", async ({ page }) => {
  await page.goto("/admin/control-diagnostics");
  await expect(page.getByText("ملاحظة فنية")).toBeVisible();
  await expect(page.locator("bdi[dir='ltr']").filter({ hasText: "GHCE-2026-0142" })).toBeVisible();
});

test("E2E-07 no final-submit capability is rendered", async ({ page }) => {
  await page.goto("/admin/control-diagnostics");
  await expect(page.getByTestId("no-final-submit").first()).toContainText("No final-submit control exists");
  await expect(page.locator("button", { hasText: /final.?submit|submit application/i })).toHaveCount(0);
  await expect(page.getByText("HUMAN SUBMISSION REQUIRED").first()).toBeVisible();
});

test("E2E-08 Week 11 monitoring exposes durable NO_CHANGE evidence", async ({ page }) => {
  await page.goto("/admin/control-diagnostics");
  await expect(page.getByText("Authority monitoring dashboard")).toBeVisible();
  await expect(page.getByText("NO_CHANGE")).toBeVisible();
  await expect(page.getByText("PRODUCTION READ: NOT APPROVED")).toBeVisible();
});

test("E2E-09 Week 11 drift fails closed to assisted fallback", async ({ page }) => {
  await page.goto("/admin/control-diagnostics");
  await expect(page.getByText("FALLBACK ACTIVE")).toBeVisible();
  await expect(page.getByText("Parsed interpretation stopped. Manual/assisted capture required.")).toBeVisible();
});

test("E2E-10 Week 12 attended MFA and handoff preserve role boundaries", async ({ page }) => {
  await page.goto("/admin/control-diagnostics");
  await expect(page.getByText("Variant & human handoff console")).toBeVisible();
  await expect(page.getByText("NO OTP CONTENT")).toBeVisible();
  await expect(page.getByText("HUMAN SUBMISSION REQUIRED").last()).toBeVisible();
});

test("E2E-11 Week 13 recurrence context is deterministic", async ({ page }) => {
  await page.goto("/admin/control-diagnostics");
  await expect(page.getByText("Recurrence, support & integrity operations")).toBeVisible();
  await expect(page.getByText("NO FUZZY AUTO-LINKING")).toBeVisible();
  await expect(page.getByText("RECURRENCE_AFTER_VERIFIED_CLOSURE")).toBeVisible();
});

test("E2E-12 Week 14 acceptance keeps G10 separate from assisted readiness", async ({ page }) => {
  await page.goto("/admin/control-diagnostics");
  await expect(page.getByText("Assisted mode / G10 evidence pack")).toBeVisible();
  await expect(page.getByText("ASSISTED").first()).toBeVisible();
  await expect(page.getByText("READY FOR FORMAL REVIEW ≠ G10 GO")).toBeVisible();
  await expect(page.getByText("NO FABRICATED PERMISSION")).toBeVisible();
});
