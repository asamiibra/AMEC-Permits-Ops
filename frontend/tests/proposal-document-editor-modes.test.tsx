import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ProposalDocumentEditor } from "../src/ProposalDocumentEditor";
import { api, apiBlob } from "../src/api";

vi.mock("../src/api", () => ({ api: vi.fn(), apiBlob: vi.fn() }));

const mockedApi = vi.mocked(api);
const mockedApiBlob = vi.mocked(apiBlob);
let savedRevision = false;

const revision = () => ({
  revision_number: savedRevision ? 3 : 2,
  source_set_hash: "manifest-current",
  change_plan: {
    mutations: [{ anchor: "n-1", section: "Cover", before: "Old client", after: "Al Watan Center", reason: "Source-backed identity", citation_keys: ["CIT-001"] }],
  },
  ai_provenance: { mutation_count: 1, evidence_refs: ["dv-1"] },
});

function configureApi() {
  mockedApi.mockImplementation(async (path: string) => {
    if (path.endsWith("/save")) { savedRevision = true; return { revision_id: "r-3", tracked_changes: [] }; }
    if (path.endsWith("/changes")) return { changes: [{ anchor: "n-1", before: "ABC", after: "XYZ" }] };
    if (path.includes("/revisions/") && !path.endsWith("/document")) return revision();
    if (path.endsWith("/import")) return {
      nodes: [{ id: "node-id", anchor: "n-1", part: "word/document.xml", text: savedRevision ? "XYZ" : "ABC", xml_hash: "hash", editable: true, block_type: "PARAGRAPH" }],
      editable_node_count: 1,
      read_only_node_count: 0,
      read_only_block_types: [],
    };
    if (path.endsWith("/sources")) return { sources: [], generation_state: "READY_FOR_EDIT", source_manifest_hash: "manifest-current" };
    return {};
  });
  mockedApiBlob.mockResolvedValue(new Blob(["PK"]));
}

function renderEditor() {
  return render(<ProposalDocumentEditor role="SYSTEM_ADMIN" proposalId="p-1" revisionId="r-2" />);
}

describe("Proposal V1 document workspace modes", () => {
  beforeEach(() => {
    mockedApi.mockReset();
    mockedApiBlob.mockReset();
    savedRevision = false;
    vi.stubGlobal("URL", { ...URL, createObjectURL: vi.fn(() => "blob:proposal"), revokeObjectURL: vi.fn() });
    configureApi();
  });

  it("opens the true rendered Document view and requests a render automatically", async () => {
    renderEditor();
    expect(await screen.findByRole("heading", { name: "Proposal Document" })).toBeVisible();
    expect(await screen.findByTitle("Rendered generated proposal DOCX")).toBeVisible();
    expect(screen.queryByRole("textbox", { name: "Editable paragraph 1" })).not.toBeInTheDocument();
    expect(mockedApiBlob).toHaveBeenCalledWith(expect.stringContaining("/revisions/r-2/render"), expect.anything());
    expect(screen.getByText("Rendered ✓")).toBeVisible();
    expect(screen.getByRole("button", { name: "Document" })).toHaveClass("active");
    expect(screen.queryByRole("button", { name: "Review changes" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "AI Changes" }));
    expect(await screen.findByText("Source-backed identity")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Edit Sections" }));
    expect(await screen.findByRole("heading", { name: "Edit Proposal sections" })).toBeVisible();
    expect(screen.getByRole("textbox", { name: "Editable paragraph 1" })).toBeVisible();
  });

  it("keeps Save section disabled until an owner edit makes the section dirty", async () => {
    renderEditor();
    fireEvent.click(await screen.findByRole("button", { name: "Edit Sections" }));
    const save = await screen.findByRole("button", { name: "Save section" });
    expect(save).toBeDisabled();
    expect(screen.getByText("Saved ✓")).toBeVisible();
    fireEvent.input(screen.getByRole("textbox", { name: "Editable paragraph 1" }), { target: { textContent: "XYZ" } });
    expect(screen.getByText("Unsaved changes")).toBeVisible();
    expect(save).toBeEnabled();
  });

  it("reviews owner edits and reverts by node anchor rather than node id", async () => {
    renderEditor();
    fireEvent.click(await screen.findByRole("button", { name: "Edit Sections" }));
    fireEvent.input(screen.getByRole("textbox", { name: "Editable paragraph 1" }), { target: { textContent: "XYZ" } });
    fireEvent.click(screen.getByRole("button", { name: "Review my edits" }));
    expect(await screen.findByText("XYZ")).toBeVisible();
    expect(screen.getByText("ABC")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Revert" }));
    await waitFor(() => expect(screen.getByRole("textbox", { name: "Editable paragraph 1" })).toHaveTextContent("ABC"));
    expect(screen.getByText("Reverted this Owner edit. Save section to persist the revision.")).toBeVisible();
  });

  it("saves the current section, reloads the saved revision, and refreshes the render", async () => {
    renderEditor();
    fireEvent.click(await screen.findByRole("button", { name: "Edit Sections" }));
    fireEvent.input(screen.getByRole("textbox", { name: "Editable paragraph 1" }), { target: { textContent: "XYZ" } });
    const save = screen.getByRole("button", { name: "Save section" });
    fireEvent.click(save);
    await waitFor(() => expect(mockedApi).toHaveBeenCalledWith(expect.stringContaining("/revisions/r-2/save"), expect.anything()));
    await waitFor(() => expect(screen.getByRole("button", { name: "Saved ✓" })).toBeVisible());
    await waitFor(() => expect(mockedApi).toHaveBeenCalledWith(expect.stringContaining("/revisions/r-3"), expect.anything()));
    expect(mockedApiBlob.mock.calls.filter(([path]) => String(path).includes("/render")).length).toBeGreaterThanOrEqual(2);
    fireEvent.click(screen.getByRole("button", { name: "Edit Sections" }));
    expect(await screen.findByRole("textbox", { name: "Editable paragraph 1" })).toHaveTextContent("XYZ");
  });

  it("keeps AI Changes sourced from persisted generation mutations, not the owner diff", async () => {
    renderEditor();
    fireEvent.click(await screen.findByRole("button", { name: "AI Changes" }));
    expect(await screen.findByText("Source-backed identity")).toBeVisible();
    expect(screen.getByText("Old client")).toBeVisible();
    expect(screen.getByText("Al Watan Center")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Review my edits" })).not.toBeInTheDocument();
    expect(mockedApi).not.toHaveBeenCalledWith("/api/proposals-v1/editor/changes", expect.anything());
  });

  it("shows an in-panel render failure with Retry and Download DOCX", async () => {
    mockedApiBlob.mockImplementation(async (path: string) => {
      if (path.includes("/render")) throw new Error("renderer unavailable");
      return new Blob(["PK"]);
    });
    renderEditor();
    expect(await screen.findByText("Document preview unavailable")).toBeVisible();
    expect(screen.getByText("renderer unavailable")).toBeVisible();
    expect(screen.getByRole("button", { name: "Retry" })).toBeVisible();
    expect(screen.getAllByRole("button", { name: "Download DOCX" }).length).toBeGreaterThanOrEqual(2);
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    await waitFor(() => expect(mockedApiBlob.mock.calls.filter(([path]) => String(path).includes("/render")).length).toBe(2));
  });

  it("downloads the current canonical DOCX from Document without silently saving", async () => {
    renderEditor();
    fireEvent.click(await screen.findByRole("button", { name: "Download DOCX" }));
    await waitFor(() => expect(mockedApiBlob).toHaveBeenCalledWith(expect.stringContaining("/revisions/r-2/document"), expect.anything()));
    expect(mockedApi).not.toHaveBeenCalledWith(expect.stringContaining("/save"), expect.anything());
    expect(await screen.findByRole("button", { name: "Downloaded ✓" })).toBeVisible();
  });
});
