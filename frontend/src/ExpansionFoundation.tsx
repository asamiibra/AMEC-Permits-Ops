import { useEffect, useState } from "react";
import { api } from "./api";

type Foundation = { fixture_version: string; fixture_manifest_hash: string; predecessor: { version: string }; manifest: { source_families: string[]; scenarios: string[] } };

export function ExpansionFoundation() {
  const [requirements, setRequirements] = useState<any>(null);
  const [clarifications, setClarifications] = useState<any>(null);
  const [capabilities, setCapabilities] = useState<any>(null);
  const [fixture, setFixture] = useState<Foundation | null>(null);
  useEffect(() => {
    Promise.all([api<any>("/api/expansion/requirements"), api<any>("/api/expansion/clarifications"), api<any>("/api/expansion/capabilities"), api<Foundation>("/api/expansion/fixture")])
      .then(([r, c, a, f]) => { setRequirements(r); setClarifications(c); setCapabilities(a); setFixture(f); }).catch(() => {});
  }, []);
  return <div className="workflow-page">
    <div className="page-intro"><div><span className="eyebrow">EXPANSION FOUNDATION · E0/E1</span><h2>Stage 1 v2.6 scope registry</h2><p>Governance and shared-domain foundation only. No downstream capability is live or owner-approved.</p></div></div>
    <div className="synthetic-note admin-banner">AMEC Engineering · SYNTHETIC ONLY · STAGE 2 APPROVAL NOT PRESENT · NO EXTERNAL ACTIONS</div>
    <div className="metric-grid">
      <div className="metric blue"><span>A12B owner-session requirements</span><strong>{requirements?.count ?? "—"}</strong><small>Registry controlled</small></div>
      <div className="metric orange"><span>A15 clarifications</span><strong>{clarifications?.count ?? "—"}</strong><small>Safe defaults active</small></div>
      <div className="metric teal"><span>Bounded assistants</span><strong>{capabilities?.assistant_ids?.length ?? "—"}</strong><small>No autonomous agents</small></div>
      <div className="metric red"><span>Stage 2 approval</span><strong>NONE</strong><small>Explicitly undecided</small></div>
    </div>
    <div className="two-col">
      <section className="panel"><div className="panel-head"><div><span className="eyebrow">FIXTURE SUCCESSOR</span><h3>{fixture?.fixture_version ?? "Loading…"}</h3></div><span className="tag">PREDECESSOR {fixture?.predecessor?.version ?? "—"}</span></div><p>Source families: {fixture?.manifest?.source_families?.join(" · ") || "Loading…"}</p><p>Scenarios: {fixture?.manifest?.scenarios?.join(" · ") || "Loading…"}</p><small className="muted">Manifest: {fixture?.fixture_manifest_hash || "—"}</small></section>
      <section className="panel"><span className="eyebrow">CAPABILITY BOUNDARY</span><h3>{capabilities?.capabilities?.length ?? "—"} metadata registrations</h3><p>Assistant identities are views over shared evidence, approvals, tasks, audit, lineage, and validity controls.</p><div className="mini-list">{(capabilities?.assistant_ids || []).map((id: string) => <div key={id}><b>{id}</b><span className="tag">UNDECIDED_STAGE2</span></div>)}</div></section>
    </div>
  </div>;
}
