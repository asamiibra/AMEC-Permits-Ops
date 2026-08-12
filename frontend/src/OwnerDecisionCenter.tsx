import { useEffect, useMemo, useState } from "react";
import { api } from "./api";

const readable = (value: unknown) => String(value ?? "").replaceAll("_", " ").toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase());
const display = (value: unknown) => typeof value === "string" ? value : JSON.stringify(value, null, 2);

type Decision = {
  key: string; group: string; title: string; question: string; why: string; status: string; blocking_level: string; decision_type: string;
  proposed_default: unknown; effective_value: unknown; options: unknown[]; affected_modules: string[]; current_system_state: Record<string, unknown>;
  effective_behavior_preview: unknown; runtime: { apply_state: string; value: unknown; mismatch: boolean };
  history: Array<{ event: string; actor: string; at: string; note?: string }>;
};

export function OwnerDecisionCenterPage() {
  const [data, setData] = useState<any>(null);
  const [selectedKey, setSelectedKey] = useState("");
  const [selectedValue, setSelectedValue] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const load = () => {
    setError("");
    api<any>("/api/owner-decisions").then((result) => {
      setData(result);
      if (!selectedKey && result.items?.[0]) setSelectedKey(result.items[0].key);
    }).catch((cause) => setError(cause instanceof Error ? cause.message : "Owner Decision Center is unavailable."));
  };
  useEffect(() => { load(); }, []);
  const selected: Decision | undefined = useMemo(() => data?.items?.find((item: Decision) => item.key === selectedKey), [data, selectedKey]);
  const choose = (key: string) => { setSelectedKey(key); setSelectedValue(""); setNotes(""); setMessage(""); };
  const act = async (action: string, value?: unknown) => {
    if (!selected) return;
    setBusy(true); setError(""); setMessage("");
    try {
      await api(`/api/owner-decisions/${selected.key}/actions`, { method: "POST", body: JSON.stringify({ action, value, notes: notes || undefined }) });
      setMessage(`${selected.title}: ${readable(action)} recorded and audited.`);
      setSelectedValue(""); setNotes(""); load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Decision change was not applied."); }
    finally { setBusy(false); }
  };
  if (error && !data) return <section className="admin-owner-panel admin-owner-error" role="alert"><h2>Owner Decision Center unavailable</h2><p>{error}</p><button className="button-primary" onClick={load}>Retry</button></section>;
  if (!data) return <section className="admin-owner-panel"><b>Loading Owner Decision Center…</b></section>;
  return <section className="owner-decision-center">
    <div className="admin-owner-panel owner-decision-hero"><div><span className="eyebrow">MASTER CONTENT SETUP &amp; GO-LIVE</span><h3>One Owner Decision Register</h3><p>Every business decision is explicit, auditable, and separate from system facts, content readiness, and software evidence. Proposed defaults are not Owner confirmations.</p><small>{data.count} canonical decisions · {data.duplicate_key_count} duplicate keys</small></div><div className="owner-decision-overall"><span>Go-live status</span><strong>{readable(data.go_live?.overall)}</strong><small>{data.go_live?.blockers?.length || 0} blocker(s)</small></div></div>
    <div className="owner-decision-metrics">{[["P0 blockers", data.summary.p0], ["P1 required", data.summary.p1], ["P2 defaults", data.summary.p2], ["P3 optional", data.summary.p3], ["External technical", data.summary.external_technical], ["Confirmed", data.summary.confirmed]].map(([label, value]) => <div className="metric" key={String(label)}><span>{label}</span><strong>{String(value)}</strong><small>canonical register</small></div>)}</div>
    {error && <div className="admin-owner-message" role="alert">{error}</div>}{message && <div className="admin-owner-message" role="status">{message}</div>}
    <div className="owner-decision-layout"><div className="owner-decision-groups">{data.groups.map((group: any) => <section className="admin-owner-panel owner-decision-group" key={group.key}><div className="admin-owner-panel-heading"><div><span className="eyebrow">{group.label}</span><h3>{group.items.length} decision(s)</h3></div></div>{group.items.map((item: Decision) => <button className={`owner-decision-row ${item.key === selectedKey ? "selected" : ""}`} key={item.key} onClick={() => choose(item.key)}><span><b>{item.title}</b><small>{item.key}</small></span><em>{readable(item.status)}</em><strong>{readable(item.blocking_level)}</strong></button>)}</section>)}</div><DecisionDetail item={selected} busy={busy} selectedValue={selectedValue} setSelectedValue={setSelectedValue} notes={notes} setNotes={setNotes} onAction={act} /></div>
    <ReadinessPanel data={data} />
  </section>;
}

function DecisionDetail({ item, busy, selectedValue, setSelectedValue, notes, setNotes, onAction }: { item?: Decision; busy: boolean; selectedValue: string; setSelectedValue: (value: string) => void; notes: string; setNotes: (value: string) => void; onAction: (action: string, value?: unknown) => void }) {
  if (!item) return <section className="admin-owner-panel"><h3>Select a decision</h3></section>;
  return <section className="admin-owner-panel owner-decision-detail"><div className="admin-owner-panel-heading"><div><span className="eyebrow">DECISION DETAIL · {readable(item.decision_type)}</span><h3>{item.title}</h3><small>{item.key}</small></div><span className={`tag ${item.status === "EXTERNAL_TECHNICAL_BLOCK" ? "warning" : ""}`}>{readable(item.status)}</span></div><div className="owner-decision-detail-grid"><div><b>Blocking level</b><span>{readable(item.blocking_level)}</span></div><div><b>Affected modules</b><span>{item.affected_modules.join(" · ")}</span></div><div><b>Question</b><span>{item.question}</span></div><div><b>Why it matters</b><span>{item.why}</span></div><div><b>Current system state</b><pre>{display(item.current_system_state)}</pre></div><div><b>Recommended safe default</b><pre>{display(item.proposed_default)}</pre></div><div><b>Effective behavior preview</b><pre>{display(item.effective_behavior_preview)}</pre></div><div><b>Runtime read-back</b><span>{readable(item.runtime.apply_state)}{item.runtime.mismatch ? " · mismatch" : ""}</span></div></div>{item.options.length > 1 && <label className="owner-decision-select">Owner selection<select value={selectedValue} onChange={(event) => setSelectedValue(event.target.value)}><option value="">Choose an option…</option>{item.options.map((option, index) => <option key={index} value={typeof option === "string" ? option : JSON.stringify(option)}>{display(option)}</option>)}</select></label>}<label className="owner-decision-notes">Owner notes<textarea value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Explain the decision or prospective impact…" /></label><div className="action-row owner-decision-actions"><button className="button-primary" disabled={busy || item.key === "REAL_SYNOLOGY_CONNECTION"} onClick={() => onAction("confirm_default")}>Confirm recommended default</button><button className="button-secondary" disabled={busy || item.key === "REAL_SYNOLOGY_CONNECTION"} onClick={() => onAction("approve_safe_default")}>Approve safe default for go-live</button>{item.options.length > 1 && <button className="button-secondary" disabled={busy || item.key === "REAL_SYNOLOGY_CONNECTION" || !selectedValue} onClick={() => onAction("choose", selectedValue)}>Choose option</button>}<button className="text-button" disabled={busy} onClick={() => onAction("reopen")}>Reopen</button>{item.key === "REAL_SYNOLOGY_CONNECTION" && <span className="owner-decision-fact-warning">Technical fact: only adapter verification can set this state.</span>}</div><h4>Decision history</h4>{item.history.length ? item.history.map((event) => <div className="owner-decision-history" key={`${event.at}-${event.event}`}><b>{readable(event.event)}</b><span>{event.actor} · {new Date(event.at).toLocaleString()}</span><small>{event.note || "No note"}</small></div>) : <p className="muted">No Owner decision has been recorded.</p>}</section>;
}

function ReadinessPanel({ data }: { data: any }) { return <section className="admin-owner-panel owner-readiness-panel"><div className="admin-owner-panel-heading"><div><span className="eyebrow">READINESS IS COMPUTED</span><h3>Inputs, content, software, and technical gates</h3></div><span className="tag">{readable(data.go_live.overall)}</span></div><div className="owner-readiness-columns"><div><h4>Content readiness</h4>{data.content_readiness.map((item: any) => <div className="owner-readiness-row" key={item.key}><span>{item.label}</span><b>{readable(item.status)}</b></div>)}</div><div><h4>Software readiness</h4>{data.software_readiness.map((item: any) => <div className="owner-readiness-row" key={item.label}><span>{item.label}</span><b>{readable(item.status)}</b></div>)}</div><div><h4>Contradictions</h4><div className="owner-readiness-row"><span>Deterministic checks</span><b>{readable(data.contradictions.status)}</b></div><div className="owner-readiness-row"><span>Unresolved</span><b>{data.contradictions.unresolved.length}</b></div></div></div><p className="admin-owner-note">Real Synology remains a technical fact, not a manually confirmable Owner decision. Test/non-production operation is not full production readiness.</p></section>; }
