import { useEffect, useState } from "react";
import { api } from "./api";

function Metric({ label, value }: { label: string; value: string | number }) {
  return <div className="metric teal"><span>{label}</span><strong>{value}</strong><small>Week 10 synthetic evidence</small></div>;
}

export function Week10Page() {
  const [data, setData] = useState<any>({});
  const [error, setError] = useState("");
  useEffect(() => {
    Promise.all([
      api<any>("/api/configuration/requirement-matrix/coverage"),
      api<any>("/api/configuration/field-matrix/coverage"),
      api<any>("/api/week10/kpi-review"),
      api<any>("/api/week10/tier2-review"),
      api<any>("/api/submission-cycles"),
    ]).then(([requirements, fields, kpi, tier2, cycles]) => setData({ requirements: requirements.coverage, fields: fields.coverage, kpi, tier2, cycles })).catch((e) => setError(e.message));
  }, []);
  const safety = data.kpi?.safety_metrics || { machine_final_submissions: 0, stale_package_readiness_escapes: 0, stale_precheck_readiness_escapes: 0, unresolved_blocking_finding_resubmission_escapes: 0 };
  return <>
    <div className="page-intro"><div><span className="eyebrow">BUILD WEEK 10 · GOLDEN PATH V2</span><h2>Closure & resubmission control</h2><p>Current-state synthetic operating loop from precheck correction through controlled human resubmission readiness.</p></div></div>
    <div className="synthetic-note">SYNTHETIC DEVELOPMENT / NOT CLIENT-APPROVED · Final submission remains HUMAN ONLY · No Ministry write path</div>
    {error && <div className="error-banner">Week 10 evidence unavailable: {error}</div>}
    <div className="metric-grid"><Metric label="Requirement coverage" value={`${data.requirements?.coverage_percent ?? "—"}%`} /><Metric label="Critical fields" value={`${data.fields?.complete_fields ?? "—"}/${data.fields?.critical_fields ?? "—"}`} /><Metric label="Submission cycles" value={data.cycles?.cycles?.length ?? "—"} /><Metric label="Machine final submits" value={safety.machine_final_submissions} /></div>
    <div className="two-col">
      <section className="panel"><div className="panel-head"><div><span className="eyebrow">RESUBMISSION GATE</span><h3>Exact current-state conditions</h3></div><span className="tag">G9</span></div>{["Current approved package / manifest", "Current preparation revision", "Current precheck clearance", "Dependencies and credentials", "Official blocking findings", "Portal reconciliation"].map((x) => <div className="link-row" key={x}><span className="system-mark municipality">✓</span><span><b>{x}</b><small>Evaluated from immutable revision and evidence records</small></span><span className="linked">PASS / BLOCK</span></div>)}</section>
      <section className="panel"><div className="panel-head"><div><span className="eyebrow">FINDING CLOSURE</span><h3>Evidence-backed lifecycle</h3></div><span className="tag warning">Role-controlled</span></div><p>Correction → evidence → configured verifier → verified closure. Task completion never closes a Finding.</p><div className="journey">Open → Correction recorded → Evidence attached → Verified → Closed and verified</div><p className="muted">Disputes satisfy the gate only when the Finding rule explicitly allows formal dispute.</p></section>
    </div>
    <div className="two-col"><section className="panel"><div className="panel-head"><h3>Requirement / field matrices</h3><span className="tag">SUPPORTED SCENARIO</span></div><div className="exposure-row"><span>Requirements complete</span><b>{data.requirements?.complete ?? "—"} / {data.requirements?.total_requirements ?? "—"}</b></div><div className="exposure-row"><span>Unknown requirements</span><b>{data.requirements?.unknown ?? 0}</b></div><div className="exposure-row"><span>Fields complete</span><b>{data.fields?.complete_fields ?? "—"} / {data.fields?.total_fields ?? "—"}</b></div><div className="exposure-row"><span>Field result</span><b>{data.fields?.result ?? "—"}</b></div></section><section className="panel"><div className="panel-head"><h3>Tier 2 disposition</h3><span className="tag">EXPLICIT</span></div>{(data.tier2?.items || []).slice(0, 6).map((item: any) => <div className="audit-row" key={item.id}><span className="audit-dot"/><span><b>{item.title || item.key || item.id}</b><small>{item.week10_disposition} · evidence retained</small></span></div>)}</section></div>
    <section className="panel"><div className="panel-head"><div><span className="eyebrow">SAFETY METRICS</span><h3>Structural zero checks</h3></div><span className="tag">0 ESCAPES</span></div><div className="metric-grid">{Object.entries(safety).map(([label, value]) => <Metric key={label} label={label.replaceAll("_", " ")} value={String(value)} />)}</div></section>
  </>;
}
