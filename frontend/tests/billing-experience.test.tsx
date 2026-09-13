import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { BillingShell } from "../src/billing/BillingShell";

const capabilities = {
  role: "OWNER_SPONSOR",
  capabilities: { can_view: true, can_accept_invoice: true, can_issue_invoice: true, can_verify_payment: true, can_create_invoice: true },
  authority_source: "SERVER_MUTATION_POLICY",
  frontend_only_authority_grants: 0,
  unresolved_owner_decisions: [{ key: "GLOBAL_INVOICE_NUMBERING_POLICY", label: "Production global Invoice numbering policy" }],
};

const center = {
  metrics: { ready_to_invoice: 1, draft_review_required: 1, issued_outstanding: 2, overdue: 1, payments_to_verify: 1, unallocated_client_credit: 1 },
  work_items: [{ category: "PAYMENT_VERIFICATION_REQUIRED", why: "Evidence precedes verification.", next_action: "Review payment evidence", authority_needed: "Payment verification capability", entity: { id: "payment-1" } }],
  open_receivables: [],
  payments: [],
  source_of_truth: "CANONICAL_BILLING_EVENTS",
  system_insights_only: true,
  ai_assisted: false,
  unresolved_owner_decisions: ["GLOBAL_INVOICE_NUMBERING_POLICY"],
};

beforeEach(() => { window.history.replaceState({}, "", "/billing"); });
afterEach(() => { vi.unstubAllGlobals(); window.history.replaceState({}, "", "/billing"); });

describe("Billing & Finance workspace", () => {
  it("renders capability-backed command center and labels insights as deterministic", async () => {
    vi.stubGlobal("fetch", vi.fn((input: string) => {
      const path = new URL(String(input), window.location.origin).pathname;
      const body = path.endsWith("/capabilities") ? capabilities : center;
      return Promise.resolve({ ok: true, headers: { get: () => "application/json" }, text: async () => JSON.stringify(body) });
    }));
    render(<BillingShell />);
    expect(await screen.findByRole("heading", { name: "Command Center" })).toBeVisible();
    expect(screen.getByText("Canonical records · System insights")).toBeVisible();
    expect(screen.getByText("Billing Intelligence")).toBeVisible();
    expect(screen.getByText("Owner decision required")).toBeVisible();
    expect(screen.getByText(/Payment verification capability/)).toBeVisible();
  });

  it("fails closed when capability resolution fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("capability unavailable")));
    render(<BillingShell />);
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Billing unavailable"));
    expect(screen.queryByRole("heading", { name: "Command Center" })).toBeNull();
  });
});
