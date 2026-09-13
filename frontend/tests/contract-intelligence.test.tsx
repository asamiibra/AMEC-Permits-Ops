import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ContractIntelligence } from "../src/contract/ContractIntelligence";

vi.mock("../src/contract/contractApi", () => ({
  getContractIntelligence: vi.fn().mockResolvedValue({
    contract_id: "contract-1",
    architecture: { registry_version: "test", citation_policy: "current", result_policy: "review" },
    runtime: { feature_enabled: false, external_inference_enabled: false, real_content_allowed: false, state: "DISABLED_BY_POLICY" },
    skills: [{
      skill_id: "contract.document-understand", version: "1.0.0", name: "Understand document",
      purpose: "Structure a Contract-related document for human review.", status: "DISABLED_BY_POLICY",
      eligibility_reason: "Execution is disabled by current AI runtime policy.", required_capabilities: ["CONTRACT_READ"],
      allowed_reads: ["authorized DocumentVersion"], allowed_effects: ["candidate only"],
      canonical_write_authority: "ZERO", protected_action_authority: "ZERO", human_review_required: true, last_run: null,
    }],
    findings: [],
  }),
}));

describe("Contract Intelligence", () => {
  it("shows an honest policy-disabled state instead of fake findings", async () => {
    render(<ContractIntelligence contractId="contract-1" />);
    expect(await screen.findByText("Available architecture · real-content execution not enabled")).toBeVisible();
    expect(screen.getByText("Execution is disabled by current AI runtime policy.")).toBeVisible();
    expect(screen.queryByText(/analysis completed/i)).not.toBeInTheDocument();
  });
});
