import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ProposalSourceWorkspace } from "../src/ProposalSourceWorkspace";
import { api, apiBlob } from "../src/api";

vi.mock("../src/api", () => ({ api: vi.fn(), apiBlob: vi.fn() }));

const mockedApi = vi.mocked(api);
const mockedApiBlob = vi.mocked(apiBlob);

describe("Proposal V1 source state", () => {
  beforeEach(() => {
    mockedApi.mockReset();
    mockedApiBlob.mockReset();
    let category = "EMAIL";
    mockedApi.mockImplementation(async (path: string, init?: RequestInit) => {
      if (path === "/api/proposals/sources/2026/projects") return { projects: [{ number: 521, name: "521 - Riviera Rayhaan", state: "DRAFT_SYNCED", folder_count: 1, file_count: 1 }] };
      if (path.endsWith("/tree")) return { entries: [{ id: "file-1", path: "521 - Riviera Rayhaan/Email/request.docx", name: "request.docx", is_directory: false, size: 10, modified_ns: 1, content_type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document", logical_category: category, category_source: category === "EMAIL" ? "AUTO_CLASSIFIED" : "OWNER_OVERRIDE" }] };
      if (path.endsWith("/category")) { category = JSON.parse(String(init?.body || "{}")).logical_category; return { logical_category: category, category_source: "OWNER_OVERRIDE" }; }
      return {};
    });
  });

  it("requires explicit Save and preserves the saved category after reload", async () => {
    render(<ProposalSourceWorkspace role="SYSTEM_ADMIN" />);
    expect(await screen.findByText("request.docx")).toBeVisible();
    const select = screen.getByLabelText("Logical category") as HTMLSelectElement;
    expect(select.value).toBe("EMAIL");
    const save = screen.getByRole("button", { name: "Saved" });
    expect(save).toBeDisabled();
    fireEvent.change(select, { target: { value: "TENDER_DOCUMENTS" } });
    expect(screen.getByRole("button", { name: "Save category" })).toBeEnabled();
    expect(mockedApi.mock.calls.some(([path]) => String(path).endsWith("/category"))).toBe(false);
    fireEvent.click(screen.getByRole("button", { name: "Save category" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Saved" })).toBeDisabled());
    expect(select.value).toBe("TENDER_DOCUMENTS");
    expect(screen.getByRole("button", { name: /Tender Documents/ })).toBeVisible();
    expect(mockedApi.mock.calls.find(([path]) => String(path).endsWith("/category"))?.[1]).toMatchObject({ method: "PATCH" });
    expect(mockedApi.mock.calls.filter(([path]) => String(path).endsWith("/category")).length).toBe(1);
  });
});
