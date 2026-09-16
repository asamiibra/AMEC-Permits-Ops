import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api";
import { createContract, listContracts } from "./contractApi";
import type { ContractListItem } from "./contractTypes";

type EligibleProposal = { id: string; proposal?: string; title?: string; proposal_reference?: string; reference?: string; contract_eligible?: boolean };
type RegisterState = "LOADING" | "READY" | "EMPTY" | "ERROR";
const lanes = [["ALL", "All contracts"], ["NEEDS_ACTION", "Needs action"], ["AUTHORITY_REVIEW", "Authority review"], ["READY_CLOSE", "Ready / close"]] as const;
const label = (value: unknown, fallback = "Not recorded") => value ? String(value).toLowerCase().replaceAll("_", " ").replace(/^./, c => c.toUpperCase()) : fallback;

export function ContractRegister({ onOpen }: { onOpen: (id: string) => void }) {
  const [items, setItems] = useState<ContractListItem[]>([]);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [lane, setLane] = useState("ALL");
  const [query, setQuery] = useState("");
  const [proposals, setProposals] = useState<EligibleProposal[]>([]);
  const [proposalId, setProposalId] = useState("");
  const [error, setError] = useState("");
  const [createError, setCreateError] = useState("");
  const [message, setMessage] = useState("");
  const [loadState, setLoadState] = useState<RegisterState>("LOADING");
  const [creating, setCreating] = useState(false);
  const [client, setClient] = useState("");
  const [sort, setSort] = useState("reference");
  const [page, setPage] = useState(0);
  const controllerRef = useRef<AbortController | null>(null);

  const load = async (nextLane = lane, nextQuery = query) => {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    setLoadState("LOADING"); setError(""); setCreateError("");
    try {
      const responses = await Promise.all(lanes.map(([key]) => listContracts(nextQuery, key, controller.signal)));
      if (controller.signal.aborted) return;
      setCounts(Object.fromEntries(responses.map((response, index) => [lanes[index][0], response.count ?? response.items.length])));
      const nextItems = responses[lanes.findIndex(([key]) => key === nextLane)]?.items || [];
      setItems(nextItems); setPage(0);
      const proposalData = await api<{ items: EligibleProposal[] }>("/api/bd/proposals", { signal: controller.signal });
      if (controller.signal.aborted) return;
      setProposals(proposalData.items.filter(item => item.contract_eligible));
      setLoadState(nextItems.length ? "READY" : "EMPTY");
    } catch (cause) {
      if (cause instanceof DOMException && cause.name === "AbortError") return;
      if (controller.signal.aborted) return;
      setLoadState("ERROR"); setError(cause instanceof Error ? cause.message : "Contracts could not be loaded.");
    }
  };

  useEffect(() => { void load("ALL", ""); return () => controllerRef.current?.abort(); }, []);

  const filtered = useMemo(() => items.filter(item => !client || item.client?.name === client).sort((a, b) => sort === "attention" ? (b.blockers_count || 0) - (a.blockers_count || 0) : String(a.contract_reference || a.contract_name || "").localeCompare(String(b.contract_reference || b.contract_name || ""))), [items, client, sort]);
  const pageCount = Math.max(1, Math.ceil(filtered.length / 20));
  const currentPage = Math.min(page, pageCount - 1);
  const visible = filtered.slice(currentPage * 20, currentPage * 20 + 20);
  const create = async () => {
    if (!proposalId || creating) return;
    setCreating(true); setCreateError("");
    try { const result = await createContract(proposalId); onOpen(result.id); }
    catch (cause) { setCreateError(cause instanceof Error ? cause.message : "Contract could not be created; the accepted Proposal remains unchanged."); }
    finally { setCreating(false); }
  };

  return <section className="contract-register" aria-labelledby="contract-register-title" aria-busy={loadState === "LOADING"}>
    <div className="contract-page-hero"><div><span className="eyebrow">AMEC · BUSINESS STAGE 2</span><h1 id="contract-register-title">Contract &amp; Mobilization</h1><p>One operational register for commercial acceptance, executed evidence, mobilization, and the next human decision.</p></div><span className="contract-synthetic-badge">SYNTHETIC / OWNER CONTROLLED</span></div>
    <div className="contract-register-summary"><div><span>Accessible Contracts</span><strong>{counts.ALL ?? 0}</strong></div><div><span>Need action</span><strong>{counts.NEEDS_ACTION ?? 0}</strong></div><div><span>Authority review</span><strong>{counts.AUTHORITY_REVIEW ?? 0}</strong></div><div><span>Ready / close</span><strong>{counts.READY_CLOSE ?? 0}</strong></div></div>
    <section className="contract-panel contract-register-panel"><div className="contract-panel-heading"><div><span className="eyebrow">OPERATIONAL REGISTER</span><h3>Contracts</h3></div><span className="contract-source-note">Canonical Contract read model</span></div>
      <div className="contract-register-toolbar"><div className="contract-tabs" role="tablist" aria-label="Contract register filters">{lanes.map(([key, text]) => <button key={key} type="button" role="tab" aria-selected={lane === key} className={lane === key ? "active" : ""} onClick={() => { setLane(key); void load(key, query); }}>{text}<b>{counts[key] ?? "—"}</b></button>)}</div><form className="contract-register-actions" onSubmit={event => { event.preventDefault(); void load(lane, query); }}><label>Search Contracts<input value={query} placeholder="Contract, client or project" onChange={event => setQuery(event.target.value)} /></label><button className="button-secondary" disabled={loadState === "LOADING"}>Search</button><label>Client<select value={client} onChange={event => { setClient(event.target.value); setPage(0); }}><option value="">All clients</option>{[...new Set(items.map(item => item.client?.name).filter(Boolean))].sort().map(name => <option key={name} value={name}>{name}</option>)}</select></label><label>Sort<select value={sort} onChange={event => setSort(event.target.value)}><option value="reference">Contract reference</option><option value="attention">Blockers first</option></select></label><button type="button" className="button-secondary" aria-label="Refresh Contract register" disabled={loadState === "LOADING"} onClick={() => void load(lane, query)}>Refresh</button></form><details><summary>Create from an accepted Proposal</summary><div className="contract-edit-form"><label>Eligible Proposal<select value={proposalId} onChange={event => setProposalId(event.target.value)}><option value="">Select accepted Proposal…</option>{proposals.map(item => <option key={item.id} value={item.id}>{item.proposal || item.title || "Proposal"} · {item.proposal_reference || item.reference}</option>)}</select></label><button className="button-primary" disabled={!proposalId || creating} onClick={() => void create()}>{creating ? "Creating Contract…" : "Create Contract"}</button></div>{!proposals.length && !createError && <p>No eligible accepted Proposals are available.</p>}{createError && <p role="alert">{createError}</p>}</details></div>
      {loadState === "LOADING" && <p role="status">Loading Contracts…</p>}
      {error && <div className="contract-error" role="alert"><strong>Could not load Contracts</strong><p>{error}</p><button className="button-secondary" onClick={() => void load(lane, query)}>Retry</button></div>}
      {loadState === "EMPTY" && !error && <div className="contract-empty"><h3>No Contracts match this view</h3><p>Adjust your search or filters, or create a draft from an eligible accepted Proposal.</p></div>}
      {loadState === "READY" && <><div className="contract-table-scroll" role="region" aria-label="Contracts register" tabIndex={0}><table className="contract-facts-table"><caption>{filtered.length} matching Contracts</caption><thead><tr><th scope="col">Contract</th><th scope="col">Client / Project</th><th scope="col">Stage</th><th scope="col">Attention / Next action</th><th scope="col">Amount</th><th scope="col">Open</th></tr></thead><tbody>{visible.map(item => <tr key={item.id}><th scope="row">{item.contract_name || "Unnamed Contract"}<small>{item.contract_reference || "Reference pending"}</small></th><td>{item.client?.name || "Client pending"}<small>{item.project?.reference || item.project_opportunity_ref || "Project pending"}</small></td><td>{label(item.stage)}</td><td>{item.blockers_count == null ? "Readiness pending" : item.blockers_count ? item.blockers_count + " blockers" : "No blockers"}<small>{label(item.next_action, "Open Contract to review")}</small></td><td>{item.amount != null ? item.amount + " " + (item.currency || "") : "Not recorded"}</td><td><button className="text-button" aria-label={`Open ${item.contract_reference || item.contract_name || "Contract"}`} onClick={() => onOpen(item.id)}>Open</button></td></tr>)}</tbody></table></div><nav className="contract-action-row" aria-label="Contract pages"><button className="button-secondary" disabled={currentPage === 0} onClick={() => setPage(value => value - 1)}>Previous</button><span>Page {currentPage + 1} of {pageCount}</span><button className="button-secondary" disabled={currentPage + 1 >= pageCount} onClick={() => setPage(value => value + 1)}>Next</button></nav></>}
      {message && <p role="alert">{message}</p>}
      <div className="contract-boundary-note"><strong>Ownership boundary</strong><span>Finance owns Invoice/payment mutations; Project Activation is a separate protected human action; Intelligence never writes Contract truth.</span></div>
    </section>
  </section>;
}
