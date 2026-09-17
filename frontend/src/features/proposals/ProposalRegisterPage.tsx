import { useEffect, useMemo, useState } from "react";
import { Icon } from "../../Icon";
import { api } from "../../api";
import { loadProposalRegister } from "./api";
import { displayDate, text } from "./helpers";
import type { ProposalRegisterResponse, ProposalRegisterRow, ProposalRole } from "./types";

type SourceProject = {
  number: number;
  name: string;
  state: string;
  discovery_class?: string;
  folder_count: number;
  file_count: number;
};

export function ProposalRegisterPage({ role, onOpen, onNew, onOpenDraft }: {
  role: ProposalRole;
  onOpen: (id: string) => void;
  onNew: () => void;
  onOpenDraft?: (number: number) => void;
}) {
  const [data, setData] = useState<ProposalRegisterResponse | null>(null);
  const [sourceProjects, setSourceProjects] = useState<SourceProject[]>([]);
  const [filters, setFilters] = useState({ q: "", client: "", stage: "" });
  const [loading, setLoading] = useState(true);
  const [sourceLoading, setSourceLoading] = useState(true);
  const [error, setError] = useState("");
  const [sourceError, setSourceError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    setLoading(true);
    const query = new URLSearchParams({ q: filters.q, lane: "ALL", ...(filters.client ? { client: filters.client } : {}), ...(filters.stage ? { stage: filters.stage } : {}) });
    loadProposalRegister(role, query, controller.signal)
      .then((result) => { if (active) { setData(result); setError(""); } })
      .catch((cause: unknown) => { if (active && !(cause instanceof DOMException && cause.name === "AbortError")) { setData(null); setError(cause instanceof Error ? cause.message : "Proposal Register is unavailable."); } })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; controller.abort(); };
  }, [filters, role, refreshKey]);

  useEffect(() => {
    let active = true;
    setSourceLoading(true);
    api<{ projects?: SourceProject[] }>("/api/proposals/sources/2026/projects", { headers: { "X-Dev-Role": role } })
      .then((result) => { if (active) { setSourceProjects(result.projects || []); setSourceError(""); } })
      .catch((cause: unknown) => { if (active) { setSourceProjects([]); setSourceError(cause instanceof Error ? cause.message : "Synology source projects are unavailable."); } })
      .finally(() => { if (active) setSourceLoading(false); });
    return () => { active = false; };
  }, [role, refreshKey]);

  const rows = data?.items || [];
  const activeProjectNumbers = useMemo(() => new Set(rows.map((row) => Number(row.project_ref)).filter((value) => Number.isFinite(value))), [rows]);
  const drafts = sourceProjects.filter((project) => !activeProjectNumbers.has(project.number));
  return <div className="proposal-feature-page proposal-v1-page">
    <header className="proposal-page-intro">
      <div><span className="eyebrow">PROPOSALS V1 · SYNOLOGY SOURCES</span><h2>Proposal worklist</h2><p>Start with a synced source project, review its files, and create a Proposal only when the Owner is ready.</p></div>
      <div className="proposal-intro-actions"><span className="tag">{role === "RESPONSIBLE_ENGINEER" ? "ENGINEERING" : role === "COMMERCIAL_APPROVER" ? "BUSINESS DEVELOPMENT" : "OWNER"}</span><button type="button" className="button-primary" onClick={onNew}><Icon name="plus" size={15} /> New Proposal</button></div>
    </header>
    {error && <div className="proposal-alert error-state" role="alert"><Icon name="alert" size={17} /> <span>{error}</span><button type="button" className="text-button" onClick={() => setRefreshKey((value) => value + 1)}>Retry</button></div>}
    {sourceError && <div className="proposal-alert warning-copy" role="status"><Icon name="alert" size={17} /> <span>{sourceError}</span></div>}
    <section className="proposal-v1-panels" aria-label="Proposal V1 work areas">
      <section className="proposal-v1-panel panel" aria-labelledby="proposal-v1-drafts-title">
        <div className="panel-head"><div><span className="eyebrow">SYNCED SYNOLOGY PROJECTS</span><h3 id="proposal-v1-drafts-title">Drafts</h3></div><small>Source files are read-only until the Owner creates a Proposal.</small></div>
        {sourceLoading ? <div className="proposal-empty"><b>Loading synced projects…</b><span>Reading Tender / 1- Proposal / 2026.</span></div> : !drafts.length ? <div className="proposal-empty"><b>No Draft source projects.</b><span>New eligible Synology folders will appear here after the bridge syncs them.</span></div> : <div className="proposal-v1-project-list">{drafts.map((project) => <button type="button" className="proposal-v1-project" key={project.number} onClick={() => onOpenDraft?.(project.number)}><span className="proposal-v1-project-copy"><b>{project.name}</b><small>{project.file_count} files · {project.folder_count} folders · Draft · Synology synced</small></span><span className="proposal-v1-project-action">Open sources <Icon name="arrow-up-right" size={14} /></span></button>)}</div>}
      </section>
      <section className="proposal-v1-panel panel" aria-labelledby="proposal-v1-active-title">
        <div className="panel-head"><div><span className="eyebrow">OWNER CREATED</span><h3 id="proposal-v1-active-title">Active Proposals</h3></div><small>Open a Proposal to review, edit, and export its document.</small></div>
        {loading ? <div className="proposal-empty"><b>Loading active Proposals…</b><span>Reading the canonical Proposal register.</span></div> : !rows.length ? <div className="proposal-empty"><b>No Active Proposals yet.</b><span>Create a Proposal from a synced Draft source project to start the editor flow.</span><span>No Proposal records match this view.</span></div> : <div className="proposal-v1-active-list">{rows.map((row) => <ActiveProposal key={row.id} row={row} onOpen={onOpen} />)}</div>}
      </section>
    </section>
    <div className="proposal-v1-footer"><button type="button" className="button-secondary" aria-label="Refresh Proposal register" onClick={() => setRefreshKey((value) => value + 1)} disabled={loading || sourceLoading}><Icon name="refresh" size={14} /> Refresh workspace</button><span><Icon name="shield" size={14} /> Synology remains read-only. Removing a source only changes the ProposalOps active source set.</span></div>
  </div>;
}

function ActiveProposal({ row, onOpen }: { row: ProposalRegisterRow; onOpen: (id: string) => void }) {
  const next = row.next_action || {};
  return <article className="proposal-v1-active-row"><div><b>{row.proposal}</b><small>{row.proposal_reference} · {row.project_ref || "Project reference pending"}</small></div><span className="proposal-status">{row.stage}</span><button type="button" className="text-button" onClick={() => onOpen(row.id)}>Open Proposal <Icon name="arrow-up-right" size={14} /></button><small className="proposal-v1-next">{text(next.label, "Review Proposal")} · {displayDate(row.last_activity)}</small></article>;
}
