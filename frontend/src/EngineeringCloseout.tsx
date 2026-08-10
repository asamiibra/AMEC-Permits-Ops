import { useEffect, useState } from "react";
import { api } from "./api";

export function EngineeringCloseoutPage() {
  const [projects, setProjects] = useState<any[]>([]);
  const [projectId, setProjectId] = useState("");
  const [reviews, setReviews] = useState<any[]>([]);
  const [readiness, setReadiness] = useState<any>(null);
  const [error, setError] = useState("");
  useEffect(() => { api<any[]>("/api/projects").then(items => { setProjects(items); setProjectId(items[0]?.id || ""); }).catch(() => setError("Shared project register is unavailable.")); }, []);
  useEffect(() => { if (!projectId) return; Promise.all([api<any[]>(`/api/projects/${projectId}/engineering-reviews`), api<any>(`/api/projects/${projectId}/handover-readiness`)]).then(([r, h]) => { setReviews(r); setReadiness(h); }).catch(() => setError("Engineering or handover context is unavailable.")); }, [projectId]);
  const review = reviews[0];
  return <div className="workflow-page expansion-workspace">
    <div className="page-intro"><div><span className="eyebrow">E5 · E6 BOUNDED WORKFLOW</span><h2>Engineering & Commercial Closeout</h2><p>Project-context views over shared evidence. Synthetic implementation only; professional, finance, send, payment, and release authority remain human-owned.</p></div><span className="tag">Prototype / development only</span></div>
    <div className="synthetic-note">SYNTHETIC / DEMO / NOT CLIENT APPROVED · NO ACCOUNTING WRITE · HUMAN SEND · NO AUTOMATIC PROJECT CLOSE</div>
    <section className="panel expansion-context"><div><b>Project context</b><small>Canonical project identity anchors both assistants.</small></div><select aria-label="Project context" value={projectId} onChange={e => setProjectId(e.target.value)}>{projects.map(p => <option key={p.id} value={p.id}>{p.project_number} · {p.project_name}</option>)}</select></section>
    {error && <div className="error-banner">{error}</div>}
    <div className="two-col expansion-columns">
      <section className="panel"><div className="panel-head"><div><span className="eyebrow">ENGINEERING REVIEW ASSISTANT</span><h3>Engineering Review</h3></div><span className="tag">ADVISORY ONLY</span></div>
        <div className="expansion-status"><span>Review state</span><b>{review?.status || "CREATED / CONFIGURE SCOPE"}</b></div>
        <div className="expansion-status"><span>Drawing version</span><b>{review?.current_drawing_version_id || "PINNED DOCUMENT VERSION REQUIRED"}</b></div>
        <div className="expansion-status"><span>Review scope / regulations</span><b>{review?.current_scope_id ? "CONFIGURED / HUMAN APPLICABILITY" : "SCOPE REQUIRED"}</b></div>
        <div className="expansion-callout"><b>AI PROPOSED ≠ ENGINEER ACCEPTED</b><p>Candidate discrepancies must cite the pinned drawing and controlled regulation evidence. AI cannot certify, approve, stamp, or close a professional comment.</p></div>
        <div className="expansion-chip-row"><span className="tag">Compliance Review Sheet</span><span className="tag">Comment Sheet</span><span className="tag">Observed Block-Time</span></div>
        <h4>Revision history</h4><p className="muted">Drawing V1 → numbered comments → corrected drawing V2 → material-change invalidation → re-review.</p>
      </section>
      <section className="panel"><div className="panel-head"><div><span className="eyebrow">E6 · FINANCE / HANDOVER</span><h3>Commercial Closeout</h3></div><span className="tag">TRACK / DRAFT / HANDOFF</span></div>
        <div className="expansion-status"><span>Invoice decision</span><b>Human decision / configured rule</b></div>
        <div className="expansion-status"><span>Finance route</span><b>General finance handoff</b></div>
        <div className="expansion-status"><span>Invoice follow-up</span><b>Due date unknown / needs review when unconfigured</b></div>
        <div className="expansion-status"><span>Handover readiness</span><b>{readiness?.evaluation?.state?.replaceAll("_", " ") || "Needs review"}</b></div>
        <div className="expansion-callout"><b>HUMAN_SEND · NO ACCOUNTING WRITE</b><p>Invoice issue/payment evidence is separate from internal readiness. Handover output requires human approval and release evidence; release does not close the project.</p></div>
        <div className="expansion-chip-row"><span className="tag">Invoice Follow-up Sheet</span><span className="tag">Handover Form / Output</span><span className="tag">Client Draft</span></div>
      </section>
    </div>
    <section className="panel"><div className="panel-head"><div><span className="eyebrow">BOUNDARY REGISTER</span><h3>What remains outside this gate</h3></div><span className="tag warning">DEFERRED</span></div><div className="boundary-grid">{["Professional certification / stamping", "NFPA or Qatar authority claim without approved edition", "DWF/CAD semantic automation", "Accounting ledger posting", "Payment processing", "Autonomous email send", "Government final submission", "Automatic project closure"].map(item => <div key={item}><span>—</span><b>{item}</b></div>)}</div></section>
  </div>;
}
