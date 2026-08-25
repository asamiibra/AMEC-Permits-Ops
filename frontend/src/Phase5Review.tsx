import { useEffect, useMemo, useState } from "react";
import { api } from "./api";

type QueueItem = {
  id: string;
  envelope_id: string;
  root_event_id: string;
  classifier_version: string;
  rules_version: string;
  source_mode: string;
  axes_json?: Record<string, unknown>;
  record_version: number;
  status: string;
};

type ClassificationResponse = {
  classification_envelope: { id: string; envelope_id: string; status: string; record_version: number };
  classification: Record<string, unknown>;
};

const decisions = ["ACCEPT", "CORRECT", "DEFER", "MARK_OUT_OF_SCOPE", "RESOLVE_RELATIONSHIP"] as const;

function label(value: string) {
  return value.replaceAll("_", " ").toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function syntheticRequest(kind: "new" | "ambiguous" | "secret") {
  return {
    fixture_id: `P5-UI-${kind.toUpperCase()}-001`,
    source_artifact_id: `synthetic-artifact://phase5/ui/${kind}`,
    source_version_token: "v1",
    source_mode: kind === "new" ? "NEW_UNKNOWN_SOURCE" : "EXISTING_KNOWN_SOURCE",
    scope_type: "PROJECT",
    scope_id: "synthetic-project-001",
    correlation_id: `phase5-ui-${kind}-correlation`,
    evidence_ids: [`synthetic-evidence://phase5/ui/${kind}/01`],
    contradiction_families: kind === "ambiguous" ? ["DISCIPLINE_CONFLICT"] : [],
    secret_exclude: kind === "secret",
  };
}

export function Phase5ReviewPage({ role }: { role: string }) {
  const [items, setItems] = useState<QueueItem[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const scope = useMemo(() => new URLSearchParams({ scope_type: "PROJECT", scope_id: "synthetic-project-001" }), []);

  const load = () => {
    setLoading(true);
    api<{ items: QueueItem[] }>(`/api/phase5/review-queue?${scope.toString()}`)
      .then((response) => {
        setItems(response.items || []);
        setSelectedId((current) => current && response.items.some((item) => item.id === current) ? current : response.items[0]?.id || "");
        setError("");
      })
      .catch((cause) => setError(cause instanceof Error ? cause.message : "Phase5 review queue could not be loaded."))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);
  const selected = items.find((item) => item.id === selectedId) || null;
  const axes = selected?.axes_json || {};
  const proposal = axes.classification_proposal && typeof axes.classification_proposal === "object" ? axes.classification_proposal as Record<string, unknown> : {};
  const evidence = Array.isArray(axes.bounded_evidence) ? axes.bounded_evidence : [];
  const rules = Array.isArray(axes.rule_evaluations) ? axes.rule_evaluations : [];

  const create = (kind: "new" | "ambiguous" | "secret") => {
    setPending(`create-${kind}`);
    setMessage("");
    api<ClassificationResponse>("/api/phase5/classify", { method: "POST", body: JSON.stringify(syntheticRequest(kind)) })
      .then((response) => { setMessage(`${label(kind)} synthetic classification ${response.classification_envelope.envelope_id} is ready for review.`); load(); })
      .catch((cause) => setError(cause instanceof Error ? cause.message : "Classification could not be created."))
      .finally(() => setPending(""));
  };

  const decide = (decision: typeof decisions[number]) => {
    if (!selected) return;
    setPending(decision);
    setMessage("");
    const relationship = axes.relationship_resolution && typeof axes.relationship_resolution === "object" ? axes.relationship_resolution : null;
    const corrections_json = decision === "CORRECT" ? [{
      axis: "document_type",
      old_value: proposal.document_type,
      new_value: "CORRECTED_SYNTHETIC_DOCUMENT",
      reason: "Synthetic reviewer correction for the bounded classifier proposal.",
      evidence_ids: evidence.map((item) => typeof item === "object" && item !== null && "evidence_id" in item ? String(item.evidence_id) : ""),
    }] : decision === "RESOLVE_RELATIONSHIP" && relationship && typeof relationship === "object" ? [relationship] : [];
    const body = {
      decision_id: `phase5-ui-decision-${Date.now()}`,
      classification_envelope_id: selected.id,
      decision,
      actor_id: "ui-non-authoritative-input",
      capability: decision === "RESOLVE_RELATIONSHIP" ? "PHASE4_RESOLVE_RELATIONSHIP" : "PHASE4_REVIEW_DECISION",
      scope_type: "PROJECT",
      scope_id: "synthetic-project-001",
      record_version: selected.record_version,
      idempotency_key: `phase5-ui-key-${Date.now()}`,
      corrections_json,
    };
    api<{ decision: string }>("/api/phase5/review-decisions", { method: "POST", body: JSON.stringify(body) })
      .then((response) => { setMessage(`${label(response.decision)} recorded by the server. Original classifier output remains immutable.`); load(); })
      .catch((cause) => setError(cause instanceof Error ? cause.message : "Review decision could not be recorded."))
      .finally(() => setPending(""));
  };

  return <div className="phase5-review-page">
    <div className="page-intro"><div><span className="eyebrow">PHASE5 · CLASSIFIER V2 SHADOW</span><h2>Review classifier evidence</h2><p>Deterministic proposals are compare-only until a permitted human review decision is recorded.</p></div><span className="tag">{role} · SYNTHETIC ONLY</span></div>
    <div className="synthetic-note">REAL_CONTENT_MODE: DISABLED · LLM_EXTERNAL_CALL_COUNT: 0 · REVIEW_COMPARE_ONLY · no classifier-only promotion or projection</div>
    <section className="panel phase5-fixture-panel" aria-label="Synthetic classifier fixtures"><div><span className="eyebrow">CONTROLLED FIXTURES</span><h3>Generate a bounded proposal</h3><p>Only sanitized evidence references are sent. No source content is read.</p></div><div className="phase5-fixture-actions"><button className="button-primary" onClick={() => create("new")} disabled={Boolean(pending)}>New source</button><button className="button-secondary" onClick={() => create("ambiguous")} disabled={Boolean(pending)}>Ambiguous review</button><button className="button-secondary" onClick={() => create("secret")} disabled={Boolean(pending)}>Secret exclude</button><button className="text-button" onClick={load} disabled={loading}>Refresh</button></div></section>
    {error && <div className="phase4-review-error" role="alert">{error}</div>}
    {message && <div className="phase4-review-success" role="status">{message}</div>}
    <div className="phase5-review-layout"><section className="panel phase5-queue" aria-label="Phase5 review queue"><div className="panel-head"><div><span className="eyebrow">SERVER QUEUE</span><h3>Pending proposals</h3></div><span className="tag">{items.length} item{items.length === 1 ? "" : "s"}</span></div>{loading && <div role="status">Loading review queue…</div>}{!loading && items.length === 0 && <div className="phase4-review-state" data-testid="phase5-empty-state"><b>No classifier proposals</b><p>Generate a controlled synthetic fixture to begin.</p></div>}{items.map((item) => <button key={item.id} className={`phase5-queue-item ${item.id === selectedId ? "selected" : ""}`} onClick={() => setSelectedId(item.id)}><strong>{item.envelope_id}</strong><small>{label(item.status)} · {label(item.source_mode)}</small></button>)}</section>
      <section className="phase5-detail" aria-label="Phase5 review detail">{selected ? <><div className="panel phase5-hero"><div><span className="eyebrow">REVIEW REQUIRED</span><h3>{String(axes.review_reason || "Human review is required before authority or projection.")}</h3><p>{selected.envelope_id} · root event {selected.root_event_id}</p></div><span className="status status-under-review">{label(selected.status)}</span></div><div className="phase5-metadata"><span><b>Classifier</b>{selected.classifier_version}</span><span><b>Source mode</b>{label(String(axes.source_mode || selected.source_mode))}</span><span><b>Hard gate</b>{String((axes.hard_gate as Record<string, unknown> | undefined)?.state || "NONE")}</span><span><b>Correlation</b>{String(axes.correlation_id || "not supplied")}</span></div><div className="phase5-grid"><section className="panel"><span className="eyebrow">PROPOSAL AXES</span><h3>Candidate classification</h3><pre>{JSON.stringify(proposal, null, 2)}</pre></section><section className="panel"><span className="eyebrow">BOUNDED EVIDENCE</span><h3>Reference IDs only</h3><ul>{evidence.map((item, index) => <li key={index}>{JSON.stringify(item)}</li>)}</ul></section><section className="panel"><span className="eyebrow">RULE EVALUATIONS</span><h3>Deterministic reasons</h3><ul>{rules.map((item, index) => <li key={index}>{JSON.stringify(item)}</li>)}</ul></section></div><section className="panel phase5-boundary"><b>Authority boundary</b><p data-testid="phase5-authority-boundary">This proposal does not create a VerifiedAssertion, approve professional work, submit externally, or execute a protected action.</p></section><div className="phase5-actions" aria-label="Phase5 review actions"><span className="eyebrow">SERVER-BACKED ACTIONS</span>{decisions.map((decision) => <button key={decision} className={decision === "ACCEPT" ? "button-primary" : "button-secondary"} disabled={Boolean(pending)} onClick={() => decide(decision)}>{pending === decision ? "Saving…" : label(decision)}</button>)}</div></> : <div className="panel phase4-review-state">Select a proposal to inspect its server-provided evidence.</div>}</section></div>
  </div>;
}
