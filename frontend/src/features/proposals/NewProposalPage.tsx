import { useEffect, useRef, useState } from "react";
import { ApiError, api } from "../../api";
import { BidiText } from "../../BidiText";
import { Icon } from "../../Icon";
import { proposalHeaders } from "./api";
import { proposalSourceRegistry } from "./registry";
import type { JsonRecord, ProposalRole, ProposalSourceOption } from "./types";

type Client = { id: string; name: string; reference?: string; status?: string };
type ClientLoadState =
  | { status: "LOADING"; items: Client[] }
  | { status: "READY"; items: Client[] }
  | { status: "EMPTY"; items: [] }
  | { status: "ERROR"; items: Client[] };

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
  if (cause instanceof ApiError && cause.message.includes("CANONICAL_CLIENT_ACCOUNT_REQUIRED")) return "Choose an active canonical Client from the list before creating the Proposal.";
  if (cause instanceof Error && cause.message && !cause.message.includes("[object Object]")) return cause.message;
  return "Proposal could not be created. Review the fields and try again.";
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
  const [selectedClientId, setSelectedClientId] = useState<string | null>(null);
  const [clientState, setClientState] = useState<ClientLoadState>({ status: "LOADING", items: [] });
  const [clientRetry, setClientRetry] = useState(0);
  const fileRef = useRef<HTMLInputElement>(null);
  const update = (key: keyof typeof form, value: string) => setForm((current) => ({ ...current, [key]: value }));

  useEffect(() => {
    const controller = new AbortController();
    setClientState((current) => ({ status: "LOADING", items: current.items }));
    api<JsonRecord>("/api/bd/proposals/clients", { headers: proposalHeaders(role), signal: controller.signal })
      .then((result) => {
        const items = Array.isArray(result.items)
          ? result.items.filter((item): item is Client => typeof item === "object" && item !== null && typeof (item as JsonRecord).id === "string" && typeof (item as JsonRecord).name === "string")
          : [];
        setClientState(items.length ? { status: "READY", items } : { status: "EMPTY", items: [] });
        setSelectedClientId((current) => current && items.some((item) => item.id === current) ? current : null);
      })
      .catch((cause: unknown) => {
        if (cause instanceof DOMException && cause.name === "AbortError") return;
        setClientState((current) => ({ status: "ERROR", items: current.items }));
        setSelectedClientId(null);
      });
    return () => controller.abort();
  }, [role, clientRetry]);

  const chooseClient = (id: string) => {
    const match = clientState.items.find((item) => item.id === id);
    setForm((current) => ({ ...current, client: match?.name || "" }));
    setSelectedClientId(match?.id || null);
  };
  const chooseSource = (next: ProposalSourceOption) => { setSource(next); setFile(null); if (fileRef.current) fileRef.current.value = ""; setError(""); };
  const clearFile = () => { setFile(null); if (fileRef.current) fileRef.current.value = ""; };

  const create = async () => {
    if (clientState.status === "LOADING") { setError("Active Clients are still loading. Wait for the list before creating the Proposal."); return; }
    if (clientState.status === "ERROR") { setError("Client list could not be loaded. Retry before creating the Proposal."); return; }
    if (clientState.status === "EMPTY") { setError("No active Clients are available for Proposal creation."); return; }
    if (!form.title.trim() || !form.client.trim()) { setError("Complete the required Proposal title and Client fields."); return; }
    if (!selectedClientId) { setError("Choose an active canonical Client from the list before creating the Proposal."); return; }
    if (!source) { setError("Choose how this Proposal began."); return; }
    if (source.key === "CLIENT_DATA" && !form.contact.trim() && !form.email.trim()) { setError("Add a Proposal contact name or email for Client Information."); return; }
    if (source.acceptsFile && !file) { setError(`Choose the required ${source.label.toLowerCase()} file.`); return; }
    setBusy(true); setError("");
    try {
      const idempotency = `p04-${Date.now()}-${form.title.trim().slice(0, 32)}`;
      let result: JsonRecord;
      if (source.acceptsFile && file) {
        const body = new FormData();
        body.append("proposal_description", form.title.trim()); body.append("project_reference", form.projectReference); body.append("client_account_id", selectedClientId); body.append("client_name", form.client.trim()); body.append("initial_source_type", source.key); body.append("source_title", form.sourceTitle || file.name); body.append("source_date", form.sourceDate); body.append("source_notes", form.notes); body.append("idempotency_key", idempotency); body.append("file", file);
        result = await api<JsonRecord>("/api/bd/proposals/intake", { method: "POST", headers: proposalHeaders(role), body });
      } else if (source.key === "CLIENT_DATA") {
        const body = new FormData();
        body.append("proposal_description", form.title.trim()); body.append("project_reference", form.projectReference); body.append("client_account_id", selectedClientId); body.append("client_name", form.client.trim()); body.append("initial_source_type", source.key); body.append("source_title", form.sourceTitle || "Client Information"); body.append("source_date", form.sourceDate); body.append("source_notes", form.notes); body.append("contact_name", form.contact); body.append("contact_email", form.email); body.append("idempotency_key", idempotency);
        result = await api<JsonRecord>("/api/bd/proposals/intake", { method: "POST", headers: proposalHeaders(role), body });
      } else {
        result = await api<JsonRecord>("/api/bd/proposals", { method: "POST", headers: { ...proposalHeaders(role), "Content-Type": "application/json" }, body: JSON.stringify({ proposal_description: form.title.trim(), project_reference: form.projectReference || undefined, client_account_id: selectedClientId, client_name: form.client.trim(), idempotency_key: idempotency }) });
      }
      const nestedProposal = typeof result.proposal === "object" && result.proposal !== null ? result.proposal as JsonRecord : null;
      const id = typeof result.id === "string" ? result.id : typeof nestedProposal?.id === "string" ? nestedProposal.id : "";
      if (!id) throw new Error("Proposal creation returned no canonical Proposal ID.");
      onCreated(id);
    } catch (cause: unknown) { setError(proposalError(cause)); } finally { setBusy(false); }
  };

  const clientStatus = clientState.status === "LOADING"
    ? <p className="field-hint" role="status">Loading active Clients…</p>
    : clientState.status === "ERROR"
      ? <p className="field-hint error-text" role="alert">Client list could not be loaded. <button type="button" className="text-button" aria-label="Retry client list" onClick={() => setClientRetry((value) => value + 1)}>Retry</button></p>
      : clientState.status === "EMPTY"
        ? <p className="field-hint" role="status">No active Clients are available for Proposal creation.</p>
        : <p className="field-hint">Select an active canonical Client; the canonical ID is stored separately from the display name.</p>;

  return <div className="proposal-feature-page proposal-new-page">
    <header className="proposal-page-intro"><div><span className="eyebrow">PROPOSALS · INTAKE</span><h2>New Proposal</h2><p>Capture the commercial enquiry first. Source evidence stays separate from the Proposal draft and remains reviewable.</p></div><button type="button" className="button-secondary" onClick={onBack}><Icon name="arrow-left" size={14} /> Proposal register</button></header>
    {error && <div className="proposal-alert error-state" role="alert"><Icon name="alert" size={17} /> <span>{error}</span></div>}
    <section className="panel source-choice-panel" aria-labelledby="source-choice-title"><div className="panel-head"><div><span className="eyebrow">STEP 1 · SOURCE / CONTEXT</span><h3 id="source-choice-title">How did this Proposal begin?</h3></div><small>Select one starting context. You can add more evidence from the Proposal workspace.</small></div><div className="source-option-grid" role="radiogroup" aria-label="Proposal source or starting context">{proposalSourceRegistry.map((option) => <button type="button" aria-pressed={source?.key === option.key} key={option.key} className={source?.key === option.key ? "source-option selected" : "source-option"} onClick={() => chooseSource(option)}><span className="source-option-icon"><Icon name={sourceIcon(option)} size={19} /></span><span className="source-option-copy"><b>{option.label}</b><small>{option.description}</small></span><span className="source-option-state" aria-hidden="true"><Icon name={source?.key === option.key ? "check" : "current"} size={17} /></span>{source?.key === option.key && <span className="sr-only">Selected</span>}</button>)}</div></section>
    {source && <section className="panel proposal-form-panel" aria-labelledby="proposal-details-title"><div className="panel-head"><div><span className="eyebrow">STEP 2 · PROPOSAL INFORMATION</span><h3 id="proposal-details-title">New Proposal from {source.label}</h3></div><span className="tag">Source selected</span></div><div className="proposal-form-grid"><label>Proposal title <RequiredMark /><input dir="auto" aria-label="Proposal title" required value={form.title} onChange={(event) => update("title", event.target.value)} placeholder="Commercial enquiry or tender name" /></label><label>Client <RequiredMark />{clientStatus}<select dir="auto" aria-label="Client" required value={selectedClientId || ""} onChange={(event) => chooseClient(event.target.value)} disabled={clientState.status !== "READY"}><option value="">Select an active canonical Client</option>{clientState.items.map((item) => <option key={item.id} value={item.id}>{item.name}{item.reference ? ` · ${item.reference}` : ""}</option>)}</select><input type="hidden" aria-label="Selected canonical Client ID" value={selectedClientId || ""} readOnly /></label><label>Project reference <span className="field-hint">Optional until a Project exists</span><input dir="auto" aria-label="Project reference" value={form.projectReference} onChange={(event) => update("projectReference", event.target.value)} placeholder="Project or client reference" /></label>{source.key === "CLIENT_DATA" && <><label>Proposal contact<input dir="auto" aria-label="Proposal contact" value={form.contact} onChange={(event) => update("contact", event.target.value)} placeholder="Contact name" /></label><label>Contact email<input dir="auto" aria-label="Contact email" value={form.email} onChange={(event) => update("email", event.target.value)} placeholder="name@client.example" type="email" /></label></>}{source.key !== "NONE" && <section className="proposal-source-details proposal-form-wide" aria-labelledby="source-details-title"><div><span className="eyebrow">STEP 3 · SOURCE EVIDENCE</span><h4 id="source-details-title">Evidence details</h4><p>These notes describe the source; they do not assert that external facts have been verified.</p></div><div className="proposal-form-grid"><label>Source title<input dir="auto" aria-label="Source title" value={form.sourceTitle} onChange={(event) => update("sourceTitle", event.target.value)} placeholder={source.acceptsFile ? "Title or filename" : "Client information source"} /></label><label>Source date<input dir="auto" aria-label="Source date" value={form.sourceDate} onChange={(event) => update("sourceDate", event.target.value)} type="date" /></label><label className="proposal-form-wide">Notes<textarea dir="auto" aria-label="Source notes" value={form.notes} onChange={(event) => update("notes", event.target.value)} placeholder="Human-entered context; not verified external fact" /></label></div></section>}</div>{source.acceptsFile && <div className="proposal-file-drop proposal-form-wide"><div><span className="eyebrow">INITIAL EVIDENCE FILE</span><b>{source.label} <RequiredMark /></b><small>{source.key === "TENDER_PHOTO" ? "Image files accepted." : "Choose the source document to register with this Proposal."}</small></div><input ref={fileRef} id="proposal-source-file" className="visually-hidden" aria-label={`${source.label} file`} type="file" accept={sourceAccept(source.key)} onChange={(event) => setFile(event.target.files?.[0] || null)} /><button type="button" className="button-secondary proposal-file-picker" onClick={() => fileRef.current?.click()}>{file ? "Replace file" : "Choose file"}</button>{file ? <div className="proposal-file-selected" role="status"><Icon name="check" size={15} /><span><BidiText as="b">{file.name}</BidiText><small>{(file.size / 1024).toFixed(0)} KB · ready to register as evidence</small></span><button type="button" className="text-button" onClick={clearFile}>Remove</button></div> : <p className="proposal-file-empty">No file selected yet.</p>}</div>}<div className="proposal-form-footer"><p><Icon name="shield" size={14} /> Document, DocumentVersion, hash, and provenance remain in the governed source system. Upload does not imply OCR or AI certainty.</p><button type="button" className="button-primary" onClick={() => void create()} disabled={busy || clientState.status !== "READY"}>{busy ? "Creating Proposal…" : "Create Proposal draft"}</button></div></section>}
    {!source && <div className="proposal-empty panel"><b>Choose a starting point to continue.</b><span>The Proposal draft is not created until you choose a source context.</span></div>}
  </div>;
}
