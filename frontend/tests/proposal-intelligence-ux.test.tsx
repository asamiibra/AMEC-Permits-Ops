import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ProposalRoutes, canonicalPath } from "../src/features/proposals/ProposalRoutes";
import { loadProposal, loadProposalRegister, proposalCommand } from "../src/features/proposals/api";
import { api } from "../src/api";

vi.mock("../src/api", () => ({ api: vi.fn() }));

vi.mock("../src/features/proposals/api", () => ({
  loadProposal: vi.fn(),
  loadProposalRegister: vi.fn(),
  proposalCommand: vi.fn(),
  proposalHeaders: vi.fn(() => ({ "X-Dev-Role": "SYSTEM_ADMIN" })),
}));

const mockedRegister = vi.mocked(loadProposalRegister);
const mockedDetail = vi.mocked(loadProposal);
const mockedCommand = vi.mocked(proposalCommand);
const mockedApi = vi.mocked(api);

const register = {
  items: [{
    id: "proposal-1", proposal_reference: "AMEC-PROP-0001", proposal: "Harbor design enquiry", project_ref: null,
    client: "Harbor Client", activity: "Design enquiry", stage: "Intake & Sources", stage_code: "IN_REVIEW",
    amount: null, last_activity: null, location: "Doha", current_owner: "Business Development",
    next_action: { label: "Resolve intake blockers", reason: "Source evidence is required." }, owner_lane: {},
    contract_eligible: false, validation: { blockers: [] },
  }],
  lane_counts: { ALL: 1, NEED_ACTION: 1, AUTHORITY_REVIEW: 0, READY_CLOSE: 0 }, count: 1,
};

const detail = {
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

describe("P04 canonical Proposal experience", () => {
  beforeEach(() => {
    mockedRegister.mockReset().mockResolvedValue(register);
    mockedDetail.mockReset().mockResolvedValue(detail);
    mockedCommand.mockReset().mockResolvedValue(detail);
    mockedApi.mockReset().mockImplementation(async (path: string) => path === "/api/bd/proposals/clients"
      ? { items: [{ id: "client-1", name: "Harbor Client" }] }
      : { id: "proposal-1" });
    window.history.pushState({}, "", "/proposals");
  });

  it.each([
    ["/proposals", "/proposals"], ["/proposals/", "/proposals"], ["/proposals/new", "/proposals/new"],
    ["/proposals/proposal-1", "/proposals/proposal-1"], ["/opportunities", "/proposals"],
    ["/opportunities/new", "/proposals/new"], ["/opportunities/proposal-1", "/proposals/proposal-1"],
    ["/bd", "/proposals"], ["/bd/proposals", "/proposals"],
  ])("maps %s to the canonical Proposal route %s", (source, expected) => {
    expect(canonicalPath(source)).toBe(expected);
  });

  it("uses one register for canonical and legacy entry paths", async () => {
    window.history.pushState({}, "", "/opportunities");
    render(<ProposalRoutes role="COMMERCIAL_APPROVER" />);
    expect(await screen.findByRole("heading", { name: "Proposal worklist", level: 2 })).toBeVisible();
    expect(window.location.pathname).toBe("/proposals");
    expect(screen.getAllByText("Harbor design enquiry").length).toBeGreaterThan(0);
    expect(mockedRegister).toHaveBeenCalledTimes(1);
  });

  it("keeps source-first New Proposal intake explicit and backend-driven", async () => {
    render(<ProposalRoutes role="COMMERCIAL_APPROVER" />);
    fireEvent.click(await screen.findByRole("button", { name: /New Proposal/ }));
    fireEvent.click(await screen.findByRole("button", { name: /Start without a source/ }));
    expect(screen.getByRole("heading", { name: "New Proposal from Start without a source", level: 3 })).toBeVisible();
    fireEvent.change(screen.getByLabelText("Proposal title"), { target: { value: "New harbor enquiry" } });
    fireEvent.change(screen.getByLabelText("Client"), { target: { value: "client-1" } });
    fireEvent.click(screen.getByRole("button", { name: "Create Proposal draft" }));
    await waitFor(() => expect(window.location.pathname).toBe("/proposals/proposal-1"));
    expect(screen.queryByRole("button", { name: /Analyze|Generate|Ask AI/ })).toBeNull();
  });

  it("binds a Proposal to the canonical Client returned by intake lookup", async () => {
    mockedApi.mockImplementation(async (path: string) => path === "/api/bd/proposals/clients"
      ? { items: [{ id: "client-1", name: "Canonical Client" }] }
      : { id: "proposal-1" });
    render(<ProposalRoutes role="COMMERCIAL_APPROVER" />);
    fireEvent.click(await screen.findByRole("button", { name: /New Proposal/ }));
    fireEvent.click(await screen.findByRole("button", { name: /Start without a source/ }));
    fireEvent.change(screen.getByLabelText("Proposal title"), { target: { value: "Canonical intake" } });
    fireEvent.change(screen.getByLabelText("Client"), { target: { value: "client-1" } });
    fireEvent.click(screen.getByRole("button", { name: "Create Proposal draft" }));
    await waitFor(() => expect(window.location.pathname).toBe("/proposals/proposal-1"));
    const createCall = mockedApi.mock.calls.find(([path]) => path === "/api/bd/proposals");
    expect(createCall).toBeTruthy();
    expect(JSON.parse(String((createCall?.[1] as RequestInit).body))).toMatchObject({ client_account_id: "client-1" });
  });

  it("blocks creation while the canonical Client list is loading", async () => {
    let resolveClients!: (value: unknown) => void;
    mockedApi.mockImplementation((path: string) => path === "/api/bd/proposals/clients"
      ? new Promise((resolve) => { resolveClients = resolve; })
      : Promise.resolve({ id: "proposal-1" }));
    render(<ProposalRoutes role="COMMERCIAL_APPROVER" />);
    fireEvent.click(await screen.findByRole("button", { name: /New Proposal/ }));
    fireEvent.click(await screen.findByRole("button", { name: /Start without a source/ }));
    expect(screen.getByRole("status")).toHaveTextContent("Loading active Clients");
    expect(screen.getByRole("button", { name: "Create Proposal draft" })).toBeDisabled();
    resolveClients({ items: [{ id: "client-1", name: "Harbor Client" }] });
  });

  it("keeps Client list errors distinct and retryable", async () => {
    let attempts = 0;
    mockedApi.mockImplementation((path: string) => {
      if (path !== "/api/bd/proposals/clients") return Promise.resolve({ id: "proposal-1" });
      attempts += 1;
      return attempts === 1 ? Promise.reject(new Error("network down")) : Promise.resolve({ items: [{ id: "client-1", name: "Harbor Client" }] });
    });
    render(<ProposalRoutes role="COMMERCIAL_APPROVER" />);
    fireEvent.click(await screen.findByRole("button", { name: /New Proposal/ }));
    fireEvent.click(await screen.findByRole("button", { name: /Start without a source/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Client list could not be loaded");
    fireEvent.click(screen.getByRole("button", { name: "Retry client list" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Create Proposal draft" })).not.toBeDisabled());
    expect(attempts).toBe(2);
  });

  it("blocks an empty canonical Client list without posting", async () => {
    mockedApi.mockImplementation(async (path: string) => path === "/api/bd/proposals/clients" ? { items: [] } : { id: "proposal-1" });
    render(<ProposalRoutes role="COMMERCIAL_APPROVER" />);
    fireEvent.click(await screen.findByRole("button", { name: /New Proposal/ }));
    fireEvent.click(await screen.findByRole("button", { name: /Start without a source/ }));
    expect(await screen.findByRole("status")).toHaveTextContent("No active Clients are available");
    expect(screen.getByRole("button", { name: "Create Proposal draft" })).toBeDisabled();
    expect(mockedApi.mock.calls.some(([path]) => path === "/api/bd/proposals")).toBe(false);
  });

  it("preserves Client Information source semantics and canonical identity", async () => {
    render(<ProposalRoutes role="COMMERCIAL_APPROVER" />);
    fireEvent.click(await screen.findByRole("button", { name: /New Proposal/ }));
    fireEvent.click(await screen.findByRole("button", { name: /Client Information/ }));
    fireEvent.change(screen.getByLabelText("Proposal title"), { target: { value: "Client-context enquiry" } });
    fireEvent.change(screen.getByLabelText("Client"), { target: { value: "client-1" } });
    fireEvent.change(screen.getByLabelText("Proposal contact"), { target: { value: "Nadia Owner" } });
    fireEvent.click(screen.getByRole("button", { name: "Create Proposal draft" }));
    await waitFor(() => expect(window.location.pathname).toBe("/proposals/proposal-1"));
    const intakeCall = mockedApi.mock.calls.find(([path]) => path === "/api/bd/proposals/intake");
    expect(intakeCall).toBeTruthy();
    const body = intakeCall?.[1]?.body as FormData;
    expect(body.get("initial_source_type")).toBe("CLIENT_DATA");
    expect(body.get("client_account_id")).toBe("client-1");
    expect(body.get("contact_name")).toBe("Nadia Owner");
  });

  it("renders lifecycle workspace state and confirms protected acceptance", async () => {
    window.history.pushState({}, "", "/proposals/proposal-1");
    render(<ProposalRoutes role="SYSTEM_ADMIN" />);
    expect(await screen.findByRole("heading", { name: "Harbor design enquiry", level: 2 })).toBeVisible();
    expect(screen.getByRole("navigation", { name: "Proposal lifecycle" })).toBeVisible();
    expect(screen.queryByRole("button", { name: /Analyze|Generate|Ask AI/ })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: /Commercial Review/ }));
    expect(await screen.findByRole("button", { name: "Accept Proposal Revision" })).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Accept Proposal Revision" }));
    expect(screen.getByRole("dialog")).toHaveTextContent("HUMAN DECISION REQUIRED");
    expect(screen.getByRole("dialog")).toHaveTextContent("freezes the exact current scope");
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});
