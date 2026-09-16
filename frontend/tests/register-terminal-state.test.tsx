import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../src/api";
import { ContractRegister } from "../src/contract/ContractRegister";
import { listContracts } from "../src/contract/contractApi";
import { loadProposalRegister } from "../src/features/proposals/api";
import { ProposalRegisterPage } from "../src/features/proposals/ProposalRegisterPage";

vi.mock("../src/api", () => ({ api: vi.fn() }));
vi.mock("../src/features/proposals/api", () => ({
  loadProposalRegister: vi.fn(),
  proposalHeaders: vi.fn(() => ({ "X-Dev-Role": "SYSTEM_ADMIN" })),
}));
vi.mock("../src/contract/contractApi", () => ({
  listContracts: vi.fn(),
  createContract: vi.fn(),
}));

const mockedApi = vi.mocked(api);
const mockedProposalRegister = vi.mocked(loadProposalRegister);
const mockedListContracts = vi.mocked(listContracts);

const proposalData = {
  items: [{ id: "proposal-1", proposal_reference: "P-1", proposal: "Harbor enquiry", project_ref: null, client: "Harbor Client", activity: "Design", stage: "Intake & Sources", stage_code: "IN_REVIEW", amount: null, last_activity: null, location: null, current_owner: "Business Development", next_action: { label: "Review Proposal" }, owner_lane: {}, contract_eligible: false, validation: {} }],
  lane_counts: { ALL: 1, NEED_ACTION: 1, AUTHORITY_REVIEW: 0, READY_CLOSE: 0 },
  count: 1,
};

const contractItem = {
  id: "contract-1", contract_name: "Harbor Contract", contract_reference: "C-1", client: { name: "Harbor Client" },
  project: { reference: "PRJ-1" }, project_opportunity_ref: null, stage: "DRAFT", status: "DRAFT", amount: null,
  currency: "QAR", close_date: null, next_action: null, blockers_count: 0, billing_readiness: "NOT_READY",
};

describe("Proposal and Contract register terminal states", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedProposalRegister.mockResolvedValue(proposalData as never);
    mockedListContracts.mockResolvedValue({ items: [contractItem] } as never);
    mockedApi.mockResolvedValue({ items: [] } as never);
  });

  it("renders Proposal Register populated and can refresh", async () => {
    render(<ProposalRegisterPage role="SYSTEM_ADMIN" onOpen={vi.fn()} onNew={vi.fn()} />);
    expect((await screen.findAllByText("Harbor enquiry")).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "Refresh Proposal register" }));
    await waitFor(() => expect(mockedProposalRegister).toHaveBeenCalledTimes(2));
  });

  it("renders Proposal Register empty and terminates failed requests", async () => {
    mockedProposalRegister.mockResolvedValue({ ...proposalData, items: [], count: 0, lane_counts: { ALL: 0, NEED_ACTION: 0, AUTHORITY_REVIEW: 0, READY_CLOSE: 0 } } as never);
    render(<ProposalRegisterPage role="SYSTEM_ADMIN" onOpen={vi.fn()} onNew={vi.fn()} />);
    expect(await screen.findByText("No Proposal records match this view.")).toBeVisible();
    mockedProposalRegister.mockRejectedValueOnce(new Error("network down"));
    fireEvent.click(screen.getByRole("button", { name: "Refresh Proposal register" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("network down");
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    await waitFor(() => expect(mockedProposalRegister).toHaveBeenCalledTimes(3));
  });

  it("renders Contract Register populated, empty, and retryable failure states", async () => {
    render(<ContractRegister onOpen={vi.fn()} />);
    expect(await screen.findByText("Harbor Contract")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Refresh Contract register" }));
    await waitFor(() => expect(mockedListContracts).toHaveBeenCalledTimes(8));

    mockedListContracts.mockResolvedValue({ items: [] } as never);
    fireEvent.click(screen.getByRole("tab", { name: /All contracts/ }));
    expect(await screen.findByText("No Contracts in this lane.")).toBeVisible();

    let attempts = 0;
    mockedListContracts.mockImplementation(async () => {
      attempts += 1;
      if (attempts === 1) throw new Error("contract service unavailable");
      return { items: [] } as never;
    });
    fireEvent.click(screen.getByRole("button", { name: "Refresh Contract register" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("contract service unavailable");
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    await waitFor(() => expect(attempts).toBe(8));
  });
});
