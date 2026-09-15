import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const proposal = {
  id: "proposal-1", proposal_reference: "AMEC-PROP-0001", project_reference: null, project_id: null,
  client_account_id: null, client_name: "Harbor Client", title: "Harbor design enquiry", stage: "COMMERCIAL_REVIEW",
  stage_label: "Commercial Review", lifecycle: [], current_owner: "Business Development", next_actor: "Business Development",
  next_action: { label: "Review Proposal", eligible: true }, amount: null, last_activity: null, updated_at: "2026-09-13T08:00:00Z",
  fields: { client_scope_of_work: "Design the harbor office", scope_of_work: "Design and engineering services", price: "100000", currency: "QAR", payment_terms: "30 days" },
  provenance: {}, sources: [], notes: [], site_photos: [], forms_v2: { stakeholders: [] }, validation: { blockers: [], warnings: [] },
  readiness_v2: {}, intake_readiness: { blockers: [] }, configuration: { proposal_template: {}, proposal_checklist: {} },
  proposal_breakdown: {}, hardening: { unknowns: [], conflicts: [], assumptions: [], client_responses: [] }, authority: {}, owner_lane: {},
  outputs: {}, current_revision: { id: "revision-1", revision_number: 1 }, draft_revision: { id: "draft-1", revision_number: 2 },
  revision_history: [], stage_history: [], commercial_controls: {}, stage_gate: {}, contract_eligible: false, intelligence: {},
};

async function mockProposalApi(route: any) {
  const url = new URL(route.request().url());
  let body: unknown = {};
  if (url.pathname === "/api/projects" || url.pathname === "/api/applications") body = [];
  else if (url.pathname === "/api/bd/proposals") body = {
    items: [{ id: proposal.id, proposal_reference: proposal.proposal_reference, proposal: proposal.title, project_ref: null, client: proposal.client_name, activity: "Design enquiry", stage: "Commercial Review", stage_code: proposal.stage, amount: null, last_activity: null, location: "Doha", current_owner: proposal.current_owner, next_action: proposal.next_action, owner_lane: {}, contract_eligible: false, validation: { blockers: [] } }],
    lane_counts: { ALL: 1, NEED_ACTION: 0, AUTHORITY_REVIEW: 0, READY_CLOSE: 0 }, count: 1,
  };
  else if (url.pathname === `/api/bd/proposals/${proposal.id}`) body = proposal;
  else if (url.pathname === `/api/bd/proposals/${proposal.id}/intelligence` && route.request().method() === "POST") {
    const request = JSON.parse(route.request().postData() || "{}");
    const outputs: Record<string, unknown> = {
      "intake-analysis": { summary: "Synthetic intake result.", missing_information: [], contradictions: [], unresolved_candidate_facts: [], source_currentness_issues: [], citation_keys: ["CIT-001"] },
      "scope-technical-analysis": { summary: "Synthetic scope result.", assumptions: [], exclusions: [], unresolved_technical_questions: [], eligibility_dependencies: [], recommendation_notes: [], citation_keys: ["CIT-001"] },
      "lpo-variance-analysis": { summary: "Synthetic LPO result.", accepted_revision_id: "revision-1", lpo_evidence_id: "evidence-1", differences: [], citation_keys: ["CIT-001"] },
      "readiness-explanation": { explanation: "Synthetic readiness result.", blockers: [], stale_dependencies: [], missing_information: [], next_permissible_human_actions: [], citation_keys: ["CIT-001"] },
    };
    body = { execution_id: `execution-${request.operation}`, work_product_id: `work-${request.operation}`, skill_id: `proposal.${request.operation}`, output: outputs[request.operation], citations: [{ citation_key: "CIT-001", source_type: "PROPOSAL_ACCEPTED_REVISION", source_id: "revision-1", source_version_or_hash: "revision-hash", locator: { context_key: "proposal-accepted-revision" } }], current_actionable: true };
  } else if (url.pathname === `/api/bd/proposals/${proposal.id}/intelligence/reviews`) body = { items: [] };
  await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
}

test.describe("P04 canonical Proposal browser proof", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => sessionStorage.setItem("proposalops-role", "SYSTEM_ADMIN"));
    await page.route("**/api/**", mockProposalApi);
  });

  test("canonical register and legacy opportunity route render the same Proposal experience", async ({ page }) => {
    await page.goto("/proposals");
    await expect(page).toHaveURL(/\/proposals$/);
    await expect(page.getByRole("heading", { name: "Proposal worklist", level: 2 })).toBeVisible();
    await expect(page.getByRole("button", { name: "New Proposal" })).toBeVisible();
    await expect(page.getByText("Harbor design enquiry").first()).toBeVisible();
    await page.goto("/opportunities");
    await expect(page).toHaveURL(/\/proposals$/);
    await expect(page.getByRole("heading", { name: "Proposal worklist", level: 2 })).toBeVisible();
    await expect(page.getByText("Opportunity Ref", { exact: true })).toHaveCount(0);
  });

  test("direct detail route exposes the five-stage workspace and guarded acceptance", async ({ page }) => {
    await page.goto(`/proposals/${proposal.id}`);
    await expect(page.getByRole("heading", { name: proposal.title, level: 2 })).toBeVisible();
    await expect(page.getByRole("navigation", { name: "Proposal lifecycle" })).toBeVisible();
    await expect(page.getByRole("button", { name: /Intake & Sources/ })).toBeVisible();
    await expect(page.getByRole("button", { name: /Engineering Preparation/ })).toBeVisible();
    await expect(page.getByRole("button", { name: /Commercial Review/ })).toBeVisible();
    await expect(page.getByRole("button", { name: /Client Response/ })).toBeVisible();
    await expect(page.getByRole("button", { name: /Contract Handoff/ })).toBeVisible();
    await page.getByRole("button", { name: /Commercial Review/ }).click();
    await page.getByRole("button", { name: "Accept Proposal Revision" }).click();
    await expect(page.getByRole("dialog")).toContainText("HUMAN DECISION REQUIRED");
    await expect(page.getByRole("dialog")).toContainText("freezes the exact current scope");
    await expect(page.getByRole("button", { name: /Analyze|Generate|Ask AI/ })).toHaveCount(0);
  });

  test("New Proposal and workspace remain usable without horizontal overflow at required viewports", async ({ page }) => {
    for (const viewport of [{ width: 1440, height: 1000 }, { width: 1024, height: 900 }, { width: 390, height: 844 }]) {
      await page.setViewportSize(viewport);
      await page.goto("/proposals/new");
      await expect(page.getByRole("heading", { name: "New Proposal", level: 2 })).toBeVisible();
      await page.getByRole("button", { name: /Client Information/ }).click();
      await expect(page.getByRole("heading", { name: "New Proposal from Client Information", level: 3 })).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
      const axe = await new AxeBuilder({ page }).analyze();
      expect(axe.violations.filter((item) => item.impact === "critical" || item.impact === "serious")).toEqual([]);
    }
  });

  test("Proposal Intelligence renders every typed output and creates a fresh key per invocation", async ({ page }) => {
    const keys: string[] = [];
    page.on("request", (request) => {
      if (request.url().includes(`/api/bd/proposals/${proposal.id}/intelligence`) && request.method() === "POST") keys.push(JSON.parse(request.postData() || "{}").idempotency_key);
    });
    await page.goto(`/proposals/${proposal.id}`);
    for (const operation of ["intake-analysis", "scope-technical-analysis", "lpo-variance-analysis", "readiness-explanation"]) {
      await page.getByLabel("Proposal Intelligence operation").selectOption(operation);
      await page.getByRole("button", { name: "Run Proposal Intelligence" }).click();
      await expect(page.getByTestId("proposal-intelligence-result")).toBeVisible();
      await expect(page.getByRole("heading", { name: "Citations / evidence", level: 5 })).toBeVisible();
      await expect(page.getByText("canonical state unchanged", { exact: false })).toBeVisible();
    }
    expect(keys).toHaveLength(4);
    expect(new Set(keys).size).toBe(4);
    expect(keys.every((key) => key.startsWith(`proposal-intelligence:${proposal.id}:`))).toBe(true);
    await expect(page.getByText("None identified.").first()).toBeVisible();
    await expect(page.getByText("PROPOSAL_ACCEPTED_REVISION · revision-1", { exact: true })).toBeVisible();
  });
});
