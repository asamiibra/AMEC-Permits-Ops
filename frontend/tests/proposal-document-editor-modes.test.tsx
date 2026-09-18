import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ProposalDocumentEditor } from "../src/ProposalDocumentEditor";
import { api, apiBlob } from "../src/api";

vi.mock("../src/api", () => ({ api: vi.fn(), apiBlob: vi.fn() }));

const mockedApi = vi.mocked(api);
const mockedApiBlob = vi.mocked(apiBlob);

describe("Proposal V1 document workspace modes", () => {
  beforeEach(() => {
    mockedApi.mockReset();
    mockedApiBlob.mockReset();
    vi.stubGlobal("URL", { ...URL, createObjectURL: vi.fn(() => "blob:proposal"), revokeObjectURL: vi.fn() });
    mockedApi.mockImplementation(async (path: string) => {
      if (path.includes("/revisions/") && !path.endsWith("/document")) {
        return {
          revision_number: 2,
          source_set_hash: "manifest-current",
          change_plan: { mutations: [{ anchor: "n-1", section: "Cover", before: "Old client", after: "Al Watan Center", reason: "Source-backed identity", citation_keys: ["CIT-001"] }] },
          ai_provenance: { mutation_count: 1, evidence_refs: ["dv-1"] },
        };
      }
      if (path.endsWith("/import")) return { nodes: [{ id: "n-1", anchor: "n-1", part: "word/document.xml", text: "Al Watan Center", xml_hash: "hash", editable: true, block_type: "PARAGRAPH" }], editable_node_count: 1, read_only_node_count: 0, read_only_block_types: [] };
      if (path.endsWith("/sources")) return { sources: [], generation_state: "READY_FOR_EDIT", source_manifest_hash: "manifest-current" };
      return {};
    });
    mockedApiBlob.mockResolvedValue(new Blob(["PK"]));
  });

  it("opens the true rendered Document view and keeps anchored text editing secondary", async () => {
    render(<ProposalDocumentEditor role="SYSTEM_ADMIN" proposalId="p-1" revisionId="r-2" />);
    expect(await screen.findByRole("heading", { name: "Generated Proposal document" })).toBeVisible();
    expect(screen.getByTitle("Rendered generated proposal DOCX")).toBeVisible();
    expect(screen.getByRole("button", { name: "Document" })).toHaveClass("active");
    fireEvent.click(screen.getByRole("button", { name: "AI Changes" }));
    expect(await screen.findByText("Source-backed identity")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Edit Sections" }));
    await waitFor(() => expect(screen.getByRole("heading", { name: "Edit Proposal sections" })).toBeVisible());
    expect(screen.getByRole("textbox", { name: "Editable paragraph 1" })).toBeVisible();
  });
});
