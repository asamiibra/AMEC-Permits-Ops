import { useEffect, useMemo, useRef, useState } from "react";
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
type ReviewScope = { scopeType: string; scopeId: string };

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
  if (role === "SYSTEM_ADMIN" || role === "OWNER_SPONSOR") return "Owner";
  if (role === "PROCESS_CHAMPION" || role === "COMMERCIAL_APPROVER") return "Business Development";
  if (role === "RESPONSIBLE_ENGINEER" || role === "REQUIREMENT_STEWARD") return "Engineering";
  return null;
}

function reviewScope(): ReviewScope | null {
  const params = new URLSearchParams(window.location.search);
  const scopeType = params.get("scope_type")?.trim() || "";
  const scopeId = params.get("scope_id")?.trim() || "";
  return scopeType && scopeId ? { scopeType, scopeId } : null;
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
  const relationship = axes.relationship_resolution && typeof axes.relationship_resolution === "object" ? axes.relationship_resolution as Record<string, unknown> : null;
  const classificationObject = classification && typeof classification === "object" ? classification as Record<string, unknown> : {};
  return {
    axes,
    scope,
    reason: text(axes.review_reason ?? axes.reason, "Classification requires human review before any authority or projection step."),
    evidence,
    classification,
    contradictions,
    links,
    currentness: text(axes.currentness ?? axes.version_state, `Record version ${item.record_version}; server precondition applies.`),
    precedence: text(axes.source_precedence, "Source precedence was not supplied by the server."),
    relationship,
    deferred: item.status === "DEFERRED" || Boolean(axes.deferred),
    outOfScope: item.status === "OUT_OF_SCOPE" || Boolean(axes.out_of_scope),
    unsupported: text(axes.unsupported_capability_state ?? axes.unsupported_capability, "No unsupported capability was supplied."),
    scopeType: typeof (scope.scope_type ?? axes.scope_type) === "string" ? String(scope.scope_type ?? axes.scope_type) : "",
    scopeId: typeof (scope.scope_id ?? axes.scope_id) === "string" ? String(scope.scope_id ?? axes.scope_id) : "",
    classificationObject,
  };
}

function validRelationship(value: Record<string, unknown> | null) {
  return Boolean(value && ["source_entity_id", "candidate_entity_id", "relationship_type", "resolution"].every((key) => typeof value[key] === "string" && String(value[key]).trim()));
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
  const [correctionAxis, setCorrectionAxis] = useState("");
  const [correctionValue, setCorrectionValue] = useState("");
  const [correctionReason, setCorrectionReason] = useState("");
  const attemptRef = useRef<{ decision: Decision; decisionId: string; idempotencyKey: string; fingerprint: string } | null>(null);
  const visiblePersona = persona(role);
  const scopeContext = useMemo(() => reviewScope(), []);

  const load = () => {
    if (!visiblePersona || !scopeContext) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError("");
    const query = new URLSearchParams({ scope_type: scopeContext.scopeType, scope_id: scopeContext.scopeId });
    api<{ items: ReviewItem[] }>(`/api/phase4/review-queue?${query.toString()}`)
      .then((response) => {
        setItems(response.items || []);
        setSelectedId((current) => current && response.items.some((item) => item.id === current) ? current : response.items[0]?.id || "");
        attemptRef.current = null;
      })
      .catch((cause) => setError(cause instanceof Error ? cause.message : "Phase4 review queue could not be loaded."))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [role, scopeContext?.scopeType, scopeContext?.scopeId]);

  const selected = useMemo(() => items.find((item) => item.id === selectedId) || null, [items, selectedId]);
  const view = selected ? extract(selected) : null;

  const submit = (decision: Decision) => {
    if (!selected || !view || pending || !visiblePersona || !scopeContext) return;
    if (decision === "RESOLVE_RELATIONSHIP" && !validRelationship(view.relationship)) {
      setMutationError("Relationship resolution is unavailable because the server supplied no valid relationship candidate.");
      return;
    }
    if (decision === "CORRECT" && (!correctionAxis || !correctionReason.trim() || !correctionValue.trim())) {
      setMutationError("CORRECT requires a server-provided axis, a changed value, and a reason.");
      return;
    }
    const corrections = decision === "RESOLVE_RELATIONSHIP" && view.relationship
      ? [view.relationship]
      : decision === "CORRECT"
        ? [{ axis: correctionAxis, old_value: view.classificationObject[correctionAxis], new_value: correctionValue, reason: correctionReason.trim(), evidence_ids: [] }]
        : [];
    const fingerprint = JSON.stringify({ decision, envelope: selected.id, record_version: selected.record_version, scope: scopeContext, corrections });
    if (!attemptRef.current || attemptRef.current.decision !== decision || attemptRef.current.fingerprint !== fingerprint) {
      attemptRef.current = { decision, fingerprint, decisionId: idempotencyKey(), idempotencyKey: idempotencyKey() };
    }
    const attempt = attemptRef.current;
    setPending(decision);
    setMutationError("");
    setConfirmation("");
    const payload = {
      decision_id: attempt.decisionId,
      classification_envelope_id: selected.id,
      decision,
      actor_id: "ui-non-authoritative-input",
      capability: decision === "RESOLVE_RELATIONSHIP" ? "PHASE4_RESOLVE_RELATIONSHIP" : "PHASE4_REVIEW_DECISION",
      scope_type: scopeContext.scopeType,
      scope_id: scopeContext.scopeId,
      record_version: selected.record_version,
      idempotency_key: attempt.idempotencyKey,
      corrections_json: corrections,
    };
    api<{ decision: Decision }>("/api/phase4/review-decisions", { method: "POST", body: JSON.stringify(payload) })
      .then((response) => {
        setConfirmation(`${label(response.decision)} recorded by the server. Refreshing the review queue.`);
        load();
      })
      .catch((cause) => {
        const message = cause instanceof Error ? cause.message : "The review decision could not be recorded.";
        if (message.includes("409")) attemptRef.current = null;
        setMutationError(message.includes("409") ? "STALE REVIEW — refresh required before submitting another decision." : message.includes("401") || message.includes("403") ? "Authorization denied — the server did not accept this review action." : message);
      })
      .finally(() => setPending(""));
  };

  if (!visiblePersona) return <div className="phase4-review-page"><div className="panel phase4-review-state" role="alert" data-testid="phase4-unsupported-role"><b>Review unavailable</b><p>This role is unsupported for Phase4 review and no review request was sent.</p></div></div>;
  if (!scopeContext) return <div className="phase4-review-page"><div className="panel phase4-review-state" role="alert" data-testid="phase4-scope-required"><b>Review scope required</b><p>The server-bound project or entity scope is missing. Open review from a scoped application route; no queue or decision request was sent.</p></div></div>;

  return <div className="phase4-review-page">
    <div className="page-intro">
      <div>
        <span className="eyebrow">PHASE4 · AMEC EVIDENCE REVIEW</span>
        <h2>Review classification evidence</h2>
        <p>Review bounded server-provided evidence before any VerifiedAssertion or typed projection authority path.</p>
      </div>
        <span className="tag" data-testid="phase4-persona">{visiblePersona} · SYNTHETIC PROTOTYPE</span>
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
          <section className="panel phase4-correction-editor" data-testid="phase4-correction-editor"><span className="eyebrow">CORRECTION EDITOR</span><h3>Correct a server-provided axis</h3><div className="phase4-correction-fields"><label>Axis<select value={correctionAxis} onChange={(event) => setCorrectionAxis(event.target.value)}><option value="">Select an axis</option>{Object.keys(view.classificationObject).map((axis) => <option key={axis} value={axis}>{axis}</option>)}</select></label><label>New value<input value={correctionValue} onChange={(event) => setCorrectionValue(event.target.value)} placeholder="Changed value" /></label><label>Reason<input value={correctionReason} onChange={(event) => setCorrectionReason(event.target.value)} placeholder="Why is this correction required?" /></label></div></section>
          {(view.deferred || view.outOfScope) && <div className="phase4-review-state" data-testid="phase4-disposition"><b>{view.deferred ? "Deferred review" : "Out-of-scope review"}</b><p>The server supplied this disposition; no client-side business decision is inferred.</p></div>}
          {mutationError && <div className="phase4-review-error" role="alert">{mutationError}</div>}
          {confirmation && <div className="phase4-review-success" role="status">{confirmation}</div>}
          <div className="phase4-review-actions" aria-label="Phase4 review actions"><span className="eyebrow">SERVER-BACKED REVIEW ACTIONS</span>{PHASE4_DECISIONS.map((decision) => <button key={decision} className={decision === "ACCEPT" ? "button-primary" : "button-secondary"} disabled={Boolean(pending) || (decision === "RESOLVE_RELATIONSHIP" && !validRelationship(view.relationship))} aria-busy={pending === decision} onClick={() => submit(decision)}>{pending === decision ? "Saving…" : label(decision)}</button>)}</div>
        </>}
        {!selected && !loading && !error && <div className="panel phase4-review-state">Select a Phase4 review item to inspect server-provided evidence and decisions.</div>}
      </section>
    </div>
  </div>;
}
