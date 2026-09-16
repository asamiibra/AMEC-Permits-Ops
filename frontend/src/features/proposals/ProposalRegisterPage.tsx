import { useEffect, useState } from "react";
import { Icon } from "../../Icon";
import { loadProposalRegister } from "./api";
import { displayDate, text } from "./helpers";
import type { ProposalRegisterResponse, ProposalRegisterRow, ProposalRole } from "./types";

const laneOptions = [
  { code: "ALL", label: "All proposals" },
  { code: "NEED_ACTION", label: "Need action" },
  { code: "AUTHORITY_REVIEW", label: "Authority review" },
  { code: "READY_CLOSE", label: "Ready / close" },
];

export function ProposalRegisterPage({ role, onOpen, onNew }: { role: ProposalRole; onOpen: (id: string) => void; onNew: () => void }) {
  const [data, setData] = useState<ProposalRegisterResponse | null>(null);
  const [filters, setFilters] = useState({ q: "", client: "", stage: "", lane: "ALL" });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);
  const update = (key: keyof typeof filters, value: string) => setFilters((current) => ({ ...current, [key]: value }));
  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    setLoading(true);
    const query = new URLSearchParams({ q: filters.q, lane: filters.lane, ...(filters.client ? { client: filters.client } : {}), ...(filters.stage ? { stage: filters.stage } : {}) });
    loadProposalRegister(role, query, controller.signal).then((result) => { if (active) { setData(result); setError(""); } }).catch((cause: unknown) => { if (active && !(cause instanceof DOMException && cause.name === "AbortError")) setError(cause instanceof Error ? cause.message : "Proposal Register is unavailable."); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; controller.abort(); };
  }, [filters, role, refreshKey]);
  const rows = data?.items || [];
  return <div className="proposal-feature-page">
    <header className="proposal-page-intro"><div><span className="eyebrow">PROPOSALS · REGISTER</span><h2>Proposal worklist</h2><p>Follow one Proposal identity from source intake through Engineering, commercial response, and Contract handoff.</p></div><div className="proposal-intro-actions"><span className="tag">{role === "RESPONSIBLE_ENGINEER" ? "ENGINEERING" : role === "COMMERCIAL_APPROVER" ? "BUSINESS DEVELOPMENT" : "OWNER"}</span><button type="button" className="button-primary" onClick={onNew} disabled={Boolean(data?.action_capabilities) && !data?.action_capabilities?.NEW_PROPOSAL?.available}><Icon name="plus" size={15} /> New Proposal</button></div></header>
    {error && <div className="proposal-alert error-state" role="alert"><Icon name="alert" size={17} /> <span>{error}</span><button type="button" className="text-button" onClick={() => setFilters((current) => ({ ...current }))}>Retry</button></div>}
    <section className="proposal-register-toolbar panel" aria-label="Proposal filters"><div className="proposal-lanes" role="tablist" aria-label="Proposal work lanes">{laneOptions.map((lane) => <button type="button" role="tab" aria-selected={filters.lane === lane.code} className={filters.lane === lane.code ? "proposal-lane active" : "proposal-lane"} key={lane.code} onClick={() => update("lane", lane.code)}><span>{lane.label}</span><strong>{loading ? "…" : data?.lane_counts?.[lane.code] ?? 0}</strong></button>)}</div><div className="proposal-filter-grid"><label>Search all<input aria-label="Search proposals" value={filters.q} onChange={(event) => update("q", event.target.value)} placeholder="Proposal ref, scope, project…" /></label><label>Client<input aria-label="Filter proposals by client" value={filters.client} onChange={(event) => update("client", event.target.value)} placeholder="Client or company" /></label><label>Lifecycle stage<select aria-label="Filter proposals by stage" value={filters.stage} onChange={(event) => update("stage", event.target.value)}><option value="">All stages</option><option value="IN_REVIEW">Intake &amp; Sources</option><option value="PROPOSAL_PREPARATION">Engineering Preparation</option><option value="COMMERCIAL_REVIEW">Commercial Review</option><option value="CLIENT_RESPONSE_PENDING">Client Response</option><option value="ACCEPTED">Contract Handoff</option><option value="CLOSED">Closed</option></select></label><button type="button" className="button-secondary" aria-label="Refresh Proposal register" onClick={() => setRefreshKey((value) => value + 1)} disabled={loading}>Refresh</button></div></section>
    <section className="proposal-register panel" aria-label="Proposal Register"><div className="panel-head"><div><span className="eyebrow">CURRENT BUSINESS STATE</span><h3>{loading ? "Loading proposals…" : `${data?.count ?? 0} proposal${data?.count === 1 ? "" : "s"}`}</h3></div><small>Backend-driven lanes · current owner · next authorized action</small></div><div className="proposal-table-wrap"><table className="proposal-table"><thead><tr><th>Proposal</th><th>Client</th><th>Stage / owner</th><th>Commercial value</th><th>Next action</th><th>Last activity</th><th /></tr></thead><tbody>{loading && <tr><td colSpan={7}><div className="proposal-empty"><b>Loading Proposal work…</b><span>Reading the canonical Proposal register.</span></div></td></tr>}{!loading && !rows.length && <tr><td colSpan={7}><div className="proposal-empty"><b>No Proposal records match this view.</b><span>Try another lane, client, stage, or reference.</span></div></td></tr>}{!loading && rows.map((row) => <RegisterRow key={row.id} row={row} onOpen={onOpen} />)}</tbody></table></div><div className="proposal-mobile-list">{!loading && rows.map((row) => <RegisterCard key={row.id} row={row} onOpen={onOpen} />)}</div></section>
    <p className="proposal-truth-note"><Icon name="shield" size={14} /> Deterministic readiness and next action come from the Proposal backend. AI output, when available, is advisory and never authorizes a protected transition.</p>
  </div>;
}

function RegisterRow({ row, onOpen }: { row: ProposalRegisterRow; onOpen: (id: string) => void }) {
  const next = row.next_action || {};
  return <tr><td><b>{row.proposal}</b><small>{row.proposal_reference} · {row.project_ref || "Project provisional"}</small></td><td>{row.client}<small>{row.location || "Location not recorded"}</small></td><td><span className="proposal-status"><Icon name={row.contract_eligible ? "check" : "current"} size={13} /> {row.stage}</span><small>{row.current_owner}</small></td><td>{row.amount === null || row.amount === undefined ? "Not authorized / not set" : text(row.amount)}</td><td><b>{text(next.label, "Review Proposal")}</b><small>{text(next.reason, "Backend readiness determines the next step.")}{typeof next.blockers === "number" ? ` · ${next.blockers} blocker${next.blockers === 1 ? "" : "s"}` : ""}</small></td><td>{displayDate(row.last_activity)}</td><td><button type="button" className="text-button" onClick={() => onOpen(row.id)}>Open <Icon name="arrow-up-right" size={14} /></button></td></tr>;
}

function RegisterCard({ row, onOpen }: { row: ProposalRegisterRow; onOpen: (id: string) => void }) {
  const next = row.next_action || {};
  return <article className="proposal-register-card"><div className="proposal-card-head"><div><span className="eyebrow">{row.proposal_reference}</span><h3>{row.proposal}</h3></div><span className="proposal-status">{row.stage}</span></div><dl><div><dt>Client</dt><dd>{row.client}</dd></div><div><dt>Owner</dt><dd>{row.current_owner}</dd></div><div><dt>Next action</dt><dd>{text(next.label, "Review Proposal")}</dd></div><div><dt>Last activity</dt><dd>{displayDate(row.last_activity)}</dd></div></dl><p>{text(next.reason, "Backend readiness determines the next step.")}</p><button type="button" className="button-secondary" onClick={() => onOpen(row.id)}>Open Proposal <Icon name="arrow-up-right" size={14} /></button></article>;
}
