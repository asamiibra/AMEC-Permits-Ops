import { useEffect, useState } from "react";
import { api } from "./api";

type Source18Overview = {
  office?: { office_code: string; name_en: string };
  engineers?: Array<{ id: string; display_name: string; discipline: string; regulatory_profile_state: string; evidence_currentness: string }>;
  readiness?: { required_count: number | null; regulator_counted: number | null; buffer_or_gap: number | null; currentness: string; source_policy_version: string | null };
  registration_artifacts?: Array<{ id: string; artifact_type: "CERTIFICATE" | "DOCUMENT"; version_number: number; status: string; source_document_version_id: string | null }>;
};

export function Source18CommitteePage() {
  const [officeId, setOfficeId] = useState(() => sessionStorage.getItem("source18-office-id") || "");
  const [overview, setOverview] = useState<Source18Overview | null>(null);
  const [error, setError] = useState("");
  const load = () => {
    if (!officeId.trim()) { setError("Enter the canonical office ID to load readiness."); return; }
    sessionStorage.setItem("source18-office-id", officeId.trim());
    setError("");
    api<Source18Overview>(`/api/source18/offices/${encodeURIComponent(officeId.trim())}/overview`).then(setOverview).catch((cause) => setError(cause instanceof Error ? cause.message : "Readiness is unavailable."));
  };
  useEffect(() => { if (officeId) load(); }, []);
  const readiness = overview?.readiness;
  return (
    <div className="source18-page" data-testid="source18-committee-page">
      <section className="home-hero"><div><span className="eyebrow">SOURCE-18 · ENGINEERS ACCEPTANCE COMMITTEE</span><h2>Office regulatory readiness</h2><p>Versioned evidence, staffing readiness, and human-controlled committee workflows.</p></div><div className="home-hero-note"><span className="dot green" /> No regulator outcome is inferred</div></section>
      <section className="home-section" aria-labelledby="source18-office-heading"><div className="home-section-heading"><div><span className="eyebrow">CANONICAL OFFICE</span><h3 id="source18-office-heading">Load office overview</h3></div><span className="muted">Source currentness is explicit</span></div><div style={{ display: "flex", gap: 12, alignItems: "end", flexWrap: "wrap" }}><label>Office ID<input aria-label="Office ID" value={officeId} onChange={(event) => setOfficeId(event.target.value)} /></label><button type="button" onClick={load}>Load readiness</button></div>{error && <p role="alert" className="truthful-empty">{error}</p>}</section>
      {overview && <><section className="home-widgets" aria-label="Source-18 readiness summary"><article className="home-widget"><span className="eyebrow">READINESS</span><h3>{overview.office?.name_en || overview.office?.office_code}</h3><div className="home-metric-row"><div><strong>{readiness?.required_count ?? "—"}</strong><span>Required</span></div><div><strong>{readiness?.regulator_counted ?? "—"}</strong><span>Regulator counted</span></div><div><strong>{readiness?.buffer_or_gap ?? "—"}</strong><span>Buffer / gap</span></div></div><p className="muted">Policy: {readiness?.source_policy_version || "UNKNOWN"} · Currentness: {readiness?.currentness || "UNKNOWN"}</p></article></section><section className="home-section" aria-labelledby="source18-registration-heading"><div className="home-section-heading"><div><span className="eyebrow">OFFICE ENROLMENT</span><h3 id="source18-registration-heading">Current certificate and document versions</h3></div><span className="muted">Separate authority artifacts</span></div><div className="home-mini-list">{(overview.registration_artifacts || []).map((artifact) => <div key={artifact.id}><strong>{artifact.artifact_type === "CERTIFICATE" ? "Office enrolment certificate" : "Office enrolment document"}</strong> · version {artifact.version_number} · {artifact.status} · source {artifact.source_document_version_id || "UNKNOWN"}</div>)}</div></section><section className="home-section" aria-labelledby="source18-engineers-heading"><div className="home-section-heading"><div><span className="eyebrow">ENGINEERING</span><h3 id="source18-engineers-heading">Engineer regulatory profiles</h3></div><span className="muted">Raw PII is hidden</span></div><div className="home-mini-list">{(overview.engineers || []).map((engineer) => <div key={engineer.id}><strong>{engineer.display_name}</strong> · {engineer.discipline} · profile {engineer.regulatory_profile_state} · evidence {engineer.evidence_currentness}</div>)}</div></section><section className="home-section" aria-label="Source-18 workflow modes"><div className="home-stage-grid"><div className="home-stage-card"><span className="home-stage-title">Counter process</span><span className="home-stage-description">Engineer update remains separate from regulator-counted state.</span></div><div className="home-stage-card"><span className="home-stage-title">Committee panel</span><span className="home-stage-description">Responsible Engineer changes and renewals require versioned policy and Owner release.</span></div></div></section></>}
    </div>
  );
}
