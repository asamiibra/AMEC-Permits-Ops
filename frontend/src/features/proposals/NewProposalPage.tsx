import { useEffect, useRef, useState } from "react";
import { ApiError, api } from "../../api";
import { Icon } from "../../Icon";
import { proposalHeaders } from "./api";
import { proposalSourceRegistry } from "./registry";
import type { JsonRecord, ProposalRole, ProposalSourceOption } from "./types";

const sourceIcon = (option: ProposalSourceOption) => option.icon === "mail"
  ? "mail" as const
  : option.icon === "document"
    ? "document" as const
    : option.icon === "image"
      ? "image" as const
      : option.icon === "users"
        ? "users" as const
        : "empty" as const;

const sourceAccept = (key: ProposalSourceOption["key"]) => key === "TENDER_PHOTO"
  ? "image/*"
  : key === "TENDER_EMAIL"
    ? ".eml,.msg,.pdf,.doc,.docx"
    : ".pdf,.doc,.docx,.txt";

function proposalError(cause: unknown): string {
  if (cause instanceof ApiError && cause.status === 401) return "Your session has expired. Sign in again before creating a Proposal.";
  if (cause instanceof ApiError && cause.status === 403) return "Your role cannot create a Proposal in this workspace.";
  return "Proposal could not be created. Review the fields and try again; no source was claimed.";
}

function RequiredMark() {
  return <span className="required-mark" aria-hidden="true">Required</span>;
}

export function NewProposalPage({ role, onBack, onCreated }: { role: ProposalRole; onBack: () => void; onCreated: (id: string) => void }) {
  const [source, setSource] = useState<ProposalSourceOption | null>(null);
  const [form, setForm] = useState({ title: "", client: "", projectReference: "", sourceTitle: "", sourceDate: "", notes: "", email: "", contact: "" });
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [clients, setClients] = useState<Array<{ id: string; name: string }>>([]);
  const fileRef = useRef<HTMLInputElement>(null);
  const update = (key: keyof typeof form, value: string) => setForm((current) => ({ ...current, [key]: value }));
  useEffect(() => { let active = true; api<JsonRecord>("/api/bd/proposals/clients", { headers: proposalHeaders(role) }).then((result) => { if (active && Array.isArray(result.items)) setClients(result.items.filter((item): item is { id: string; name: string } => typeof item === "object" && item !== null && typeof (item as JsonRecord).id === "string" && typeof (item as JsonRecord).name === "string")); }).catch(() => undefined); return () => { active = false; }; }, [role]);
  const selectedClientId = clients.find((item) => item.name.toLowerCase() === form.client.trim().toLowerCase())?.id;
  const chooseSource = (next: ProposalSourceOption) => { setSource(next); setFile(null); if (fileRef.current) fileRef.current.value = ""; setError(""); };
  const clearFile = () => { setFile(null); if (fileRef.current) fileRef.current.value = ""; };
  const create = async () => {
    if (!form.title.trim() || !form.client.trim()) { setError("Complete the required Proposal title and Client fields."); return; }
    if (!source) { setError("Choose how this Proposal began."); return; }
    if (source.acceptsFile && !file) { setError(`Choose the required ${source.label.toLowerCase()} file.`); return; }
    setBusy(true); setError("");
    try {
      const idempotency = `p04-${Date.now()}-${form.title.trim().slice(0, 32)}`;
      let result: JsonRecord;
      if (source.acceptsFile && file) {
        const body = new FormData();
        body.append("proposal_description", form.title.trim()); body.append("project_reference", form.projectReference); if (selectedClientId) body.append("client_account_id", selectedClientId); body.append("client_name", form.client.trim()); body.append("initial_source_type", source.key); body.append("source_title", form.sourceTitle || file.name); body.append("source_date", form.sourceDate); body.append("source_notes", form.notes); body.append("idempotency_key", idempotency); body.append("file", file);
        result = await api<JsonRecord>("/api/bd/proposals/intake", { method: "POST", headers: proposalHeaders(role), body });
      } else {
        result = await api<JsonRecord>("/api/bd/proposals", { method: "POST", headers: { ...proposalHeaders(role), "Content-Type": "application/json" }, body: JSON.stringify({ proposal_description: form.title.trim(), project_reference: form.projectReference || undefined, client_account_id: selectedClientId, client_name: form.client.trim(), idempotency_key: idempotency }) });
      }
      const nestedProposal = typeof result.proposal === "object" && result.proposal !== null ? result.proposal as JsonRecord : null;
      const id = typeof result.id === "string" ? result.id : typeof nestedProposal?.id === "string" ? nestedProposal.id : "";
      if (!id) throw new Error("invalid");
      onCreated(id);
    } catch (cause: unknown) { setError(proposalError(cause)); } finally { setBusy(false); }
  };
  return <div className="proposal-feature-page proposal-new-page">
    <header className="proposal-page-intro"><div><span className="eyebrow">PROPOSALS · INTAKE</span><h2>New Proposal</h2><p>Capture the commercial enquiry first. Source evidence stays separate from the Proposal draft and remains reviewable.</p></div><button type="button" className="button-secondary" onClick={onBack}><Icon name="arrow-left" size={14} /> Proposal register</button></header>
    {error && <div className="proposal-alert error-state" role="alert"><Icon name="alert" size={17} /> <span>{error}</span></div>}
    <section className="panel source-choice-panel" aria-labelledby="source-choice-title">
      <div className="panel-head"><div><span className="eyebrow">STEP 1 · SOURCE / CONTEXT</span><h3 id="source-choice-title">How did this Proposal begin?</h3></div><small>Select one starting context. You can add more evidence from the Proposal workspace.</small></div>
      <div className="source-option-grid" role="radiogroup" aria-label="Proposal source or starting context">
        {proposalSourceRegistry.map((option) => <button type="button" aria-pressed={source?.key === option.key} key={option.key} className={source?.key === option.key ? "source-option selected" : "source-option"} onClick={() => chooseSource(option)}>
          <span className="source-option-icon"><Icon name={sourceIcon(option)} size={19} /></span><span className="source-option-copy"><b>{option.label}</b><small>{option.description}</small></span><span className="source-option-state" aria-hidden="true"><Icon name={source?.key === option.key ? "check" : "current"} size={17} /></span>{source?.key === option.key && <span className="sr-only">Selected</span>}
        </button>)}
      </div>
    </section>
    {source && <section className="panel proposal-form-panel" aria-labelledby="proposal-details-title">
      <div className="panel-head"><div><span className="eyebrow">STEP 2 · PROPOSAL INFORMATION</span><h3 id="proposal-details-title">New Proposal from {source.label}</h3></div><span className="tag">Source selected</span></div>
      <div className="proposal-form-grid">
        <label>Proposal title <RequiredMark /><input aria-label="Proposal title" required value={form.title} onChange={(event) => update("title", event.target.value)} placeholder="Commercial enquiry or tender name" /></label>
        <label>Client <RequiredMark /><input aria-label="Client" required value={form.client} onChange={(event) => update("client", event.target.value)} placeholder="Existing client or candidate name" /></label>
        <label>Project reference <span className="field-hint">Optional until a Project exists</span><input aria-label="Project reference" value={form.projectReference} onChange={(event) => update("projectReference", event.target.value)} placeholder="Project or client reference" /></label>
        {source.key === "CLIENT_DATA" && <><label>Proposal contact<input aria-label="Proposal contact" value={form.contact} onChange={(event) => update("contact", event.target.value)} placeholder="Contact name" /></label><label>Contact email<input aria-label="Contact email" value={form.email} onChange={(event) => update("email", event.target.value)} placeholder="name@client.example" type="email" /></label></>}
      </div>
      {source.key !== "NONE" && <section className="proposal-source-details" aria-labelledby="source-details-title"><div><span className="eyebrow">STEP 3 · SOURCE EVIDENCE</span><h4 id="source-details-title">Evidence details</h4><p>These notes describe the source; they do not assert that external facts have been verified.</p></div><div className="proposal-form-grid"><label>Source title<input aria-label="Source title" value={form.sourceTitle} onChange={(event) => update("sourceTitle", event.target.value)} placeholder={source.acceptsFile ? "Title or filename" : "Client information source"} /></label><label>Source date<input aria-label="Source date" value={form.sourceDate} onChange={(event) => update("sourceDate", event.target.value)} type="date" /></label><label className="proposal-form-wide">Notes<textarea aria-label="Source notes" value={form.notes} onChange={(event) => update("notes", event.target.value)} placeholder="Human-entered context; not verified external fact" /></label></div></section>}
      {source.acceptsFile && <div className="proposal-file-drop proposal-form-wide"><div><span className="eyebrow">INITIAL EVIDENCE FILE</span><b>{source.label} <RequiredMark /></b><small>{source.key === "TENDER_PHOTO" ? "Image files accepted." : "Choose the source document to register with this Proposal."}</small></div><input ref={fileRef} id="proposal-source-file" className="visually-hidden" aria-label={`${source.label} file`} type="file" accept={sourceAccept(source.key)} onChange={(event) => setFile(event.target.files?.[0] || null)} /><button type="button" className="button-secondary proposal-file-picker" onClick={() => fileRef.current?.click()}>{file ? "Replace file" : "Choose file"}</button>{file ? <div className="proposal-file-selected" role="status"><Icon name="check" size={15} /><span><b>{file.name}</b><small>{(file.size / 1024).toFixed(0)} KB · ready to register as evidence</small></span><button type="button" className="text-button" onClick={clearFile}>Remove</button></div> : <p className="proposal-file-empty">No file selected yet.</p>}</div>}
      <div className="proposal-form-footer"><p><Icon name="shield" size={14} /> Document, DocumentVersion, hash, and provenance remain in the governed source system. Upload does not imply OCR or AI certainty.</p><button type="button" className="button-primary" onClick={() => void create()} disabled={busy}>{busy ? "Creating Proposal…" : "Create Proposal draft"}</button></div>
    </section>}
    {!source && <div className="proposal-empty panel"><b>Choose a starting point to continue.</b><span>The Proposal draft is not created until you choose a source context.</span></div>}
  </div>;
}
