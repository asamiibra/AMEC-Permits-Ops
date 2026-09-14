import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api";
import { createContract, listContracts } from "./contractApi";
import type { ContractListItem } from "./contractTypes";

type EligibleProposal = { id: string; proposal?: string; title?: string; proposal_reference?: string; reference?: string; contract_eligible?: boolean };
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
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [client, setClient] = useState("");
  const [sort, setSort] = useState("reference");
  const [page, setPage] = useState(0);
  const generation = useRef(0);
  const load = async (nextLane = lane, nextQuery = query) => {
    const request = ++generation.current;
    setLoading(true); setError("");
    try {
      const responses = await Promise.all(lanes.map(([key]) => listContracts(nextQuery, key)));
      if (request !== generation.current) return;
      setCounts(Object.fromEntries(responses.map((response, index) => [lanes[index][0], response.count ?? response.items.length])));
      setItems(responses[lanes.findIndex(([key]) => key === nextLane)]?.items || []);
      setPage(0);
    } catch (cause) {
      if (request === generation.current) setError(cause instanceof Error ? cause.message : "Contracts could not be loaded.");
    } finally { if (request === generation.current) setLoading(false); }
  };
  useEffect(() => {
    void load("ALL", "");
    let current = true;
    api<{ items: EligibleProposal[] }>("/api/bd/proposals").then(response => {
      if (current) setProposals(response.items.filter(item => item.contract_eligible));
    }).catch(() => { if (current) setCreateError("Proposal eligibility is unavailable. Refresh to try again."); });
    return () => { generation.current++; current = false; };
  }, []);
  const filtered = useMemo(() => items.filter(item => !client || item.client?.name === client).sort((a, b) => sort === "attention" ? (b.blockers_count || 0) - (a.blockers_count || 0) : String(a.contract_reference || a.contract_name || "").localeCompare(String(b.contract_reference || b.contract_name || ""))), [items, client, sort]);
  const pageCount = Math.max(1, Math.ceil(filtered.length / 20));
  const currentPage = Math.min(page, pageCount - 1);
  const visible = filtered.slice(currentPage * 20, currentPage * 20 + 20);
  const create = async () => {
    if (!proposalId || creating) return;
    setCreating(true); setCreateError("");
    try { const result = await createContract(proposalId); onOpen(result.id); }
    catch (cause) { setCreateError(cause instanceof Error ? cause.message : "Contract could not be created."); }
    finally { setCreating(false); }
  };
  return <section className="contract-register" aria-labelledby="contract-register-title" aria-busy={loading}>
    <div className="contract-page-hero"><div><span className="eyebrow">CONTRACTS</span><h2 id="contract-register-title">Contract &amp; Mobilization</h2><p>Find a Contract, review its blockers, and continue the next human decision.</p></div></div>
    <section className="contract-panel">
      <div className="contract-register-toolbar">
        <div className="contract-tabs" role="group" aria-label="Contract register filters">{lanes.map(([key, text]) => <button key={key} type="button" aria-pressed={lane === key} className={lane === key ? "active" : ""} onClick={() => { setLane(key); void load(key, query); }}>{text}<b>{counts[key] ?? "—"}</b></button>)}</div>
        <form className="contract-register-actions" onSubmit={event => { event.preventDefault(); void load(lane, query); }}><label>Search Contracts<input value={query} placeholder="Contract, client or project" onChange={event => setQuery(event.target.value)} /></label><button className="button-secondary" disabled={loading}>Search</button><label>Client<select value={client} onChange={event => { setClient(event.target.value); setPage(0); }}><option value="">All clients</option>{[...new Set(items.map(item => item.client?.name).filter(Boolean))].sort().map(name => <option key={name} value={name}>{name}</option>)}</select></label><label>Sort<select value={sort} onChange={event => setSort(event.target.value)}><option value="reference">Contract reference</option><option value="attention">Blockers first</option></select></label></form>
        <details><summary>Create from an accepted Proposal</summary><div className="contract-edit-form"><label>Eligible Proposal<select value={proposalId} onChange={event => setProposalId(event.target.value)}><option value="">Select accepted Proposal…</option>{proposals.map(item => <option key={item.id} value={item.id}>{item.proposal || item.title || "Proposal"} · {item.proposal_reference || item.reference}</option>)}</select></label><button className="button-primary" disabled={!proposalId || creating} onClick={() => void create()}>{creating ? "Creating Contract…" : "Create Contract"}</button></div>{!proposals.length && !createError && <p>No eligible accepted Proposals are available.</p>}{createError && <p role="alert">{createError}</p>}</details>
      </div>
      {loading && <p role="status">Loading Contracts…</p>}
      {error && <div className="contract-error" role="alert"><strong>Could not load Contracts</strong><p>{error}</p><button className="button-secondary" onClick={() => void load(lane, query)}>Retry</button></div>}
      {!loading && !error && (visible.length ? <><div className="contract-table-scroll" role="region" aria-label="Contracts register" tabIndex={0}><table className="contract-facts-table"><caption>{filtered.length} matching Contracts</caption><thead><tr><th scope="col">Contract</th><th scope="col">Client / Project</th><th scope="col">Stage</th><th scope="col">Attention / Next action</th><th scope="col">Amount</th><th scope="col">Open</th></tr></thead><tbody>{visible.map(item => <tr key={item.id}><th scope="row">{item.contract_name || "Unnamed Contract"}<small>{item.contract_reference || "Reference pending"}</small></th><td>{item.client?.name || "Client pending"}<small>{item.project?.reference || item.project_opportunity_ref || "Project pending"}</small></td><td>{label(item.stage)}</td><td>{item.blockers_count == null ? "Readiness pending" : item.blockers_count ? item.blockers_count + " blockers" : "No blockers"}<small>{label(item.next_action, "Open Contract to review")}</small></td><td>{item.amount != null ? item.amount + " " + (item.currency || "") : "Not recorded"}</td><td><button className="text-button" aria-label={`Open ${item.contract_reference || item.contract_name || "Contract"}`} onClick={() => onOpen(item.id)}>Open</button></td></tr>)}</tbody></table></div><nav className="contract-action-row" aria-label="Contract pages"><button className="button-secondary" disabled={currentPage === 0} onClick={() => setPage(value => value - 1)}>Previous</button><span>Page {currentPage + 1} of {pageCount}</span><button className="button-secondary" disabled={currentPage + 1 >= pageCount} onClick={() => setPage(value => value + 1)}>Next</button></nav></> : <div className="contract-empty"><h3>No Contracts match this view</h3><p>Adjust your search or filters, or create a draft from an eligible accepted Proposal.</p></div>)}
    </section>
  </section>;
}
