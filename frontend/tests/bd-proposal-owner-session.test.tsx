import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { BDProposalOwnerSessionPage } from "../src/BDProposalOwnerSession";
import { api } from "../src/api";

vi.mock("../src/api", () => ({ api: vi.fn() }));

const mockedApi = vi.mocked(api);

describe("BD Proposal owner register", () => {
  beforeEach(() => {
    mockedApi.mockReset();
    mockedApi.mockResolvedValue({
      items: [{ id: "proposal-1", proposal: "Harbor design activity", proposal_reference: "AMEC-SYN-PROP-0001", project_ref: "PROJ-WEST-01", client: "Lane Search Company", stage: "Intake & Sources", amount: null, last_activity: null, next_action: { label: "Resolve intake blockers" } }],
      lane_counts: { ALL: 1, NEED_ACTION: 1, AUTHORITY_REVIEW: 0, READY_CLOSE: 0 },
    });
  });

  it("renders owner lanes, explicit Client/Activity/Location search, and owner columns", async () => {
    render(<BDProposalOwnerSessionPage role="COMMERCIAL_APPROVER" />);
    expect(await screen.findByRole("heading", { name: "Proposal Register" })).toBeVisible();
    expect(screen.getByRole("tab", { name: /All\s*1/ })).toBeVisible();
    expect(screen.getByRole("tab", { name: /Need Action\s*1/ })).toBeVisible();
    expect(screen.getByRole("tab", { name: /Authority Review\s*0/ })).toBeVisible();
    expect(screen.getByRole("tab", { name: /Ready \/ Close\s*0/ })).toBeVisible();
    expect(screen.getByLabelText("Search proposals by client")).toBeVisible();
    expect(screen.getByLabelText("Search proposals by activity")).toBeVisible();
    expect(screen.getByLabelText("Search proposals by location")).toBeVisible();
    expect(screen.getByText("Proposal Description")).toBeVisible();
    expect(screen.getByText("Project Ref")).toBeVisible();
    expect(screen.getByText("Amount")).toBeVisible();
    expect(screen.getByText("Not set")).toBeVisible();
    expect(screen.getByRole("button", { name: "Open →" })).toBeVisible();
  });

  it("sends backend lane and search filters instead of filtering only the rendered page", async () => {
    render(<BDProposalOwnerSessionPage role="COMMERCIAL_APPROVER" />);
    const clientField = await screen.findByLabelText("Search proposals by client");
    fireEvent.change(clientField, { target: { value: "Lane Search Company" } });
    fireEvent.click(screen.getByRole("tab", { name: /Need Action\s*1/ }));
    await waitFor(() => expect(mockedApi).toHaveBeenCalledWith(expect.stringContaining("client=Lane+Search+Company"), expect.anything()));
    expect(mockedApi).toHaveBeenCalledWith(expect.stringContaining("lane=NEED_ACTION"), expect.anything());
  });
});
