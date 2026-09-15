import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ProposalWorkspace } from "../src/ProposalWorkspace";

vi.mock("../src/api", () => ({ api: vi.fn() }));

const proposal = {
  id: "proposal-1", title: "Owner test proposal", proposal_reference: "PROP-001", client_name: "Canonical Client",
  stage: "IN_REVIEW", stage_label: "Intake & Sources", current_owner: "Business Development", next_action: { label: "Resolve intake blockers" },
  fields: { client_scope_of_work: "Client wording", scope_of_work: "AMEC normalized scope", price: 100, currency: "QAR" },
  forms_v2: { stakeholders: [], regulatory_scope_intents: [], assumptions: [], service_scope_items: [], engineering_contributions: [], external_cost_assumptions: [], proposal_contact: null, commercial_client: { display_name: "Canonical Client" }, expected_client_inputs: null, proposal_form: [] },
  hardening: { unknowns: [], conflicts: [], active_staleness: [], client_responses: [], commercial_outcome: null }, validation: { ready: false, blockers: [{ code: "SOURCE_EVIDENCE_REQUIRED", label: "Source evidence", section: "sources" }], warnings: [] },
  intake_readiness: { ready: false, blockers: [], warnings: [] }, readiness_v2: { ready: false, blocking: [] }, sources: [], site_photos: [], revision_history: [], stage_history: [], outputs: {}, configuration: {}, commercial_controls: {}, contract_eligibility: { eligible: false, blockers: ["SOURCE_EVIDENCE_REQUIRED"] }, authority: {}, updated_at: "2026-01-01T00:00:00Z",
};

describe("Proposal workspace closure", () => {
  it("deep-links each workspace view and supports browser back", () => {
    window.history.pushState({}, "", "/opportunities/proposal-1");
    render(<ProposalWorkspace role="COMMERCIAL_APPROVER" proposal={proposal} setProposal={vi.fn()} onBack={vi.fn()} setMessage={vi.fn()} error="" setError={vi.fn()} />);
    fireEvent.click(screen.getByRole("link", { name: /Engineering/ }));
    expect(window.location.search).toBe("?view=engineering");
    expect(screen.getByRole("heading", { name: "Service scope & scope of work" })).toBeVisible();
    window.history.pushState({}, "", "/opportunities/proposal-1");
    fireEvent(window, new PopStateEvent("popstate"));
    expect(screen.getByRole("heading", { name: "Executive operating summary" })).toBeVisible();
  });

  it("keeps readiness server-owned and links blockers to the working view", () => {
    window.history.pushState({}, "", "/opportunities/proposal-1");
    render(<ProposalWorkspace role="COMMERCIAL_APPROVER" proposal={proposal} setProposal={vi.fn()} onBack={vi.fn()} setMessage={vi.fn()} error="" setError={vi.fn()} />);
    expect(screen.getAllByText("Source evidence").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Resolve intake blockers/).length).toBeGreaterThan(0);
    expect(screen.queryByLabelText(/DocumentVersion ID|Professional Party ID|Capability ref|Policy ref/i)).toBeNull();
  });
});
