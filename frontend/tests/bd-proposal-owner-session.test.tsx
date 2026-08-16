import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { BDProposalOwnerSessionPage } from "../src/BDProposalOwnerSession";
import { api } from "../src/api";

vi.mock("../src/api", () => ({ api: vi.fn() }));

const mockedApi = vi.mocked(api);

describe("BD Proposal owner register", () => {
  beforeEach(() => {
    window.history.pushState({}, "", "/opportunities");
    mockedApi.mockReset();
    mockedApi.mockResolvedValue({
      items: [{ id: "proposal-1", proposal: "Harbor design activity", proposal_reference: "AMEC-SYN-PROP-0001", project_ref: "PROJ-WEST-01", client: "Lane Search Company", activity: "Harbor design activity", stage: "Intake & Sources", stage_code: "IN_REVIEW", amount: null, last_activity: null, current_owner: "Business Development", next_action: { label: "Resolve intake blockers" }, owner_lane: { memberships: ["ALL", "NEED_ACTION"] }, contract_eligible: false, validation: { ready: false } }],
      lane_counts: { ALL: 1, NEED_ACTION: 1, AUTHORITY_REVIEW: 0, READY_CLOSE: 0 },
    });
  });

  it("renders owner lanes, explicit Client/Activity/Location search, and owner columns", async () => {
    render(<BDProposalOwnerSessionPage role="COMMERCIAL_APPROVER" />);
    expect(await screen.findByRole("heading", { name: "Proposal Register" })).toBeVisible();
    expect(screen.getByRole("tab", { name: /All\s*1/ })).toBeVisible();
    expect(screen.getByRole("tab", { name: /Need Action\s*1/ })).toBeVisible();
    expect(screen.getByRole("tab", { name: /Authority Review\s*0/ })).toBeVisible();
    expect(screen.getByRole("tab", { name: /Ready \/ Close\s*0/ })).toBeVisible();
    expect(screen.getByLabelText("Search proposals by client")).toBeVisible();
    expect(screen.getByLabelText("Search proposals by activity")).toBeVisible();
    expect(screen.getByLabelText("Search proposals by location")).toBeVisible();
    expect(screen.getByText("Proposal Description")).toBeVisible();
    expect(screen.getByText("Project Ref")).toBeVisible();
    expect(screen.getByText("Amount")).toBeVisible();
    expect(screen.getByText("Not set")).toBeVisible();
    expect(screen.getByRole("button", { name: "Open" })).toBeVisible();
  });

  it("sends backend lane and search filters instead of filtering only the rendered page", async () => {
    render(<BDProposalOwnerSessionPage role="COMMERCIAL_APPROVER" />);
    const clientField = await screen.findByLabelText("Search proposals by client");
    fireEvent.change(clientField, { target: { value: "Lane Search Company" } });
    fireEvent.click(screen.getByRole("tab", { name: /Need Action\s*1/ }));
    await waitFor(() => expect(mockedApi).toHaveBeenCalledWith(expect.stringContaining("client=Lane+Search+Company"), expect.anything()));
    expect(mockedApi).toHaveBeenCalledWith(expect.stringContaining("lane=NEED_ACTION"), expect.anything());
  });

  it("fails closed with business-safe copy when the register contract is invalid", async () => {
    mockedApi.mockResolvedValue({ items: [{ id: "proposal-1" }], lane_counts: { ALL: 1 } });
    render(<BDProposalOwnerSessionPage role="COMMERCIAL_APPROVER" />);
    expect(await screen.findByRole("alert")).toHaveTextContent("We couldn't load the Proposal Register. Please retry.");
    expect(screen.getByRole("tab", { name: /All\s*—/ })).toBeVisible();
    expect(screen.queryByRole("button", { name: "Open" })).toBeNull();
  });

  it("retries the register request and restores counts and rows after a temporary failure", async () => {
    mockedApi.mockRejectedValueOnce(new Error("API returned 503 for /api/bd/proposals"));
    mockedApi.mockResolvedValueOnce({
      items: [{ id: "proposal-1", proposal: "Recovered Proposal", proposal_reference: "REF-1", project_ref: null, client: "Client", activity: "Activity", stage: "Contract Handoff", stage_code: "CONTRACT_HANDOVER", amount: null, last_activity: null, current_owner: "Business Development", next_action: { label: "Proceed to Contract handoff" }, owner_lane: { memberships: ["ALL", "READY_CLOSE"] }, contract_eligible: true, validation: { ready: true } }],
      lane_counts: { ALL: 1, NEED_ACTION: 0, AUTHORITY_REVIEW: 0, READY_CLOSE: 1 },
    });
    render(<BDProposalOwnerSessionPage role="COMMERCIAL_APPROVER" />);
    expect(await screen.findByRole("alert")).toHaveTextContent("We couldn't load the Proposal Register. Please retry.");
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText("Recovered Proposal")).toBeVisible();
    expect(screen.getByRole("tab", { name: /All\s*1/ })).toBeVisible();
  });

  it("renders the mature Proposal workspace seams and historical-review prompts", async () => {
    mockedApi.mockReset();
    mockedApi
      .mockResolvedValueOnce({
        items: [{ id: "proposal-1", proposal: "Hardening proposal", proposal_reference: "AMEC-SYN-PROP-0001", project_ref: "PROJ-01", client: "Client", activity: "Hardening proposal", stage: "Accepted", stage_code: "ACCEPTED", amount: "QAR 100", last_activity: null, current_owner: "Business Development", next_action: { label: "Review Proposal" }, owner_lane: { memberships: ["ALL", "READY_CLOSE"] }, contract_eligible: true, validation: { ready: true } }],
        lane_counts: { ALL: 1, NEED_ACTION: 0, AUTHORITY_REVIEW: 0, READY_CLOSE: 0 },
      })
      .mockResolvedValueOnce({
        id: "proposal-1",
        proposal_reference: "AMEC-SYN-PROP-0001",
        project_reference: "PROJ-01",
        title: "Hardening proposal",
        stage: "ACCEPTED",
        next_actor: "Business Development",
        updated_at: "2026-08-15T00:00:00+00:00",
        fields: { client_name: "Client", scope_of_work: "AMEC scope", price: "QAR 100", currency: "QAR", duration: "30 days" },
        validation: { ready: true, blockers: [], warnings: [], template: { item: { ref: "F-0003", version: "1" } }, checklist: { item: { ref: "F-0004", version: "1" } } },
        intake_readiness: { ready: true, blockers: [], warnings: [] },
        forms_v2: { stakeholders: [], assumptions: [], conflicts: [], proposal_form: [{ filename: "proposal-form.pdf", verification_state: "READ_BACK_VERIFIED", source_revision: "v1" }], expected_client_inputs: { status: "POLICY_RESOLVED" }, regulatory_scope_intents: [], external_cost_assumptions: [], engineering_contributions: [] },
        hardening: { current_information_changed: true, active_staleness: [{ id: "stale-1", reason_code: "SOURCE_VERSION_CHANGED", impacted_sections: ["commercial"] }], unknowns: [{ id: "unknown-1", statement: "Unknown client input", materiality: "MATERIAL", status: "OPEN", acknowledged: false }], conflicts: [{ id: "conflict-1", field_code: "site.area", source_a: "Tender", source_b: "Email", value_a: "500 m2", value_b: "750 m2", materiality: "MATERIAL", status: "OPEN", acknowledged: false }], material_open_unknowns: [{ id: "unknown-1" }], material_open_conflicts: [{ id: "conflict-1" }], client_responses: [], commercial_outcome: null, boundaries: { acknowledged_is_not_resolved: true } },
        authority: { status: "READY", status_label: "Human review ready", government_authority: false, readiness_blockers: [] },
        proposal_breakdown: { items: [], commercial_summary: {} },
        configuration: { proposal_template: { label: "Proposal Template", status: "READY", ref: "F-0003", version: "1", purpose: "PROPOSAL_TEMPLATE" }, proposal_checklist: { label: "Proposal Checklist", status: "READY", ref: "F-0004", version: "1", purpose: "PROPOSAL_CHECKLIST" }, definitions: { count: 0 }, engineering_references: { status: "DEFERRED", items: [] } },
        outputs: { available: true, proposal: { filename: "proposal.txt" }, checklist: { filename: "checklist.txt" } },
        current_revision: { id: "revision-1", revision_number: 1, template: { ref: "F-0003", version: "1" }, checklist: { ref: "F-0004", version: "1" } },
        revision_history: [{ id: "revision-1", revision_number: 1, accepted_by: "OWNER", accepted_at: "2026-08-15T00:00:00+00:00", content_hash: "abcdef1234567890" }],
        sources: [], notes: [], site_photos: [], amec_input: {}, additional_information: null,
      });
    render(<BDProposalOwnerSessionPage role="COMMERCIAL_APPROVER" />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    expect(await screen.findByRole("heading", { name: "Stakeholders", level: 3 })).toBeVisible();
    expect(screen.getAllByText("Regulatory Scoping").length).toBeGreaterThan(0);
    expect(screen.getByText("Proposal Form · existing Proposal context")).toBeVisible();
    expect(screen.getByText("Decision context")).toBeVisible();
    expect(screen.getAllByText("Client Response").length).toBeGreaterThan(1);
    expect(screen.getByRole("heading", { name: "Commercial Outcome", level: 3 })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Proposal history and lineage", level: 3 })).toBeVisible();
    expect(screen.getByRole("link", { name: "Proposal Download" })).toBeVisible();
    expect(screen.getByText(/Dashboard configuration/)).toBeVisible();
  });

  it("turns each initial source card into a selected, source-specific intake panel", async () => {
    mockedApi.mockReset();
    mockedApi.mockResolvedValue({ items: [], lane_counts: { ALL: 0, NEED_ACTION: 0, AUTHORITY_REVIEW: 0, READY_CLOSE: 0 } });
    render(<BDProposalOwnerSessionPage role="COMMERCIAL_APPROVER" />);
    fireEvent.click(await screen.findByRole("button", { name: "New Proposal" }));
    fireEvent.click(screen.getByRole("button", { name: /Tender Email/ }));
    expect(screen.getByRole("button", { name: /Tender Email.*Selected/ })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("heading", { name: "Tender Email intake" })).toBeVisible();
    expect(screen.getByLabelText("Tender Email source file")).toBeVisible();
    expect(screen.getByRole("button", { name: "Create Proposal & Add Tender Email" })).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: /Tender Document/ }));
    expect(screen.getByRole("heading", { name: "Tender Document intake" })).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Tender Email intake" })).toBeNull();
  });
});
