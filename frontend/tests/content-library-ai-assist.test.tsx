import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CanonicalFormsLibrary } from "../src/MasterContentForms";

const source = {
  id: "source-form-1",
  ref: "F-0001",
  content_type: "FORM",
  title: "Governed source form",
  category: { id: "cat-1", label: "Permit" },
  description: "Current source description",
  used_in: ["ADMIN"],
  owner_status: "Current",
  version: 2,
  version_status: "CURRENT",
  current_document_version_id: "document-version-2",
};

const category = { id: "cat-1", label: "Permit", allowed_content_types: ["FORM"] };

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn((input: string | URL, init?: RequestInit) => {
    const url = new URL(String(input), window.location.origin);
    const body = url.pathname === "/api/master-content"
      ? [source]
      : url.pathname === "/api/master-content/categories"
        ? [category]
        : url.pathname === "/api/dashboard-v2/catalogs"
          ? { external_bodies: [], jurisdictions: [], service_types: [], lifecycle_phases: [] }
          : url.pathname.endsWith("/intelligence/master-content.description-draft")
            ? {
                work_product_id: "wp-description-1",
                skill_id: "master-content.description-draft",
                output_class: "DRAFT",
                review_precondition_version: "source-hash-2",
                draft_fields: { title: "AI reviewed form title", description: "AI reviewed description" },
                citations: [{ ordinal: 1, source_type: "MASTER_CONTENT_VERSION", source_id: "document-version-2", source_version_or_hash: "source-hash-2", locator_json: { citation_key: "CIT-001" } }],
                output: {
                  summary: "Source-grounded description draft.",
                  title: "AI reviewed form title",
                  description: "AI reviewed description",
                  keywords: ["permit"],
                  draft_only: true,
                  findings: ["Review the description before saving."],
                  open_questions: [],
                  citations: ["CIT-001"],
                  human_review_required: true,
                  canonical_state_mutated: false,
                },
              }
            : url.pathname.endsWith("/review")
              ? { decision_id: "decision-1", decision: "ACCEPT", work_product_id: "wp-description-1", accepted_fields: { title: "AI reviewed form title", description: "AI reviewed description" }, canonical_state_mutated: false }
              : {};
    return Promise.resolve({ ok: true, headers: { get: (name: string) => name === "content-type" ? "application/json" : null }, text: async () => JSON.stringify(body) });
  }));
});

describe("Content Library AI Form workflow", () => {
  it("runs a grounded skill, renders evidence, and applies only accepted draft fields", async () => {
    render(<CanonicalFormsLibrary role="SYSTEM_ADMIN" />);
    await waitFor(() => expect(screen.getByText("Governed source form")).toBeVisible());

    fireEvent.click(screen.getByRole("button", { name: "+ New Form" }));
    fireEvent.change(screen.getByLabelText("Governed source for AI assistance"), { target: { value: source.id } });
    fireEvent.click(screen.getByRole("button", { name: "Description draft" }));

    await waitFor(() => expect(screen.getByText("Source-grounded description draft.")).toBeVisible());
    expect(screen.getByText("CIT-001")).toBeVisible();
    expect(screen.getByText(/MASTER_CONTENT_VERSION · document-version-2/)).toBeVisible();
    expect(screen.getByText("Findings")).toBeVisible();
    expect(screen.getByRole("button", { name: "Accept selected suggestions" })).toBeEnabled();

    fireEvent.click(screen.getByRole("button", { name: "Accept selected suggestions" }));
    await waitFor(() => expect(screen.getByText(/Selected values are now in the editable draft/)).toBeVisible());
    expect(screen.getByLabelText("Title / Name")).toHaveValue("AI reviewed form title");
    expect(screen.getByLabelText("Description")).toHaveValue("AI reviewed description");
    expect(screen.getByText(/Nothing is saved until you use the normal Save action/)).toBeVisible();
  });
});
