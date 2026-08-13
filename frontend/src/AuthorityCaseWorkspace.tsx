import { useEffect, useMemo, useState, type FormEvent } from "react";
import { api } from "./api";
import "./authority-case.css";

type Project = { id: string; project_number: string; project_name: string; activated_at?: string | null };
type CatalogItem = { id: string; code?: string; name_en?: string; name?: string; status?: string };
type CaseSummary = { case: Record<string, any>; external_body?: CatalogItem | null; jurisdiction?: CatalogItem | null; service_type?: CatalogItem | null; identifiers?: Record<string, any>[] };
type Workspace = CaseSummary & { policy_binding?: Record<string, any> | null; requirements: Record<string, any>[]; preparations: Record<string, any>[]; packages: Record<string, any>[]; cycles: Record<string, any>[]; findings: Record<string, any>[]; outcomes: Record<string, any>[]; state_separation: { internal: string; external: string } };

const label = (item?: CatalogItem | null) => item?.name_en || item?.name || item?.code || item?.id || "—";
const pretty = (value: unknown) => String(value ?? "—").replaceAll("_", " ");

export function AuthorityCaseWorkspacePage() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [bodies, setBodies] = useState<CatalogItem[]>([]);
  const [jurisdictions, setJurisdictions] = useState<CatalogItem[]>([]);
  const [services, setServices] = useState<CatalogItem[]>([]);
  const [selectedId, setSelectedId] = useState(() => window.location.pathname.split("/")[2] || "");
  const [form, setForm] = useState({ project_id: "", external_body_id: "", jurisdiction_id: "", service_type_id: "" });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const loadCases = async () => {
    const rows = await api<CaseSummary[]>("/api/authority-cases");
    setCases(rows);
    if (!selectedId && rows[0]?.case?.id) setSelectedId(rows[0].case.id);
  };
  const loadWorkspace = async (id: string) => {
    if (!id) { setWorkspace(null); return; }
    setWorkspace(await api<Workspace>(`/api/authority-cases/${id}`));
  };
  useEffect(() => {
    Promise.all([loadCases(), api<Project[]>("/api/projects"), api<CatalogItem[]>("/api/regulatory/external-bodies?status=ACTIVE"), api<CatalogItem[]>("/api/regulatory/jurisdictions?status=ACTIVE"), api<CatalogItem[]>("/api/regulatory/service-types?status=ACTIVE")]).then(([, projectRows, bodyRows, jurisdictionRows, serviceRows]) => {
      setProjects(projectRows); setBodies(bodyRows); setJurisdictions(jurisdictionRows); setServices(serviceRows);
      setForm((current) => ({ ...current, project_id: current.project_id || projectRows.find((row) => row.activated_at)?.id || projectRows[0]?.id || "", external_body_id: current.external_body_id || bodyRows[0]?.id || "", jurisdiction_id: current.jurisdiction_id || jurisdictionRows[0]?.id || "", service_type_id: current.service_type_id || serviceRows[0]?.id || "" }));
    }).catch((cause) => setError(cause instanceof Error ? cause.message : "Authority Case catalogs are unavailable."));
  }, []);
  useEffect(() => { loadWorkspace(selectedId).catch((cause) => setError(cause instanceof Error ? cause.message : "Authority Case workspace is unavailable.")); }, [selectedId]);

  const selectCase = (id: string) => { setSelectedId(id); setMessage(""); setError(""); window.history.pushState({}, "", `/authority-cases/${id}`); };
  const createCase = async (event: FormEvent) => {
    event.preventDefault(); if (busy) return;
    setBusy(true); setError(""); setMessage("");
    try {
      const result = await api<CaseSummary>("/api/authority-cases", { method: "POST", body: JSON.stringify({ ...form, idempotency_key: `authority-case-ui-${form.project_id}-${form.external_body_id}-${form.jurisdiction_id}-${form.service_type_id}` }) });
      selectCase(result.case.id); await loadCases(); setMessage("Explicit Authority Case created. No proposal, activation, or baseline event created it automatically.");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Case creation was blocked."); } finally { setBusy(false); }
  };
  const counts = useMemo(() => workspace ? [workspace.requirements.length, workspace.preparations.length, workspace.packages.length, workspace.cycles.length] : [0, 0, 0, 0], [workspace]);
  return <div className="authority-case-page">
    <div className="page-intro"><div><span className="eyebrow">PREPARATION + SUBMISSION LOOP · BOUNDED WORKSPACE</span><h2>Authority Cases</h2><p>Case-specific requirements, evidence, immutable preparation, explicit package manifests, deterministic precheck, human submit authorization, and externally confirmed outcomes.</p></div><span className="tag">No portal writes</span></div>
    <div className="synthetic-note">PORTAL AUTOMATION DEFERRED BY SCOPE · HUMAN SUBMISSION REQUIRED · EXTERNAL CONFIRMATION IS THE ONLY SUBMISSION CLAIM</div>
    {message && <div className="inline-message" role="status">{message}</div>}{error && <div className="error-banner">{error}</div>}
    <div className="authority-case-layout">
      <aside className="panel authority-case-list"><div className="panel-head"><div><span className="eyebrow">EXPLICIT CASE REGISTER</span><h3>Open cases</h3></div><span className="tag">{cases.length} total</span></div>{cases.length ? cases.map((item) => <button key={item.case.id} className={item.case.id === selectedId ? "authority-case-row selected" : "authority-case-row"} onClick={() => selectCase(item.case.id)}><b>{item.case.case_reference}</b><small>{label(item.external_body)} · {pretty(item.case.status)}</small><small>{label(item.jurisdiction)} · {label(item.service_type)}</small></button>) : <p className="muted">No cases yet. Start one with explicit canonical context.</p>}
        <form className="authority-case-create" onSubmit={createCase}><span className="eyebrow">START CASE</span><h3>Explicit context</h3><label>Activated project<select value={form.project_id} onChange={(event) => setForm({ ...form, project_id: event.target.value })} required><option value="">Select project</option>{projects.map((item) => <option key={item.id} value={item.id}>{item.project_number} · {item.project_name}{item.activated_at ? " · activated" : " · activation required"}</option>)}</select></label><label>External body<select value={form.external_body_id} onChange={(event) => setForm({ ...form, external_body_id: event.target.value })} required>{bodies.map((item) => <option key={item.id} value={item.id}>{label(item)}</option>)}</select></label><label>Jurisdiction<select value={form.jurisdiction_id} onChange={(event) => setForm({ ...form, jurisdiction_id: event.target.value })} required>{jurisdictions.map((item) => <option key={item.id} value={item.id}>{label(item)}</option>)}</select></label><label>Service type<select value={form.service_type_id} onChange={(event) => setForm({ ...form, service_type_id: event.target.value })} required>{services.map((item) => <option key={item.id} value={item.id}>{label(item)}</option>)}</select></label><button className="button-primary" disabled={busy || !form.project_id}>{busy ? "Creating…" : "Create Authority Case"}</button></form>
      </aside>
      <main>{workspace ? <>
        <section className="panel authority-case-hero"><div><span className="eyebrow">CASE {workspace.case.case_reference}</span><h3>{label(workspace.external_body)} · {label(workspace.service_type)}</h3><p>{label(workspace.jurisdiction)} · subject {workspace.case.subject_type} · {workspace.case.subject_id}</p></div><span className="status status-preparing">{pretty(workspace.case.status)}</span></section>
        <section className="authority-metric-grid">{[["Requirements", counts[0]], ["Preparations", counts[1]], ["Packages", counts[2]], ["Confirmed cycles", counts[3]]].map(([name, value]) => <div className="metric" key={String(name)}><span>{name}</span><strong>{value}</strong><small>Explicit records only</small></div>)}</section>
        <div className="two-col"><section className="panel"><div className="panel-head"><div><span className="eyebrow">STATE SEPARATION</span><h3>Internal / external</h3></div></div><div className="authority-state-row"><span>Internal case state</span><b>{pretty(workspace.state_separation.internal)}</b></div><div className="authority-state-row"><span>External confirmation state</span><b>{pretty(workspace.state_separation.external)}</b></div><div className="authority-state-row"><span>Policy binding</span><b>{workspace.policy_binding ? "RESOLVED · exact version pinned" : "NOT CONFIGURED"}</b></div></section><section className="panel"><div className="panel-head"><div><span className="eyebrow">ENGINEERING HANDOFF</span><h3>Approved baseline boundary</h3></div><span className="tag">Consumed by precheck</span></div><p className="authority-copy">The preparation revision pins an exact approved design baseline and members. Authority outcome never creates construction release.</p><div className="authority-state-row"><span>Preparation state</span><b>{workspace.preparations.length ? pretty(workspace.preparations[workspace.preparations.length - 1].authority_state) : "NOT STARTED"}</b></div></section></div>
        <section className="panel table-panel"><div className="panel-head authority-panel-pad"><div><span className="eyebrow">REQUIREMENT INSTANCES</span><h3>Applicability and evidence readiness</h3></div><span className="tag">No latest fallback</span></div>{workspace.requirements.length ? <table><thead><tr><th>Instance</th><th>Applicability</th><th>Status</th><th>Reason</th></tr></thead><tbody>{workspace.requirements.map((item) => <tr key={item.id}><td><b>{item.id.slice(0, 8)}</b><small>{item.requirement_definition_id || item.policy_item_id}</small></td><td>{pretty(item.applicability)}</td><td><span className="status status-preparing">{pretty(item.status)}</span></td><td>{item.reason || "—"}</td></tr>)}</tbody></table> : <p className="authority-empty">Requirements are not initialized. Resolve an exact active policy before preparation.</p>}</section>
        <div className="two-col"><section className="panel"><div className="panel-head"><div><span className="eyebrow">PREPARATION REVISIONS</span><h3>Immutable snapshots</h3></div></div>{workspace.preparations.length ? workspace.preparations.map((item) => <div className="authority-list-line" key={item.id}><b>R{item.authority_revision_number}</b><span>{pretty(item.authority_state)}</span><small>{item.authority_snapshot_hash || "Hash pending"}</small></div>) : <p className="muted">No preparation revision yet.</p>}</section><section className="panel"><div className="panel-head"><div><span className="eyebrow">SUBMISSION CYCLES</span><h3>External confirmation</h3></div></div>{workspace.cycles.length ? workspace.cycles.map((item) => <div className="authority-list-line" key={item.id}><b>C{item.cycle_number}</b><span>{pretty(item.status)}</span><small>Package hash pinned</small></div>) : <p className="muted">No confirmed external cycle. Authorization remains pending confirmation.</p>}</section></div>
        <section className="panel"><div className="panel-head"><div><span className="eyebrow">FINDINGS + OUTCOMES</span><h3>Resubmission loop</h3></div><span className="tag">Human controlled</span></div><div className="authority-state-row"><span>Captured findings</span><b>{workspace.findings.length}</b></div><div className="authority-state-row"><span>Recorded outcomes</span><b>{workspace.outcomes.length}</b></div><p className="authority-copy">Findings can produce a new preparation revision and package. The interface does not submit to an authority or infer acceptance.</p></section>
      </> : <section className="panel authority-empty"><h3>Select an Authority Case</h3><p>Use the explicit case register to inspect the pinned regulatory context and execution state.</p></section>}</main>
    </div>
  </div>;
}
