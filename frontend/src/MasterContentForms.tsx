import { useEffect, useState } from "react";
import { api } from "./api";

type Category = { id: string; label: string; allowed_content_types: string[]; source_kind?: string };
type Version = { id: string; version: number; status: string; file_name: string; updated_by: string; updated_at: string; change_reason?: string };
export type CanonicalForm = { id: string; serial_number?: number; ref: string; content_type: "FORM"; title: string; category?: { id: string; label: string } | null; description?: string; used_in?: string[]; version?: number; version_status: string; updated?: string; versions?: Version[] };

const ownerRoles = new Set(["SYSTEM_ADMIN", "OWNER_SPONSOR"]);
const MODULES = ["MY_WORK", "BD", "ADMIN", "ENGINEERING", "PERMIT", "ISSUES", "NOTIFICATIONS", "REPORTS", "PROPOSAL", "CONTRACT"];

export function CanonicalFormsLibrary({ role, surface = "DASHBOARD", compact = false }: { role: string; surface?: "DASHBOARD" | "ADMINISTRATION"; compact?: boolean }) {
  const [forms, setForms] = useState<CanonicalForm[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editor, setEditor] = useState<CanonicalForm | null | undefined>(undefined);
  const [history, setHistory] = useState<{ itemId: string; title: string; versions: Version[] } | null>(null);
  const [busy, setBusy] = useState(false);
  const canWrite = ownerRoles.has(role);
  const load = async () => {
    setLoading(true); setError("");
    try {
      const [content, categoryRows] = await Promise.all([
        api<CanonicalForm[]>("/api/master-content?content_type=FORM"),
        api<Category[]>("/api/master-content/categories"),
      ]);
      setForms(content); setCategories(categoryRows);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Forms could not be loaded.");
    } finally { setLoading(false); }
  };
  useEffect(() => { void load(); }, []);
  const save = async (form: FormData) => {
    setBusy(true); setError("");
    try {
      await api(editor ? `/api/master-content/${editor.id}/versions` : "/api/master-content", {
        method: "POST", body: form,
        headers: { "Idempotency-Key": crypto.randomUUID(), "X-Source-Surface": surface },
      });
      setEditor(undefined); await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The Form change could not be saved.");
    } finally { setBusy(false); }
  };
  return <section className={`panel dashboard-section canonical-forms-library ${compact ? "canonical-forms-library-compact" : ""}`} data-testid={`${surface.toLowerCase()}-forms`}>
    <div className="dashboard-section-head"><div><span className="eyebrow">{surface === "ADMINISTRATION" ? "ADMINISTRATION · CANONICAL FORMS" : "MASTER LIBRARY"}</span><h3>Forms</h3></div>{canWrite && <button className="button-primary" onClick={() => setEditor(null)}>New Form</button>}</div>
    {surface === "ADMINISTRATION" && <p className="admin-owner-copy canonical-forms-description">The same canonical Forms library used by Dashboard, AMEC Work, Business Development, and Permit workflows.</p>}
    {error && <div className="dashboard-error" role="alert"><b>Forms unavailable</b><span>{error}</span><button className="button-secondary" onClick={() => void load()}>Retry</button></div>}
    {loading ? <div className="dashboard-state" role="status">Loading Forms…</div> : <div className="dashboard-table-wrap"><table className="dashboard-table"><thead><tr><th>S/N</th><th>Reference</th><th>Form Name</th><th>Category</th><th>Description</th><th>Used In</th><th>Current Version</th><th>Status</th><th>Updated</th><th>Action</th></tr></thead><tbody>{forms.map((form, index) => <tr key={form.id}><td>{form.serial_number || index + 1}</td><td>{form.ref}</td><td><b>{form.title}</b></td><td>{form.category?.label || "—"}</td><td>{form.description || "—"}</td><td>{form.used_in?.join(" · ") || "—"}</td><td>v{form.version || "—"}</td><td><span className="dashboard-status">{form.version_status}</span></td><td>{form.updated ? new Date(form.updated).toLocaleDateString() : "—"}</td><td className="dashboard-actions"><button onClick={() => void downloadForm(form.id)}>Open</button>{canWrite && <button onClick={() => setEditor(form)}>Modify</button>}<button onClick={async () => { const detail = await api<CanonicalForm>(`/api/master-content/${form.id}`); setHistory({ itemId: form.id, title: `${form.ref} · ${form.title}`, versions: detail.versions || [] }); }}>Version History</button></td></tr>)}</tbody></table>{forms.length === 0 && <div className="dashboard-empty">No Forms are available.</div>}</div>}
    {editor !== undefined && <FormEditor item={editor || undefined} categories={categories} busy={busy} onClose={() => setEditor(undefined)} onSave={save} />}
    {history && <FormHistory history={history} onClose={() => setHistory(null)} />}
  </section>;
}

function FormEditor({ item, categories, busy, onClose, onSave }: { item?: CanonicalForm; categories: Category[]; busy: boolean; onClose: () => void; onSave: (form: FormData) => Promise<void> }) {
  const [ref, setRef] = useState(""); const [title, setTitle] = useState(item?.title || ""); const [category, setCategory] = useState(item?.category?.id || ""); const [description, setDescription] = useState(item?.description || ""); const [usedIn, setUsedIn] = useState(item?.used_in || []); const [reason, setReason] = useState(""); const [file, setFile] = useState<File | null>(null);
  const submit = (event: React.FormEvent) => { event.preventDefault(); const form = new FormData(); if (!item) { form.append("content_type", "FORM"); if (ref.trim()) form.append("ref", ref.trim()); } else { form.append("expected_current_version", String(item.version || 0)); form.append("change_reason", reason); } form.append("title", title); if (category) form.append("category_id", category); form.append("description", description); form.append("used_in", JSON.stringify(usedIn)); if (file) form.append("file", file); void onSave(form); };
  return <div className="dashboard-modal-backdrop"><form className="dashboard-modal" onSubmit={submit}><div className="dashboard-modal-head"><div><span className="eyebrow">{item ? "MODIFY · NEW VERSION" : "NEW MASTER FORM"}</span><h3>{item ? `${item.ref} · ${item.title}` : "New Form"}</h3></div><button type="button" className="modal-close" onClick={onClose}>×</button></div><label>Form Name<input aria-label="Title / Name" required value={title} onChange={event => setTitle(event.target.value)} /></label><label>Reference<small className="field-help">Leave blank for a system-generated stable reference (for example F-0001).</small><input aria-label="Reference" placeholder="Auto-generated on save" value={ref} onChange={event => setRef(event.target.value)} /></label><label>Category<select value={category} onChange={event => setCategory(event.target.value)}><option value="">Select category</option>{categories.filter(row => row.allowed_content_types.includes("FORM")).map(row => <option value={row.id} key={row.id}>{row.label}</option>)}</select></label><label>Description<textarea value={description} onChange={event => setDescription(event.target.value)} /></label><fieldset className="used-in-fields"><legend>Used In</legend><div className="used-in-grid">{MODULES.map(module => <label key={module}><input type="checkbox" checked={usedIn.includes(module)} onChange={event => setUsedIn(event.target.checked ? [...usedIn, module] : usedIn.filter(value => value !== module))} />{module.replaceAll("_", " ")}</label>)}</div></fieldset>{item && <label>Change reason<input required value={reason} onChange={event => setReason(event.target.value)} /></label>}<label>Source Document{item && <small className="field-help">Leave empty for a metadata-only immutable snapshot.</small>}<input aria-label="File" type="file" accept=".pdf,.docx,.doc,.xlsx,.xls,.txt,.csv" required={!item} onChange={event => setFile(event.target.files?.[0] || null)} /></label><section className="ai-assist-shell"><div><b>✨ AI Assist</b><span>Coming Soon · human acceptance required</span></div><button type="button" disabled>Suggest Category</button><button type="button" disabled>Improve Description</button></section><div className="dashboard-modal-foot"><button type="button" className="button-secondary" onClick={onClose}>Cancel</button><button className="button-primary" disabled={busy}>{busy ? "Verifying storage…" : item ? "Save new version" : "Save and verify"}</button></div></form></div>;
}

function FormHistory({ history, onClose }: { history: { itemId: string; title: string; versions: Version[] }; onClose: () => void }) { return <div className="dashboard-modal-backdrop"><section className="dashboard-modal history-modal"><div className="dashboard-modal-head"><div><span className="eyebrow">IMMUTABLE HISTORY</span><h3>{history.title}</h3></div><button className="modal-close" onClick={onClose}>×</button></div><div className="history-list">{history.versions.map(version => <div className="history-row" key={version.id}><b>v{version.version}</b><span className="dashboard-status">{version.status}</span><span>{version.file_name}</span><button className="history-download" onClick={() => void downloadFormVersion(history.itemId, version.id, version.file_name)}>Download</button><small>{version.change_reason || "—"} · {version.updated_by} · {new Date(version.updated_at).toLocaleString()}</small></div>)}</div></section></div>; }

async function downloadForm(itemId: string) { const response = await fetch(`/api/master-content/${itemId}/download`, { headers: { "X-Dev-Role": sessionStorage.getItem("proposalops-role") || "SYSTEM_ADMIN" } }); if (!response.ok) throw new Error("The Form could not be opened."); const blob = await response.blob(); const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = "form"; link.click(); URL.revokeObjectURL(url); }
async function downloadFormVersion(itemId: string, versionId: string, fileName: string) { const response = await fetch(`/api/master-content/${itemId}/versions/${versionId}/download`, { headers: { "X-Dev-Role": sessionStorage.getItem("proposalops-role") || "SYSTEM_ADMIN" } }); if (!response.ok) throw new Error("The Form version could not be opened."); const blob = await response.blob(); const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = fileName; link.click(); URL.revokeObjectURL(url); }
