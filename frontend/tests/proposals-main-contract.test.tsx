import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ProposalsContractsPage, validateProposalsMainPayload } from "../src/ProposalsContracts";

const kpi = (label: string, entity: "proposal" | "contract") => ({ label, count: 1, states: ["DRAFT"], entity });
const validPayload = () => ({
  rows: [], proposals: [], contracts: [], contract_rows: [], view: "proposals", clients: [],
  kpis: {
    OPEN_PROPOSALS: kpi("Open Proposals", "proposal"), OPEN_CONTRACTS: kpi("Open Contracts", "contract"),
    PROPOSAL_HANDOVER: kpi("Proposal Handover", "proposal"), CONTRACT_HANDOVER: kpi("Contract Handover", "contract"),
    PROPOSALS_IN_PROCESS: kpi("Proposals In Process", "proposal"), CONTRACTS_IN_PROCESS: kpi("Contracts In Process", "contract"),
  },
  filters: [{ key: "ALL", label: "All", entity: "both" }], filter_predicates: { proposal: { ALL: null }, contract: { ALL: null } },
  persona: { persona: "SYSTEM_ADMIN", allowed_actions: [], source_actions: [], amount_visible: true },
  sor: { adapter: "MockSynologyAdapter" }, lineage_model: "Proposal → Contract → Permit", synthetic_only: true,
});

function jsonResponse(body: unknown, status = 200, contentType = "application/json") {
  return { ok: status >= 200 && status < 300, status, headers: { get: (name: string) => name.toLowerCase() === "content-type" ? contentType : null }, text: async () => typeof body === "string" ? body : JSON.stringify(body) };
}

afterEach(() => vi.unstubAllGlobals());

describe("Proposals & Contracts response contract", () => {
  it("accepts a complete response and valid empty registers", () => {
    expect(validateProposalsMainPayload(validPayload())).toMatchObject({ view: "proposals", rows: [] });
  });

  it.each([
    ["required field omitted", () => { const body = validPayload(); delete (body.kpis as any).OPEN_PROPOSALS; return body; }],
    ["required field null", () => { const body = validPayload(); (body.kpis as any).OPEN_PROPOSALS = null; return body; }],
    ["wrong type", () => { const body = validPayload(); (body.kpis as any).OPEN_PROPOSALS.count = "1"; return body; }],
  ])("rejects %s without inventing a KPI", (_label, makePayload) => {
    expect(() => validateProposalsMainPayload(makePayload())).toThrow(/register response/);
  });

  it("renders a controlled error for malformed payload and recovers on Retry", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(jsonResponse({ ...validPayload(), kpis: {} })).mockResolvedValueOnce(jsonResponse(validPayload()));
    vi.stubGlobal("fetch", fetchMock);
    render(<ProposalsContractsPage projects={[]} persona="SYSTEM_ADMIN" openRecord={vi.fn()} />);
    expect(await screen.findByRole("heading", { name: "Proposals & Contracts could not be loaded" })).toBeVisible();
    expect(screen.queryByText("0")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    await waitFor(() => expect(screen.getByRole("heading", { name: "Proposals & Contracts" })).toBeVisible());
    expect(screen.getByText("Open Proposals")).toBeVisible();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
