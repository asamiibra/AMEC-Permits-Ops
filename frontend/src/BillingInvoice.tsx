import { useEffect, useMemo, useState } from "react";
import { api } from "./api";
import { Icon } from "./Icon";

type BillingItem = { invoice: any; contract?: any; client?: any; project: any; revision: any; stage: string; receivable: any };

const lanes = [
  ["ALL", "All"],
  ["NEED_ACTION", "Need Action"],
  ["AUTHORITY_REVIEW", "Authority Review"],
  ["READY_CLOSE", "Ready / Close"],
] as const;

const human = (value: unknown) => String(value ?? "—").replaceAll("_", " ");

export function BillingInvoicePage() {
  const [path, setPath] = useState(window.location.pathname);
  const [items, setItems] = useState<BillingItem[]>([]);
  const [lane, setLane] = useState("ALL");
  const [detail, setDetail] = useState<any>(null);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");

  const load = () => {
    setError("");
    const invoiceId = path.split("/")[3];
    const request = invoiceId ? api<any>(`/api/billing/invoices/${invoiceId}`) : api<any>(`/api/billing/invoices?q=${encodeURIComponent(query)}`);
    request.then((data) => invoiceId ? setDetail(data) : setItems(data.items || [])).catch((cause) => setError(cause instanceof Error ? cause.message : "Billing is unavailable."));
  };
  useEffect(() => {
    const sync = () => { setPath(window.location.pathname); setDetail(null); };
    window.addEventListener("popstate", sync);
    return () => window.removeEventListener("popstate", sync);
  }, []);
  useEffect(() => { load(); }, [path]);

  const adminSurface = path.startsWith("/admin/invoices");
  const basePath = adminSurface ? "/admin/invoices" : "/billing/invoices";
  const open = (invoiceId: string) => { window.history.pushState({}, "", `${basePath}/${invoiceId}`); window.dispatchEvent(new PopStateEvent("popstate")); };
  const back = () => { window.history.pushState({}, "", basePath); window.dispatchEvent(new PopStateEvent("popstate")); };
  const filtered = useMemo(() => items.filter((item) => lane === "ALL" || item.stage === lane), [items, lane]);

  if (detail) return <InvoiceWorkspace detail={detail} onBack={back} onRefresh={load} />;
  return <section className="billing-page">
    <div className="billing-intro"><div><span className="eyebrow">AMEC · {adminSurface ? "ADMINISTRATION / INVOICES" : "BILLING / INVOICE"}</span><h2>{adminSurface ? "Invoices" : "Billing & Invoice"}</h2><p>{adminSurface ? "Controlled invoice preparation, review, issue, delivery, and receivable follow-up." : "Human-controlled billing plans, milestone eligibility, invoice revisions, and receivables."}</p></div><span className="tag owner-chip">Source-safe · synthetic</span></div>
    <div className="billing-lanes" role="tablist" aria-label="Invoice lanes">{lanes.map(([key, label]) => <button key={key} role="tab" aria-selected={lane === key} className={lane === key ? "billing-lane active" : "billing-lane"} onClick={() => setLane(key)}>{label}<strong>{key === "ALL" ? items.length : items.filter((item) => item.stage === key).length}</strong></button>)}</div>
    <div className="billing-search"><input aria-label="Search Invoices" placeholder="Search invoice, Contract, Client, or Project" value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") void load(); }} /><button className="button-secondary" onClick={() => void load()}>Search</button></div>
    {error && <div className="error-banner" role="alert">{error}</div>}
    <div className="billing-table"><div className="billing-row billing-head"><b>Invoice</b><b>Invoice Ref</b><b>Contract / Project</b><b>Amount</b><b>Due Date</b><b>Stage</b><b>Open</b></div>{filtered.map((item) => <div className="billing-row" key={item.invoice.id}><div><b>{item.invoice.invoice_reference}</b><small>{human(item.stage)}</small></div><span>{item.invoice.invoice_ref_status === "ALLOCATED" ? item.invoice.invoice_reference : "Not allocated"}</span><span>{item.contract?.contract_reference || "Contract context"}<small>{item.client?.display_name || "Client pending"}{item.project?.project_code ? ` · Project Code: ${item.project.project_code}` : item.project ? " · Activated project" : " · Project context from Contract"}</small></span><span>{item.revision?.payable_total ?? "—"} {item.revision?.currency || ""}</span><span>{item.revision?.due_date || (item.revision?.due_date_status === "PENDING_EVENT" ? "Pending event" : "—")}</span><span>{human(item.invoice.status)}<small>{human(item.receivable?.state)}</small></span><button className="text-button" onClick={() => open(item.invoice.id)}>Open <Icon name="arrow-up-right" size={14} /></button></div>)}{!filtered.length && <div className="billing-empty"><b>No invoices in this lane.</b><p>Invoice drafts appear only from an eligible Billing Milestone.</p></div>}</div>
    <div className="billing-safe-note"><b>Control boundary</b><span>Accept and Issue remain separate human actions. Payment verification changes receivables only; no accounting or financial settlement is performed.</span></div>
  </section>;
}

function InvoiceWorkspace({ detail, onBack, onRefresh }: { detail: any; onBack: () => void; onRefresh: () => void }) {
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const invoice = detail.invoice;
  const revision = detail.revision;
  const act = async (path: string, payload: any) => {
    setBusy(true); setMessage("");
    try { await api<any>(path, { method: "POST", body: JSON.stringify(payload) }); setMessage("Recorded. The exact revision remains auditable."); onRefresh(); }
    catch (cause) { setMessage(cause instanceof Error ? cause.message : "Action could not be recorded."); }
    finally { setBusy(false); }
  };
  return <section className="billing-page"><button className="text-button" onClick={onBack}><Icon name="arrow-left" size={14} /> Billing / Invoice list</button><div className="billing-intro"><div><span className="eyebrow">INVOICE WORKSPACE</span><h2>{invoice.invoice_reference}</h2><p>{detail.contract?.contract_name || detail.contract?.contract_reference || "Contract"} · exact ContractRevision pinned</p></div><span className={`status status-${String(invoice.status).toLowerCase().replaceAll("_", "-")}`}>{human(invoice.status)}</span></div>
    <div className="billing-summary-grid"><div><small>Client</small><b>{invoice.client_account_id || "—"}</b></div><div><small>Project</small><b>{detail.project?.project_code ? `Project Code: ${detail.project.project_code}` : detail.project ? "Activated project" : revision?.contract_project_context_snapshot?.project_opportunity_ref || "Contract project context"}</b></div><div><small>Payable total</small><b>{revision?.payable_total ?? "—"} {revision?.currency || ""}</b></div><div><small>Due date</small><b>{revision?.due_date || (revision?.due_date_status === "PENDING_EVENT" ? "Pending verified event" : "—")}</b></div></div>
    <div className="billing-workspace-grid"><section className="billing-card"><span className="eyebrow">DETERMINISTIC LINES</span><h3>Invoice revision {revision?.revision_number}</h3>{(detail.lines || []).map((line: any) => <div className="billing-line" key={line.id}><span><b>{line.description}</b><small>{human(line.line_role)}{line.billing_milestone_id ? ` · ${line.billing_milestone_id}` : ""}</small></span><b>{line.calculated_line_amount} {line.currency}</b></div>)}<div className="billing-total"><span>Payable</span><b>{revision?.payable_total} {revision?.currency}</b></div></section><section className="billing-card"><span className="eyebrow">HUMAN CONTROL</span><h3>Lifecycle actions</h3><p>Actions are backend-enforced and idempotent. No action sends an invoice or settles accounting.</p><div className="billing-actions"><button className="button-secondary" disabled={busy || invoice.status !== "DRAFT"} onClick={() => act(`/api/billing/invoice-revisions/${revision.id}/accept`, { idempotency_key: `ui-accept-${revision.id}` })}>Accept draft</button><button className="button-primary" disabled={busy || invoice.status !== "ACCEPTED_INTERNAL"} onClick={() => act(`/api/billing/invoice-revisions/${revision.id}/issue`, { idempotency_key: `ui-issue-${revision.id}` })}>Issue invoice</button></div>{message && <div className="admin-owner-message" role="status">{message}</div>}</section></div>
    <div className="billing-safe-note"><b>Receivable</b><span>{human(detail.receivable?.communication_state)} · {human(detail.receivable?.state)} · outstanding {detail.receivable?.outstanding_amount ?? "—"}. Delivery, acknowledgment, approval, and payment remain separate evidence-backed events; paid is not financial settlement.</span></div>
    <section className="billing-card billing-communications"><span className="eyebrow">COMMUNICATION HISTORY</span><h3>{human(detail.communications?.state || detail.receivable?.communication_state)}</h3><p>{(detail.communications?.deliveries || []).length} delivery event(s) · {(detail.communications?.acknowledgments || []).length} acknowledgment event(s).</p></section>
  </section>;
}
