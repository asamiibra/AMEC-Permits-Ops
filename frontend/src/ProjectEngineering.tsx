import { useEffect, useState } from "react";
import { api } from "./api";
import { Icon } from "./Icon";

type Project = { id: string; project_number: string; project_name: string; activated_at?: string | null };
type Summary = { project: Project & { activated: boolean }; work_packages: any[]; deliverables: any[]; baselines: any[]; authority_approval_created: boolean; construction_release_created: boolean; submission_package_created: boolean };

export function ProjectEngineeringPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState("");
  const [summary, setSummary] = useState<Summary | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = async (id: string) => {
    if (!id) return;
    try { setSummary(await api<Summary>(`/api/projects/${id}/engineering`)); setError(""); } catch { setError("Project Engineering context is unavailable or the project is not activated."); }
  };
  useEffect(() => { api<Project[]>("/api/projects").then(items => { setProjects(items); const first = items[0]?.id || ""; setProjectId(first); load(first); }).catch(() => setError("Canonical Project register is unavailable.")); }, []);
  const createPackage = async () => {
    if (!summary || busy) return;
    setBusy(true); setMessage("");
    try { await api(`/api/projects/${summary.project.id}/engineering/work-packages`, { method: "POST", headers: { "Content-Type": "application/json", "X-Dev-Role": "RESPONSIBLE_ENGINEER", "X-Dev-Actor": "engineering-ui" }, body: JSON.stringify({ package_ref: `WP-${Date.now()}`, title: "Project engineering work package", discipline: "GENERAL" }) }); setMessage("Work package created. Upload, review, approval, and baseline states remain explicit."); await load(summary.project.id); } catch (cause) { setError(cause instanceof Error ? cause.message : "Work package creation was blocked."); } finally { setBusy(false); }
  };
  return <div className="workflow-page expansion-workspace">
    <div className="page-intro"><div><span className="eyebrow">PROJECT ENGINEERING · APPROVED DESIGN BASELINE</span><h2>Engineering Works</h2><p>Exact deliverables, business revisions, canonical DocumentVersions, review findings, professional approval, technical evidence, and immutable AMEC baselines.</p></div><div className="detail-actions"><button className="button-secondary" onClick={() => { window.history.pushState({}, "", "/engineering/drawing-review"); window.dispatchEvent(new PopStateEvent("popstate")); }}>Open Drawing Review</button><span className="tag">Human-controlled</span></div></div>
    <div className="synthetic-note">AMEC APPROVED DESIGN BASELINE ≠ AUTHORITY APPROVAL ≠ CONSTRUCTION RELEASE · AI CANNOT APPROVE, SIGN, OR STAMP</div>
    <section className="panel expansion-context"><div><b>Canonical Project</b><small>Engineering is gated by explicit Project Activation.</small></div><select aria-label="Project context" value={projectId} onChange={event => { setProjectId(event.target.value); load(event.target.value); }}>{projects.map(project => <option key={project.id} value={project.id}>{project.project_number} · {project.project_name}</option>)}</select></section>
    {message && <div className="inline-message" role="status">{message}</div>}{error && <div className="error-banner">{error}</div>}
    {summary && <>
      <section className="panel"><div className="panel-head"><div><span className="eyebrow">{summary.project.activated ? "ACTIVATED PROJECT" : "ACTIVATION REQUIRED"}</span><h3>{summary.project.project_name}</h3></div><button className="button-primary" onClick={createPackage} disabled={busy || !summary.project.activated}>{busy ? "Creating…" : "Create work package"}</button></div><div className="expansion-status"><span>Project gate</span><b>{summary.project.activated ? "PASS · explicit activation recorded" : "BLOCKED · activate through Admin Contract"}</b></div><div className="expansion-status"><span>Work packages / deliverables</span><b>{summary.work_packages.length} / {summary.deliverables.length}</b></div><div className="expansion-status"><span>Approved design baselines</span><b>{summary.baselines.filter(item => item.status === "APPROVED").length} approved · {summary.baselines.filter(item => item.status === "CANDIDATE").length} candidate</b></div></section>
      <div className="two-col expansion-columns"><section className="panel"><div className="panel-head"><div><span className="eyebrow">EXACT BUSINESS REVISIONS</span><h3>Deliverables</h3></div><span className="tag">Immutable after approval</span></div>{summary.deliverables.length ? summary.deliverables.map(item => <div className="preparation-source" key={item.id}><span><Icon name="arrow-up-right" size={15} /></span><div><b>{item.deliverable_ref} · {item.title}</b><small>{item.discipline} · {item.status} · current revision is explicit, never inferred from latest file</small></div></div>) : <p className="muted">No project deliverables yet.</p>}</section><section className="panel"><div className="panel-head"><div><span className="eyebrow">BASELINE HISTORY</span><h3>Design baselines</h3></div><span className="tag">Exact manifest</span></div>{summary.baselines.length ? summary.baselines.map(item => <div className="preparation-source" key={item.id}><span><Icon name={item.status === "APPROVED" ? "completion" : "empty"} size={15} /></span><div><b>{item.baseline_ref}</b><small>{item.status} · {item.manifest_hash || "Manifest pending validation"}</small></div></div>) : <p className="muted">No candidate baseline yet.</p>}</section></div>
      <section className="panel"><div className="panel-head"><div><span className="eyebrow">BOUNDARY REGISTER</span><h3>Future layers remain separate</h3></div><span className="tag warning">OUT OF SCOPE</span></div><div className="boundary-grid"><div><span>—</span><b>Authority approval: not created</b></div><div><span>—</span><b>Construction release: not created</b></div><div><span>—</span><b>Submission package: not created</b></div><div><span>—</span><b>Future Preparation + Submission consumes exact baseline members</b></div></div></section>
    </>}
  </div>;
}
