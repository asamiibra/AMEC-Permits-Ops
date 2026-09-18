import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ProposalSourceWorkspace } from "../src/ProposalSourceWorkspace";
import { api } from "../src/api";

vi.mock("../src/api", () => ({ api: vi.fn(), apiBlob: vi.fn() }));

const mockedApi = vi.mocked(api);

const project = { number: 454, name: "454 - Al Watan Center", state: "DRAFT_SYNCED", folder_count: 1, file_count: 1 };
const entry = { id: "file-1", path: "454 - Al Watan Center/Tender Documents/request.docx", name: "request.docx", is_directory: false, size: 10, modified_ns: 1, content_type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document", logical_category: "TENDER_DOCUMENTS", category_source: "AUTO_CLASSIFIED" };

describe("Proposal V1 source snapshot UX", () => {
  beforeEach(() => mockedApi.mockReset());

  function mockWorkspace(initialState: "COMPLETE" | "INCOMPLETE" = "COMPLETE") {
    let manifestState = initialState;
    let createCalls = 0;
    mockedApi.mockImplementation(async (path: string) => {
      if (path === "/api/proposals/sources/2026/projects") return { projects: [project] };
      if (typeof path !== "string") return {};
      if (path.endsWith("/tree")) return { entries: [entry] };
      if (path.endsWith("/manifest")) return { completeness_state: manifestState, completeness_reasons: manifestState === "INCOMPLETE" ? ["OVERSIZE_NOT_CAPTURED: Tender Documents/large.pdf", "CAPTURE_FAILED: Tender Documents/request.docx"] : [], scan_status: manifestState === "COMPLETE" ? "COMPLETED" : "INCOMPLETE" };
      if (path.includes("/create-proposal")) {
        createCalls += 1;
        if (createCalls === 1) { manifestState = "INCOMPLETE"; throw Object.assign(new Error("Source snapshot incomplete"), { code: "SOURCE_SNAPSHOT_INCOMPLETE" }); }
        return { proposal_id: "p-454", proposal_reference: "AMEC-454", generation_state: "GENERATION_PENDING" };
      }
      if (path.includes("/sync")) { manifestState = "COMPLETE"; return { runs: [{ project_number: 454, captured_count: 1, unchanged_count: 0 }] }; }
      return {};
    });
    return () => { manifestState = "COMPLETE"; };
  }

  it("refreshes the authoritative manifest after a create conflict and uses Retry Sync", async () => {
    mockWorkspace();
    render(<ProposalSourceWorkspace role="SYSTEM_ADMIN" />);
    const create = await screen.findByRole("button", { name: "Create Proposal" });
    await waitFor(() => expect(create).toBeEnabled());
    fireEvent.click(create);
    expect(await screen.findByText("OVERSIZE_NOT_CAPTURED: Tender Documents/large.pdf")).toBeVisible();
    expect(screen.getByText("CAPTURE_FAILED: Tender Documents/request.docx")).toBeVisible();
    expect(screen.getByRole("button", { name: "Create Proposal" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Retry Sync" }));
    await waitFor(() => expect(screen.queryByText("Source snapshot incomplete")).toBeNull());
    expect(screen.getByRole("button", { name: "Create Proposal" })).toBeEnabled();
    expect(mockedApi.mock.calls.some(([path, init]) => String(path).includes("/api/proposals/sources/2026/sync?project=454") && init?.method === "POST")).toBe(true);
  });

  it("keeps Create Proposal disabled and shows manifest reasons when the initial scan is incomplete", async () => {
    mockWorkspace("INCOMPLETE");
    render(<ProposalSourceWorkspace role="SYSTEM_ADMIN" />);
    expect(await screen.findByText("OVERSIZE_NOT_CAPTURED: Tender Documents/large.pdf")).toBeVisible();
    expect(screen.getByRole("button", { name: "Create Proposal" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Retry Sync" })).toBeVisible();
  });
});
