import { useEffect, useMemo, useState } from "react";
import { api } from "./api";
import { Icon } from "./Icon";

export const PHASE4_DECISIONS = [
  "ACCEPT",
  "CORRECT",
  "DEFER",
  "MARK_OUT_OF_SCOPE",
  "RESOLVE_RELATIONSHIP",
  "REJECT",
] as const;

type Decision = (typeof PHASE4_DECISIONS)[number];
type ReviewItem = {
  id: string;
  envelope_id: string;
  root_event_id: string;
  document_version_id?: string | null;
  source_mode: string;
  classifier_version: string;
  rules_version: string;
  taxonomy_revision: string;
  module_truth_contract_sha: string;
  corpus_app_contract_sha: string;
  axes_json?: Record<string, unknown>;
  record_version: number;
  status: string;
};

type Props = { role: string };

function text(value: unknown, fallback = "Not supplied by the server") {
  if (typeof value === "string" && value.trim()) return value;
  if (typeof value === "number") return String(value);
  return fallback;
}

function list(value: unknown): unknown[] {
  return Array.isArray(value) ? value : value == null ? [] : [value];
}

function label(value: string) {
  return value.replaceAll("_", " ").toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function persona(role: string) {
  if (role === "PROCESS_CHAMPION" || role === "COMMERCIAL_APPROVER") return "Business Development";
  if (role === "RESPONSIBLE_ENGINEER" || role === "REQUIREMENT_STEWARD") return "Engineering";
  return "Owner";
}

function idempotencyKey() {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `phase4-ui-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function detail(value: unknown) {
  if (typeof value === "string") return value;
  if (value && typeof value === "object") return JSON.stringify(value);
  return "Not supplied by the server";
}

function extract(item: ReviewItem) {
  const axes = item.axes_json || {};
  const scope = axes.scope && typeof axes.scope === "object" ? axes.scope as Record<string, unknown> : {};
  const evidence = list(axes.bounded_evidence ?? axes.evidence ?? axes.evidence_refs);
  const links = list(axes.candidate_links ?? axes.deep_links ?? axes.work_issue_notification_links);
  const contradictions = list(axes.contradictions ?? axes.conflicts);
  const classification = axes.classification_proposal ?? axes.proposals ?? axes.classification_axes ?? axes;
  const relationship = axes.relationship_resolution && typeof axes.relationship_resolution === "object"
    ? axes.relationship_resolution
    : {
        source_entity_id: text(axes.source_entity_id, item.root_event_id),
        candidate_entity_id: text(axes.candidate_entity_id, text(scope.scope_id, "server-supplied candidate")),
        relationship_type: text(axes.relationship_type, "SERVER_SUPPLIED_RELATIONSHIP"),
        resolution: "BOUND_BY_REVIEWER",
      };
  return {
    axes,
    scope,
    reason: text(axes.review_reason ?? axes.reason, "Classification requires human review before any authority or projection step."),
    evidence,
    classification,
    contradictions,
    links,
    currentness: text(axes.currentness ?? axes.version_state, `Record version ${item.record_version}; server precondition applies.`),
    precedence: text(axes.source_precedence, "Accepted Phase3C Module Truth rules (server supplied)."),
    relationship,
    deferred: item.status === "DEFERRED" || Boolean(axes.deferred),
    outOfScope: item.status === "OUT_OF_SCOPE" || Boolean(axes.out_of_scope),
    unsupported: text(axes.unsupported_capability_state ?? axes.unsupported_capability, "No unsupported capability was supplied."),
    scopeType: text(scope.scope_type ?? axes.scope_type, "PROJECT"),
    scopeId: text(scope.scope_id ?? axes.scope_id, "synthetic-project-001"),
  };
}

function renderValue(value: unknown) {
  if (value && typeof value === "object") return JSON.stringify(value);
  return text(value);
}

export function Phase4ReviewPage({ role }: Props) {
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [mutationError, setMutationError] = useState("");
  const [pending, setPending] = useState<Decision | "">("");
  const [confirmation, setConfirmation] = useState("");

  const load = () => {
    setLoading(true);
    setError("");
    api<{ items: ReviewItem[] }>("/api/phase4/review-queue")
      .then((response) => {
        setItems(response.items || []);
        setSelectedId((current) => current && response.items.some((item) => item.id === current) ? current : response.items[0]?.id || "");
      })
      .catch((cause) => setError(cause instanceof Error ? cause.message : "Phase4 review queue could not be loaded."))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [role]);

  const selected = useMemo(() => items.find((item) => item.id === selectedId) || null, [items, selectedId]);
  const view = selected ? extract(selected) : null;

  const submit = (decision: Decision) => {
    if (!selected || pending) return;
    setPending(decision);
    setMutationError("");
    setConfirmation("");
    const payload = {
      decision_id: idempotencyKey(),
      classification_envelope_id: selected.id,
      decision,
      actor_id: `synthetic-${role.toLowerCase()}`,
      capability: decision === "RESOLVE_RELATIONSHIP" ? "PHASE4_RESOLVE_RELATIONSHIP" : "PHASE4_REVIEW_DECISION",
      scope_type: view?.scopeType || "PROJECT",
      scope_id: view?.scopeId || "synthetic-project-001",
      record_version: selected.record_version,
      idempotency_key: idempotencyKey(),
      corrections_json: decision === "RESOLVE_RELATIONSHIP" ? [view?.relationship] : [],
    };
    api<{ decision: Decision }>("/api/phase4/review-decisions", { method: "POST", body: JSON.stringify(payload) })
      .then((response) => {
        setConfirmation(`${label(response.decision)} recorded by the server. Refreshing the review queue.`);
        load();
      })
      .catch((cause) => {
        const message = cause instanceof Error ? cause.message : "The review decision could not be recorded.";
        setMutationError(message.includes("409") ? "STALE REVIEW — refresh required before submitting another decision." : message.includes("401") || message.includes("403") ? "Authorization denied — the server did not accept this review action." : message);
      })
      .finally(() => setPending(""));
  };

  return <div className="phase4-review-page">
    <div className="page-intro">
      <div>
        <span className="eyebrow">PHASE4 · AMEC EVIDENCE REVIEW</span>
        <h2>Review classification evidence</h2>
        <p>Review bounded server-provided evidence before any VerifiedAssertion or typed projection authority path.</p>
      </div>
        <span className="tag" data-testid="phase4-persona">{persona(role)} · SYNTHETIC PROTOTYPE</span>
    </div>
    <div className="synthetic-note">Review decisions are user intent only. The server enforces capability, scope, version, audit, promotion, and protected-action boundaries.</div>
    <div className="phase4-review-layout">
      <section className="panel phase4-review-queue" aria-label="Phase4 review queue">
        <div className="panel-head"><div><span className="eyebrow">SERVER QUEUE</span><h3>Items requiring review</h3></div><button className="text-button" onClick={load} disabled={loading}><Icon name="refresh" size={14} /> Refresh</button></div>
        {loading && <div className="phase4-review-state" role="status">Loading Phase4 review queue…</div>}
        {!loading && error && <div className="phase4-review-state phase4-review-error" role="alert"><b>Unable to load review queue</b><p>{error}</p><button className="button-primary" onClick={load}>Retry</button></div>}
        {!loading && !error && items.length === 0 && <div className="phase4-review-state" data-testid="phase4-empty-state"><Icon name="empty" size={22} /><b>No Phase4 review items</b><p>New classification envelopes will appear here when the server routes them for human review.</p></div>}
        {!loading && !error && items.map((item) => <button key={item.id} className={`phase4-review-queue-item ${item.id === selectedId ? "selected" : ""}`} onClick={() => { setSelectedId(item.id); setMutationError(""); setConfirmation(""); }}><span><strong>{item.envelope_id}</strong><small>{label(item.status)} · {item.source_mode}</small></span><Icon name="arrow-right" size={15} /></button>)}
      </section>
      <section className="phase4-review-detail" aria-label="Phase4 review item">
        {selected && view && <>
          <div className="panel phase4-review-hero"><div><span className="eyebrow">REVIEW REASON</span><h3>{view.reason}</h3><p>Envelope <bdi>{selected.envelope_id}</bdi> · {label(selected.status)}</p></div><span className="status status-under-review">{label(selected.status)}</span></div>
          <div className="phase4-review-grid">
            <section className="panel" data-testid="phase4-evidence"><span className="eyebrow">BOUNDED EVIDENCE</span><h3>Safe evidence references</h3>{view.evidence.length ? <ul>{view.evidence.map((item, index) => <li key={index}>{renderValue(item)}</li>)}</ul> : <p>{text(undefined)}</p>}</section>
            <section className="panel" data-testid="phase4-classification"><span className="eyebrow">CLASSIFICATION PROPOSAL</span><h3>Server-proposed axes</h3><pre>{JSON.stringify(view.classification, null, 2)}</pre></section>
            <section className="panel" data-testid="phase4-contradictions"><span className="eyebrow">CONTRADICTIONS</span><h3>Conflicts and blockers</h3>{view.contradictions.length ? <ul>{view.contradictions.map((item, index) => <li key={index}>{renderValue(item)}</li>)}</ul> : <p>No contradiction supplied by the server.</p>}</section>
            <section className="panel" data-testid="phase4-links"><span className="eyebrow">CANDIDATE LINKS</span><h3>Candidate project / entity / record</h3>{view.links.length ? view.links.map((item, index) => { const link = item && typeof item === "object" ? item as Record<string, unknown> : {}; const href = text(link.href ?? link.deep_link, "#"); return <a className="phase4-review-link" href={href} key={index}>{text(link.label ?? link.id, renderValue(item))} <Icon name="arrow-up-right" size={13} /></a>; }) : <p>No candidate link supplied by the server.</p>}</section>
          </div>
          <section className="panel phase4-review-boundary"><div><span className="eyebrow">AUTHORITY BOUNDARY</span><h3>Review is not protected authority</h3><p data-testid="phase4-authority-warning">Classification review does not create a VerifiedAssertion, approve professional work, submit to a regulator, or execute a protected business action.</p></div><div><b>Protected action status</b><p data-testid="phase4-protected-boundary">Any protected human action remains separately required and server-authorized.</p></div></section>
          <section className="panel phase4-review-metadata"><div><b>Currentness / version</b><span data-testid="phase4-currentness">{view.currentness}</span></div><div><b>Source precedence</b><span data-testid="phase4-precedence">{view.precedence}</span></div><div><b>Unsupported capability</b><span data-testid="phase4-unsupported">{view.unsupported}</span></div><div><b>Scope</b><span>{view.scopeType} · {view.scopeId}</span></div></section>
          {(view.deferred || view.outOfScope) && <div className="phase4-review-state" data-testid="phase4-disposition"><b>{view.deferred ? "Deferred review" : "Out-of-scope review"}</b><p>The server supplied this disposition; no client-side business decision is inferred.</p></div>}
          {mutationError && <div className="phase4-review-error" role="alert">{mutationError}</div>}
          {confirmation && <div className="phase4-review-success" role="status">{confirmation}</div>}
          <div className="phase4-review-actions" aria-label="Phase4 review actions"><span className="eyebrow">SERVER-BACKED REVIEW ACTIONS</span>{PHASE4_DECISIONS.map((decision) => <button key={decision} className={decision === "ACCEPT" ? "button-primary" : "button-secondary"} disabled={Boolean(pending)} aria-busy={pending === decision} onClick={() => submit(decision)}>{pending === decision ? "Saving…" : label(decision)}</button>)}</div>
        </>}
        {!selected && !loading && !error && <div className="panel phase4-review-state">Select a Phase4 review item to inspect server-provided evidence and decisions.</div>}
      </section>
    </div>
  </div>;
}
