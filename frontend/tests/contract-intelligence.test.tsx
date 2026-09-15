import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ContractIntelligence } from "../src/contract/ContractIntelligence";

vi.mock("../src/contract/contractApi", () => ({
  getContractIntelligence: vi.fn().mockResolvedValue({
    contract_id: "contract-1",
    architecture: { registry_version: "test", citation_policy: "current", result_policy: "review" },
    execution_state: "EXECUTABLE_WHEN_ELIGIBLE",
    runtime: { feature_enabled: false, external_inference_enabled: false, real_content_allowed: false, state: "EXECUTABLE_WHEN_ELIGIBLE", runtime_ready: false },
    skills: [{
      skill_id: "contract.document-understand", version: "1.0.0", name: "Understand document",
      purpose: "Structure a Contract-related document for human review.", status: "RUNTIME_NOT_COMMISSIONED", runtime_state: "EXECUTABLE_WHEN_ELIGIBLE", runtime_ready: false,
      eligibility_state: "EXECUTABLE_WHEN_ELIGIBLE", eligibility_reason: "Required Contract context is present.", runtime_reason: "Shared D4 runtime is not commissioned in this environment.", required_capabilities: ["CONTRACT_READ"],
      allowed_reads: ["authorized DocumentVersion"], allowed_effects: ["candidate only"],
      canonical_write_authority: "ZERO", protected_action_authority: "ZERO", human_review_required: true, last_run: null,
    }],
    findings: [],
  }),
}));

describe("Contract Intelligence", () => {
  it("shows an honest advisory runtime state without fake findings", async () => {
    render(<ContractIntelligence contractId="contract-1" />);
    expect(await screen.findByText("Shared Intelligence runtime integrated · advisory only")).toBeVisible();
    expect(screen.getByText("Capability catalogue")).toBeVisible();
    expect(screen.getByText(/Eligible skills can prepare advisory work for human review\./)).toBeVisible();
    expect(screen.getByText("Shared D4 runtime is not commissioned in this environment.")).toBeVisible();
    expect(screen.queryByText(/analysis completed/i)).not.toBeInTheDocument();
  });
});
