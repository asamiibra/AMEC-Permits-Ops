import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ProposalRoutes } from "../src/features/proposals/ProposalRoutes";
import { api } from "../src/api";

vi.mock("../src/api", () => ({ api: vi.fn() }));

const mockedApi = vi.mocked(api);

describe("Proposal V1 editor entry routing", () => {
  beforeEach(() => {
    mockedApi.mockReset();
    window.history.pushState({}, "", "/proposals/p-1");
  });

  it("opens the generated DOCX editor only for READY_FOR_EDIT", async () => {
    mockedApi.mockImplementation(async (path: string) => path.includes("/entry")
      ? { proposal_id: "p-1", revision_id: "r-1", generation_state: "READY_FOR_EDIT", editor_mode: "EDIT" }
      : {});
    render(<ProposalRoutes role="SYSTEM_ADMIN" />);
    await waitFor(() => expect(window.location.pathname).toBe("/proposals/p-1/editor"));
    expect(window.location.search).toContain("revision=r-1");
  });

  it("keeps a failed V1 generation on the recovery surface", async () => {
    mockedApi.mockImplementation(async (path: string) => path.includes("/entry")
      ? { proposal_id: "p-1", revision_id: null, generation_state: "FAILED_RETRYABLE", editor_mode: "RECOVERY", retry_allowed: true, blocker: "PROPOSAL_AI_GENERATION_FAILED" }
      : {});
    render(<ProposalRoutes role="SYSTEM_ADMIN" />);
    expect(await screen.findByRole("heading", { name: "Proposal V1 generation failed", level: 2 })).toBeVisible();
    expect(screen.queryByText("Proposal Intelligence")).toBeNull();
    expect(screen.getByRole("button", { name: "Retry generation" })).toBeVisible();
  });

  it.each(["GENERATION_PENDING", "RUNNING", "BLOCKED_BASELINE", "PENDING_OWNER_SOURCES"])("keeps %s in Proposal V1", async (generation_state) => {
    mockedApi.mockResolvedValue({ proposal_id: "p-1", revision_id: null, generation_state, editor_mode: "PROGRESS" });
    render(<ProposalRoutes role="SYSTEM_ADMIN" />);
    await screen.findByRole("heading", { name: /Proposal V1/ });
    expect(screen.queryByText("Intake & Sources")).toBeNull();
    expect(window.location.pathname).toBe("/proposals/p-1");
  });
});
