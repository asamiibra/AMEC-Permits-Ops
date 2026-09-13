import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { BillingShell } from "../src/billing/BillingShell";
import { PaymentWorkspace } from "../src/billing/BillingDetailWorkspaces";
import type { BillingCapabilityDTO } from "../src/billing/billing-types";

const capabilities: BillingCapabilityDTO = {
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
  it("allocates to the explicitly selected second eligible invoice", async () => {
    const requests: Array<{ url: string; body?: string }> = [];
    const payment = { payment: { id: "p1", client_account_id: "c1", contract_id: "ct1", project_id: "pr1", received_date: "2026-01-01", amount: "200.00", currency: "QAR", reference: "PAY-1", payment_method: "BANK_TRANSFER", verification_status: "VERIFIED", recorded_at: "2026-01-01" }, credit: { state: "UNALLOCATED_CLIENT_CREDIT", received_amount: "200.00", allocated_amount: "0.00", unallocated_balance: "200.00", verification_status: "VERIFIED", currency: "QAR" }, context: { client: { id: "c1", name: "Client", reference: "C1" }, project: { id: "pr1", name: "Project", reference: "P1" }, contract: { id: "ct1", name: "Contract", reference: "CT1" } }, evidence: { primary: true, receipt_voucher: false }, allocations: [], reversals: [], eligible_invoices: [{ invoice_id: "i1", invoice_reference: "AMEC-1", outstanding_amount: "100.00", currency: "QAR", milestone_ids: ["m1"] }, { invoice_id: "i2", invoice_reference: "AMEC-2", outstanding_amount: "100.00", currency: "QAR", milestone_ids: ["m2"] }] };
    vi.stubGlobal("fetch", vi.fn((input: string, init?: RequestInit) => { const url = String(input); requests.push({ url, body: init?.body as string | undefined }); const path = new URL(url, window.location.origin).pathname; const body = path.endsWith("/payments/p1") ? payment : path.includes("/evidence") ? { items: [], total: 0 } : {}; return Promise.resolve({ ok: true, headers: { get: () => "application/json" }, text: async () => JSON.stringify(body) }); }));
    render(<PaymentWorkspace paymentId="p1" capabilities={{ ...capabilities, capabilities: { ...capabilities.capabilities, can_allocate_payment: true, can_reverse_payment: true } }} onOpen={() => undefined} />);
    await screen.findByRole("heading", { name: "PAY-1" });
    const selectButtons = await screen.findAllByRole("button", { name: "Select" });
    selectButtons[1].click();
    await screen.findByDisplayValue("100.00");
    screen.getByRole("button", { name: "Allocate verified payment" }).click();
    await waitFor(() => expect(requests.some((item) => item.url.endsWith("/payments/p1/allocate") && item.body?.includes('"invoice_id":"i2"'))).toBe(true));
  });

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
