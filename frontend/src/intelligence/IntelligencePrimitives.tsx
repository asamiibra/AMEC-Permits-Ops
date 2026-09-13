import { useEffect, useRef } from "react";
import { Icon } from "../Icon";
import { asList, asRecord, displayDate, labelize, text } from "../features/proposals/helpers";
import type { JsonRecord } from "../features/proposals/types";

export type IntelligenceState = "CURRENT" | "STALE" | "INVALID";

export function TrustStateBadge({ state }: { state: string }) {
  const normalized = state.toUpperCase();
  const className = normalized === "CANDIDATE" ? "candidate" : normalized === "VERIFIED" || normalized === "CANONICAL" ? "verified" : "neutral";
  return <span className={`intelligence-badge ${className}`}><Icon name={normalized === "CANDIDATE" ? "sparkles" : normalized === "VERIFIED" || normalized === "CANONICAL" ? "check" : "current"} size={13} /> {labelize(normalized)}</span>;
}
export function WorkProductStateBadge({ state }: { state: string }) {
  const normalized = state.toUpperCase() as IntelligenceState;
  return <span className={`intelligence-badge work-product-${normalized.toLowerCase()}`}><Icon name={normalized === "CURRENT" ? "current" : normalized === "STALE" ? "alert" : "close"} size={13} /> {normalized}</span>;
}

export function CandidateAssertionView({ assertion }: { assertion: JsonRecord }) {
  return <article className="intelligence-assertion" data-testid="candidate-assertion"><div className="intelligence-card-head"><div><span className="eyebrow">MACHINE OBSERVATION</span><h4>{text(assertion.display_value ?? assertion.assertion_code, "Candidate assertion")}</h4></div><TrustStateBadge state={text(assertion.trust_state ?? assertion.status, "CANDIDATE")} /></div><p>{text(assertion.provenance_summary, "Candidate only. A human must review the source evidence before it can influence business state.")}</p><small>Producer: {text(assertion.producer_kind, "Not recorded")} · Confidence: {text(assertion.confidence, "Not supplied")}</small></article>;
}

export function EvidenceCitationList({ citations }: { citations: JsonRecord[] }) {
  if (!citations.length) return <p className="muted">No citations were supplied.</p>;
  return <ul className="citation-list">{citations.map((citation, index) => <li key={text(citation.id, `citation-${index}`)}><Icon name="library" size={14} /><span><b>{text(citation.document_title ?? citation.document_version_id, "Governed evidence")}</b><small>{text(citation.locator ?? citation.page_or_section, "Evidence locator not captured")}</small></span><button type="button" className="text-button" onClick={() => window.dispatchEvent(new CustomEvent("proposal:evidence-open", { detail: citation }))}>View evidence</button></li>)}</ul>;
}

export function IntelligenceWorkProductCard({ workProduct }: { workProduct: JsonRecord }) {
  const state = text(workProduct.state ?? workProduct.currentness_state, "CURRENT").toUpperCase();
  return <article className="intelligence-work-product" data-testid="intelligence-work-product"><div className="intelligence-card-head"><div><span className="eyebrow">{text(workProduct.output_class, "ANALYSIS")}</span><h4>{text(workProduct.skill_name ?? workProduct.skill_id, "Proposal Intelligence work product")}</h4></div><WorkProductStateBadge state={state} /></div>{state === "STALE" && <div className="staleness-banner" role="status">This analysis used evidence or business state that is no longer current.</div>}{state === "INVALID" && <div className="staleness-banner invalid" role="status">This work product is invalid for current decisions and must not be treated as guidance.</div>}<p>{text(workProduct.summary ?? workProduct.output_summary, "No analysis summary was supplied.")}</p><small>Created: {displayDate(workProduct.created_at)} · Review required · No protected action is executed.</small><EvidenceCitationList citations={asList(workProduct.citations)} /></article>;
}

export function IntelligenceUnavailableBoundary({ items = [] }: { items?: JsonRecord[] }) {
  return <section className="intelligence-panel" aria-label="Proposal Intelligence"><div className="panel-head"><div><span className="eyebrow">PROPOSAL INTELLIGENCE</span><h3>Evidence-aware assistance</h3></div><span className="tag">READ-ONLY</span></div>{items.length ? items.map((item, index) => item.output_class || item.skill_id ? <IntelligenceWorkProductCard key={text(item.id, `work-product-${index}`)} workProduct={item} /> : <CandidateAssertionView key={text(item.id, `assertion-${index}`)} assertion={item} />) : <div className="intelligence-empty"><Icon name="sparkles" size={18} /><div><b>No executable Proposal skill is registered</b><p>When governed Proposal analysis exists, this surface will show candidates, citations, and currentness here. No decorative Analyze, Generate, or Chat action is presented.</p></div></div>}</section>;
}

export function ConfirmActionDialog({ title, consequence, confirmLabel, onConfirm, onCancel }: { title: string; consequence: string; confirmLabel: string; onConfirm: () => void; onCancel: () => void }) {
  const confirmRef = useRef<HTMLButtonElement>(null);
  useEffect(() => { confirmRef.current?.focus(); const onKeyDown = (event: KeyboardEvent) => { if (event.key === "Escape") onCancel(); }; window.addEventListener("keydown", onKeyDown); return () => window.removeEventListener("keydown", onKeyDown); }, [onCancel]);
  return <div className="proposal-dialog-backdrop" role="presentation"><section className="proposal-dialog" role="dialog" aria-modal="true" aria-labelledby="proposal-dialog-title"><span className="eyebrow">HUMAN DECISION REQUIRED</span><h3 id="proposal-dialog-title">{title}</h3><p>{consequence}</p><div className="proposal-dialog-actions"><button type="button" className="button-secondary" onClick={onCancel}>Cancel</button><button ref={confirmRef} type="button" className="button-primary" onClick={onConfirm}>{confirmLabel}</button></div></section></div>;
}
