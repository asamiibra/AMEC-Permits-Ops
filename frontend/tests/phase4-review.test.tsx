import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { PHASE4_DECISIONS, Phase4ReviewPage } from "../src/Phase4Review";

const item = {
  id: "classification-001",
  envelope_id: "envelope-001",
  root_event_id: "event-001",
  document_version_id: "version-001",
  source_mode: "RULES_ONLY",
  classifier_version: "rules-only-v1",
  rules_version: "phase4-rules-v1",
  taxonomy_revision: "phase3c-taxonomy-v6c",
  module_truth_contract_sha: "module-truth-sha",
  corpus_app_contract_sha: "corpus-contract-sha",
  record_version: 1,
  status: "PENDING_REVIEW",
  axes_json: {
    review_reason: "Contradictory application evidence requires human review.",
    bounded_evidence: ["synthetic://evidence/application-001", "sha256:bounded-evidence"],
    classification_proposal: { document_type: "APPLICATION_FORM", discipline: "ENGINEERING" },
    contradictions: [{ field: "discipline", values: ["ENGINEERING", "CIVIL"] }],
    candidate_links: [{ label: "Synthetic project", href: "/permits/synthetic-project-001" }],
    currentness: "Current source version v1; record version 1.",
    source_precedence: "Accepted Phase3C Module Truth rules.",
    unsupported_capability_state: "Manual review required for unsupported parser capability.",
    scope: { scope_type: "PROJECT", scope_id: "synthetic-project-001" },
    relationship_resolution: { source_entity_id: "source-001", candidate_entity_id: "entity-001", relationship_type: "PROJECT_DOCUMENT", resolution: "BOUND_BY_REVIEWER" },
  },
};

function response(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: { get: (name: string) => name.toLowerCase() === "content-type" ? "application/json" : null },
    text: async () => JSON.stringify(body),
  };
}

function queueResponse(items = [item]) { return response({ items }); }

async function renderReview(fetchMock = vi.fn().mockResolvedValue(queueResponse()), waitForItem = true) {
  window.history.replaceState({}, "", "/phase4/review?scope_type=PROJECT&scope_id=synthetic-project-001");
  vi.stubGlobal("fetch", fetchMock);
  render(<Phase4ReviewPage role="SYSTEM_ADMIN" />);
  if (waitForItem) await screen.findByRole("button", { name: /envelope-001/ });
  return fetchMock;
}

afterEach(() => { cleanup(); window.history.replaceState({}, "", "/phase4/review"); vi.unstubAllGlobals(); });

describe("Phase4 review UX", () => {
  it("FE-P4-001 renders the canonical review queue and item", async () => {
    await renderReview();
    expect(screen.getByRole("heading", { name: "Review classification evidence" })).toBeTruthy();
    expect(screen.getAllByText("envelope-001").length).toBeGreaterThan(0);
  });

  it("FE-P4-002 renders the review reason", async () => { await renderReview(); expect(screen.getByText("Contradictory application evidence requires human review.")).toBeTruthy(); });
  it("FE-P4-003 renders bounded evidence", async () => { await renderReview(); expect(screen.getByTestId("phase4-evidence")).toHaveTextContent("synthetic://evidence/application-001"); });
  it("FE-P4-004 renders the classification proposal", async () => { await renderReview(); expect(screen.getByTestId("phase4-classification")).toHaveTextContent("APPLICATION_FORM"); });
  it("FE-P4-005 renders contradictions", async () => { await renderReview(); expect(screen.getByTestId("phase4-contradictions")).toHaveTextContent("discipline"); });
  it("FE-P4-006 renders candidate links", async () => { await renderReview(); expect(screen.getByRole("link", { name: /Synthetic project/ })).toHaveAttribute("href", "/permits/synthetic-project-001"); });
  it("FE-P4-007 renders currentness and version", async () => { await renderReview(); expect(screen.getByTestId("phase4-currentness")).toHaveTextContent("record version 1"); });
  it("FE-P4-008 renders server source precedence", async () => { await renderReview(); expect(screen.getByTestId("phase4-precedence")).toHaveTextContent("Accepted Phase3C Module Truth rules"); });
  it("FE-P4-009 renders the authority warning", async () => { await renderReview(); expect(screen.getByTestId("phase4-authority-warning")).toHaveTextContent("does not create a VerifiedAssertion"); });
  it("FE-P4-010 renders the protected-action boundary", async () => { await renderReview(); expect(screen.getByTestId("phase4-protected-boundary")).toHaveTextContent("separately required"); });

  it("FE-P4-011 has a deterministic loading state", () => {
    const pending = vi.fn(() => new Promise(() => undefined));
    window.history.replaceState({}, "", "/phase4/review?scope_type=PROJECT&scope_id=synthetic-project-001");
    vi.stubGlobal("fetch", pending);
    render(<Phase4ReviewPage role="SYSTEM_ADMIN" />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading Phase4 review queue");
  });

  it("FE-P4-012 has a deterministic empty state", async () => {
    await renderReview(vi.fn().mockResolvedValue(queueResponse([])), false);
    expect(await screen.findByTestId("phase4-empty-state")).toHaveTextContent("No Phase4 review items");
  });

  it("FE-P4-013 has a deterministic error state", async () => {
    const fetchMock = vi.fn().mockRejectedValue(new Error("queue unavailable"));
    window.history.replaceState({}, "", "/phase4/review?scope_type=PROJECT&scope_id=synthetic-project-001");
    vi.stubGlobal("fetch", fetchMock);
    render(<Phase4ReviewPage role="SYSTEM_ADMIN" />);
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("queue unavailable"));
  });

  it("FE-P4-014 shows stale/conflict state", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(queueResponse()).mockResolvedValueOnce(response({ detail: { code: "CLASSIFICATION_RECORD_VERSION_CONFLICT" } }, 409));
    await renderReview(fetchMock);
    fireEvent.click(screen.getByRole("button", { name: "Accept" }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("STALE REVIEW"));
  });

  it("FE-P4-015 shows deferred state supplied by the server", async () => {
    await renderReview(vi.fn().mockResolvedValue(queueResponse([{ ...item, status: "DEFERRED" }])));
    expect(screen.getByTestId("phase4-disposition")).toHaveTextContent("Deferred review");
  });

  it("FE-P4-016 shows out-of-scope state supplied by the server", async () => {
    await renderReview(vi.fn().mockResolvedValue(queueResponse([{ ...item, status: "OUT_OF_SCOPE" }])));
    expect(screen.getByTestId("phase4-disposition")).toHaveTextContent("Out-of-scope review");
  });

  it("FE-P4-017 shows unsupported capability state", async () => { await renderReview(); expect(screen.getByTestId("phase4-unsupported")).toHaveTextContent("Manual review required"); });

  it.each(PHASE4_DECISIONS)("FE-P4 action submits exact %s token", async (decision) => {
    const fetchMock = vi.fn().mockResolvedValueOnce(queueResponse()).mockResolvedValueOnce(response({ decision })).mockResolvedValueOnce(queueResponse([]));
    await renderReview(fetchMock);
    if (decision === "CORRECT") {
      fireEvent.change(screen.getByLabelText("Axis"), { target: { value: "discipline" } });
      fireEvent.change(screen.getByLabelText("New value"), { target: { value: "CIVIL" } });
      fireEvent.change(screen.getByLabelText("Reason"), { target: { value: "Synthetic correction" } });
    }
    fireEvent.click(screen.getByRole("button", { name: decision.replaceAll("_", " ").toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase()) }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
    const [url, init] = fetchMock.mock.calls[1];
    expect(url).toBe("/api/phase4/review-decisions");
    expect(JSON.parse(init.body).decision).toBe(decision);
    expect(url).not.toContain("promote");
    expect(url).not.toContain("projection");
  });

  it("FE-P4-024 handles ordinary review authorization denial", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(queueResponse()).mockResolvedValueOnce(response({ detail: "CAPABILITY_DENIED" }, 403));
    await renderReview(fetchMock);
    fireEvent.click(screen.getByRole("button", { name: "Accept" }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Authorization denied"));
  });

  it("FE-P4-025 handles relationship-resolution authorization denial", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(queueResponse()).mockResolvedValueOnce(response({ detail: "CAPABILITY_DENIED" }, 403));
    await renderReview(fetchMock);
    fireEvent.click(screen.getByRole("button", { name: "Resolve Relationship" }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Authorization denied"));
  });

  it("FE-P4-026 prevents duplicate submit while pending", async () => {
    let resolveMutation!: (value: unknown) => void;
    const mutation = new Promise((resolve) => { resolveMutation = resolve; });
    const fetchMock = vi.fn().mockResolvedValueOnce(queueResponse()).mockReturnValueOnce(mutation);
    await renderReview(fetchMock);
    const button = screen.getByRole("button", { name: "Accept" });
    fireEvent.click(button);
    fireEvent.click(button);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    resolveMutation(response({ decision: "ACCEPT" }));
  });

  it("FE-P4-027 handles server mutation failure", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(queueResponse()).mockRejectedValueOnce(new Error("server unavailable"));
    await renderReview(fetchMock);
    fireEvent.click(screen.getByRole("button", { name: "Reject" }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("server unavailable"));
  });

  it("FE-P4-028 preserves exact deep-link behavior", async () => { await renderReview(); expect(screen.getByRole("link", { name: /Synthetic project/ })).toHaveAttribute("href", "/permits/synthetic-project-001"); });
  it("FE-P4-029 aligns with the visible Owner persona", async () => { await renderReview(); expect(screen.getByTestId("phase4-persona")).toHaveTextContent("Owner"); });
  it("FE-P4-030 does not expose direct VerifiedAssertion promotion", async () => { await renderReview(); expect(screen.queryByText(/Promote VerifiedAssertion/i)).toBeNull(); expect(screen.queryByRole("button", { name: /Promote/i })).toBeNull(); });
  it("FE-P4-031 does not expose direct protected-action execution", async () => { await renderReview(); expect(screen.queryByRole("button", { name: /Submit|Approve|Activate|Writeback/i })).toBeNull(); });

  it("FE-P4-V35-032 disables relationship resolution when the server candidate is absent", async () => {
    await renderReview(vi.fn().mockResolvedValue(queueResponse([{ ...item, axes_json: { ...item.axes_json, relationship_resolution: undefined } as unknown as typeof item.axes_json }])))
    expect(screen.getByRole("button", { name: "Resolve Relationship" })).toBeDisabled();
  });

  it("FE-P4-V35-033 sends no queue request without a scoped route", async () => {
    window.history.replaceState({}, "", "/phase4/review");
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    render(<Phase4ReviewPage role="SYSTEM_ADMIN" />);
    expect(await screen.findByTestId("phase4-scope-required")).toBeTruthy();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("FE-P4-V35-034 has no synthetic project fallback", async () => {
    await renderReview(vi.fn().mockResolvedValue(queueResponse([{ ...item, axes_json: { classification_proposal: { discipline: "ENGINEERING" } } as typeof item.axes_json }])))
    expect(screen.getByText(/^Scope$/).parentElement).not.toHaveTextContent("synthetic-project-001");
  });

  it("FE-P4-V35-035 fails closed for an unknown role", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    window.history.replaceState({}, "", "/phase4/review?scope_type=PROJECT&scope_id=synthetic-project-001");
    render(<Phase4ReviewPage role="UNKNOWN_ROLE" />);
    expect(await screen.findByTestId("phase4-unsupported-role")).toBeTruthy();
    expect(fetchMock).not.toHaveBeenCalled();
    expect(screen.getByTestId("phase4-unsupported-role")).not.toHaveTextContent("Owner");
  });

  it("FE-P4-V35-036 renders missing source precedence honestly", async () => {
    await renderReview(vi.fn().mockResolvedValue(queueResponse([{ ...item, axes_json: { ...item.axes_json, source_precedence: undefined } as unknown as typeof item.axes_json }])))
    expect(screen.getByTestId("phase4-precedence")).toHaveTextContent("not supplied by the server");
    expect(screen.getByTestId("phase4-precedence")).not.toHaveTextContent("Accepted Phase3C");
  });

  it("FE-P4-V35-037 requires a changed correction axis/value/reason", async () => {
    const fetchMock = vi.fn().mockResolvedValue(queueResponse());
    await renderReview(fetchMock);
    fireEvent.click(screen.getByRole("button", { name: "Correct" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("CORRECT requires");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("FE-P4-V35-038/039 reuses both identifiers after uncertain transport failure", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(queueResponse()).mockRejectedValueOnce(new Error("network failed")).mockResolvedValueOnce(response({ decision: "ACCEPT" })).mockResolvedValueOnce(queueResponse([]));
    await renderReview(fetchMock);
    fireEvent.click(screen.getByRole("button", { name: "Accept" }));
    await screen.findByRole("alert");
    fireEvent.click(screen.getByRole("button", { name: "Accept" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(4));
    const first = JSON.parse(fetchMock.mock.calls[1][1].body);
    const retry = JSON.parse(fetchMock.mock.calls[2][1].body);
    expect(retry.decision_id).toBe(first.decision_id);
    expect(retry.idempotency_key).toBe(first.idempotency_key);
  });

  it("FE-P4-V35-040 creates new identity for changed intent", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(queueResponse()).mockRejectedValueOnce(new Error("network failed")).mockResolvedValueOnce(response({ decision: "REJECT" })).mockResolvedValueOnce(queueResponse([]));
    await renderReview(fetchMock);
    fireEvent.click(screen.getByRole("button", { name: "Accept" }));
    await screen.findByRole("alert");
    fireEvent.click(screen.getByRole("button", { name: "Reject" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(4));
    const first = JSON.parse(fetchMock.mock.calls[1][1].body);
    const changed = JSON.parse(fetchMock.mock.calls[2][1].body);
    expect(changed.decision_id).not.toBe(first.decision_id);
    expect(changed.idempotency_key).not.toBe(first.idempotency_key);
  });

  it("FE-P4-V35-041 submits the exact server relationship candidate", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(queueResponse()).mockResolvedValueOnce(response({ decision: "RESOLVE_RELATIONSHIP" })).mockResolvedValueOnce(queueResponse([]));
    await renderReview(fetchMock);
    fireEvent.click(screen.getByRole("button", { name: "Resolve Relationship" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
    const body = JSON.parse(fetchMock.mock.calls[1][1].body);
    expect(body.corrections_json).toEqual([item.axes_json.relationship_resolution]);
  });
});
