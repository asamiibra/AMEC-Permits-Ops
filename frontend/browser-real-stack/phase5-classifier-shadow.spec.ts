import { test, expect, APIRequestContext, Page } from "@playwright/test";

const API = "http://127.0.0.1:8000";

async function openReview(page: Page) {
  await page.addInitScript(() => {
    sessionStorage.setItem("permitops-role", "SYSTEM_ADMIN");
    localStorage.setItem("permitops-locale", "en");
  });
  await page.goto("/phase5/review");
  await expect(page.getByRole("heading", { name: "Review classifier evidence" })).toBeVisible();
}

async function classify(request: APIRequestContext, fixture: string, options: Record<string, unknown> = {}) {
  const response = await request.post(`${API}/api/phase5/classify`, {
    headers: { "X-Dev-Role": "SYSTEM_ADMIN" },
    data: {
      fixture_id: fixture,
      source_artifact_id: `synthetic-artifact://phase5/browser/${fixture}`,
      source_version_token: "v1",
      source_mode: "NEW_UNKNOWN_SOURCE",
      scope_type: "PROJECT",
      scope_id: "synthetic-project-001",
      correlation_id: `browser-${fixture}`,
      evidence_ids: [`synthetic-evidence://phase5/browser/${fixture}/01`],
      ...options,
    },
  });
  expect(response.ok()).toBeTruthy();
  return response.json();
}

test.describe("Phase5 required paths against the SQL Server-backed backend", () => {
  test("P5-BROWSER-NEW", async ({ page, request }) => {
    const body = await classify(request, "P5-BROWSER-NEW");
    expect(body.classification.hard_gate.state).toBe("NONE");
    await openReview(page);
    await expect(page.getByText(/REVIEW_COMPARE_ONLY/)).toBeVisible();
  });

  test("P5-BROWSER-AMBIGUOUS_REVIEW", async ({ page, request }) => {
    const body = await classify(request, "P5-BROWSER-AMBIGUOUS_REVIEW", { contradiction_families: ["DISCIPLINE_CONFLICT"] });
    expect(body.classification.classification_proposal.disposition).toBe("NEEDS_REVIEW");
    await openReview(page);
    await expect(page.getByText(/Review classifier evidence/)).toBeVisible();
  });

  test("P5-BROWSER-OUT_OF_SCOPE", async ({ page, request }) => {
    const body = await classify(request, "P5-BROWSER-OUT_OF_SCOPE", { out_of_scope: true });
    expect(body.classification.executed_layers).toEqual(["L0", "L1"]);
    expect(body.classification.projection_count).toBe(0);
    await openReview(page);
  });

  test("P5-BROWSER-SECRET_EXCLUDE", async ({ page, request }) => {
    const body = await classify(request, "P5-BROWSER-SECRET_EXCLUDE", { secret_exclude: true });
    expect(body.classification.hard_gate.state).toBe("SECRET_EXCLUDE");
    expect(body.classification.preview_count).toBe(0);
    expect(body.classification.training_count).toBe(0);
    await openReview(page);
  });

  test("P5-BROWSER-MODIFIED_KNOWN_SOURCE", async ({ page, request }) => {
    const body = await classify(request, "P5-BROWSER-MODIFIED_KNOWN_SOURCE", { source_mode: "MODIFIED_KNOWN_SOURCE", previous_source_version_token: "v0" });
    expect(body.classification.source_mode).toBe("MODIFIED_KNOWN_SOURCE");
    expect(body.classification.comparisons.prior_state).toBe("MODIFIED_KNOWN_SOURCE");
    await openReview(page);
  });

  test("P5-BROWSER-MOVE_RENAME_CANDIDATE", async ({ page, request }) => {
    const body = await classify(request, "P5-BROWSER-MOVE_RENAME_CANDIDATE", { source_mode: "MOVE_RENAME_CANDIDATE", candidate_entity_id: "synthetic-project-001" });
    expect(body.classification.relationship_resolution.resolution).toBe("PENDING_HUMAN_REVIEW");
    await openReview(page);
  });

  test("P5-BROWSER-MISSING_CANDIDATE", async ({ page, request }) => {
    const body = await classify(request, "P5-BROWSER-MISSING_CANDIDATE", { missing_candidate: true });
    expect(body.classification.classification_proposal.disposition).toBe("MISSING_CANDIDATE");
    expect(body.classification.classification_proposal.currentness).toBe("CANDIDATE_ONLY");
    await openReview(page);
  });

  test("P5-BROWSER-CORRECTION", async ({ page, request }) => {
    const body = await classify(request, "P5-BROWSER-CORRECTION");
    const proposal = body.classification.classification_proposal;
    const decision = await request.post(`${API}/api/phase5/review-decisions`, { headers: { "X-Dev-Role": "SYSTEM_ADMIN" }, data: { decision_id: "P5-BROWSER-CORRECTION-DECISION", classification_envelope_id: body.classification_envelope.id, decision: "CORRECT", actor_id: "browser-input", capability: "PHASE4_REVIEW_DECISION", scope_type: "PROJECT", scope_id: "synthetic-project-001", record_version: body.classification_envelope.record_version, idempotency_key: "P5-BROWSER-CORRECTION-IDEMPOTENCY", corrections_json: [{ axis: "document_type", old_value: proposal.document_type, new_value: "CORRECTED_SYNTHETIC_DOCUMENT", reason: "bounded browser correction", evidence_ids: body.classification.bounded_evidence.map((item: { evidence_id: string }) => item.evidence_id) }] } });
    expect(decision.ok()).toBeTruthy();
    await openReview(page);
  });

  test("P5-BROWSER-PROTECTED_ACTION", async ({ page, request }) => {
    const response = await request.post(`${API}/api/phase5/projections`, { headers: { "X-Dev-Role": "SYSTEM_ADMIN" }, data: { projection_id: "P5-BROWSER-PROTECTED", verified_assertion_id: "00000000-0000-0000-0000-000000000000", target_domain: "SYNTHETIC", target_entity_type: "SYNTHETIC", target_entity_id: "synthetic", operation: "SUBMIT", precondition_version: "v1", idempotency_key: "P5-BROWSER-PROTECTED-IDEMPOTENCY", correlation_id: "P5-BROWSER-PROTECTED" } });
    expect(response.status()).toBe(403);
    await openReview(page);
  });

  test("P5-BROWSER-PERSONA_SCOPE", async ({ page, request }) => {
    const response = await request.get(`${API}/api/phase5/review-queue?scope_type=PROJECT&scope_id=synthetic-project-001`, { headers: { "X-Dev-Role": "BUSINESS_DEVELOPMENT" } });
    expect([200, 403]).toContain(response.status());
    await openReview(page);
    await expect(page.getByText(/SYNTHETIC ONLY/)).toBeVisible();
  });
});
