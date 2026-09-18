import { useEffect, useMemo, useRef, useState } from "react";
import { api, apiBlob } from "./api";

type Project = { number: number; name: string; state: string; discovery_class?: string; folder_count: number; file_count: number };
type Entry = { id: string; path: string; name: string; is_directory: boolean; size: number; modified_ns: number; content_type: string; logical_category?: CategoryKey; category_source?: string; included_in_proposal?: boolean; inclusion_origin?: string };
type Manifest = { completeness_state?: "COMPLETE" | "INCOMPLETE"; completeness_reasons?: string[]; source_manifest_hash?: string };
type CategoryKey = "TENDER_DOCUMENTS" | "PHOTOS_IMAGES" | "EMAIL" | "CLIENT_DATA" | "CLIENT_DOCUMENTS" | "PROJECT_INFORMATION" | "OTHER_UNCLASSIFIED";
type PendingSource = { file: File; category: CategoryKey };

const CATEGORY_DEFS: Array<{ key: CategoryKey; label: string; helper: string; sourceType: string }> = [
  { key: "TENDER_DOCUMENTS", label: "Tender Documents", helper: "RFP, scope, BOQ and specifications", sourceType: "TENDER_DOCUMENT" },
  { key: "PHOTOS_IMAGES", label: "Photos / Images", helper: "Tender photos, drawings and images", sourceType: "TENDER_PHOTO" },
  { key: "EMAIL", label: "Email", helper: "Email exports and correspondence", sourceType: "TENDER_EMAIL" },
  { key: "CLIENT_DATA", label: "Client Data", helper: "Client details and structured data", sourceType: "CLIENT_DATA" },
  { key: "CLIENT_DOCUMENTS", label: "Client Documents", helper: "Registrations, certificates and IDs", sourceType: "CLIENT_DATA" },
  { key: "PROJECT_INFORMATION", label: "Project Information", helper: "Plans, site information and project notes", sourceType: "TENDER_DOCUMENT" },
  { key: "OTHER_UNCLASSIFIED", label: "Other / Unclassified", helper: "Sources requiring Owner classification", sourceType: "TENDER_DOCUMENT" },
];
const roleHeaders = (role: string) => ({ "X-Dev-Role": role });
const formatSize = (size: number) => size < 1024 ? size + " B" : size < 1024 * 1024 ? (size / 1024).toFixed(1) + " KB" : (size / 1024 / 1024).toFixed(1) + " MB";

function classify(entry: Entry): CategoryKey {
  const value = (entry.path + " " + entry.name).toLowerCase();
  const ext = entry.name.toLowerCase().split(".").pop() || "";
  if (ext === "eml" || ext === "msg" || value.includes("email") || value.includes("correspondence")) return "EMAIL";
  if (["jpg", "jpeg", "png", "gif", "webp", "heic", "tif", "tiff", "bmp"].includes(ext) || /photo|image|screenshot|drawing|plan/.test(value)) return "PHOTOS_IMAGES";
  if (/client document|registration|certificate|commercial record|cr\b|identity|\bid\b/.test(value)) return "CLIENT_DOCUMENTS";
  if (/client data|client information|contact|company profile/.test(value)) return "CLIENT_DATA";
  if (/tender|rfp|rfq|boq|scope|specification|sow|schedule/.test(value) || ["pdf", "doc", "docx", "xls", "xlsx", "csv"].includes(ext)) return "TENDER_DOCUMENTS";
  if (/project|site|location|brief|method statement/.test(value)) return "PROJECT_INFORMATION";
  return "OTHER_UNCLASSIFIED";
}

export function ProposalSourceWorkspace({ role = "OWNER_SPONSOR", onBack, onOpenEditor }: { role?: string; onBack?: () => void; onOpenEditor?: (proposalId: string, revisionId: string, projectNumber: number) => void }) {
  const queryProject = Number(new URLSearchParams(window.location.search).get("project"));
  const hasQueryProject = Number.isFinite(queryProject) && queryProject > 0;
  const [projects, setProjects] = useState<Project[]>([]);
  const [selected, setSelected] = useState(hasQueryProject ? queryProject : 0);
  const [entries, setEntries] = useState<Entry[]>([]);
  const [activeFolder, setActiveFolder] = useState("");
  const [category, setCategory] = useState<CategoryKey | "ALL">("ALL");
  const [categoryDrafts, setCategoryDrafts] = useState<Record<string, CategoryKey>>({});
  const [savingCategory, setSavingCategory] = useState<Record<string, boolean>>({});
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [preview, setPreview] = useState("");
  const [loading, setLoading] = useState(false);
  const [createdProposal, setCreatedProposal] = useState("");
  const [pendingSources, setPendingSources] = useState<PendingSource[]>([]);
  const [savingInclusion, setSavingInclusion] = useState<Record<string, boolean>>({});
  const [manifest, setManifest] = useState<Manifest>({});
  const [sourceCategory, setSourceCategory] = useState<CategoryKey>("OTHER_UNCLASSIFIED");
  const fileInput = useRef<HTMLInputElement>(null);

  const projectName = projects.find((project) => project.number === selected)?.name || (selected ? String(selected) : "Synology source projects");
  const loadProjects = () => api<{ projects?: Project[] }>("/api/proposals/sources/2026/projects", { headers: roleHeaders(role) }).then((data) => {
    const next = data.projects || [];
    setProjects(next);
    if (!hasQueryProject && (!selected || !next.some((project) => project.number === selected))) setSelected(next[0]?.number || 0);
  }).catch((cause) => setError(cause instanceof Error ? cause.message : "Source projects unavailable."));
  const loadTree = () => {
    if (!selected) { setEntries([]); return; }
    setLoading(true); setPreview(""); setActiveFolder(""); setCategory("ALL"); setManifest({});
    Promise.all([
      api<{ entries?: Entry[] }>("/api/proposals/sources/2026/projects/" + selected + "/tree", { headers: roleHeaders(role) }),
      api<Manifest>("/api/proposals/sources/2026/projects/" + selected + "/manifest", { headers: roleHeaders(role) }),
    ])
      .then(([data, currentManifest]) => { const next = data.entries || []; setEntries(next); setManifest(currentManifest || {}); setCategoryDrafts(Object.fromEntries(next.filter((entry) => !entry.is_directory).map((entry) => [entry.id, (entry.logical_category || classify(entry)) as CategoryKey]))); })
      .catch((cause) => setError(cause instanceof Error ? cause.message : "Source tree unavailable."))
      .finally(() => setLoading(false));
  };
  useEffect(() => { void loadProjects(); }, [role]);
  useEffect(() => { void loadTree(); }, [selected]);

  const sync = async () => { setError(""); try { const data = await api<{ runs?: Array<{ project_number: number; captured_count: number; unchanged_count: number }> }>("/api/proposals/sources/2026/sync", { method: "POST", headers: roleHeaders(role) }); setMessage("Sync complete: " + (data.runs?.map((run) => run.project_number + ": " + run.captured_count + " new, " + run.unchanged_count + " unchanged").join(" · ") || "no changes")); await loadProjects(); await loadTree(); } catch (cause) { setError(cause instanceof Error ? cause.message : "Sync failed."); } };
  const createProposal = async () => {
    setError(""); setCreatedProposal("");
    try {
      const data = await api<{ proposal_id?: string; proposal_reference?: string; editor_ready?: boolean; editor_revision_id?: string; source_count?: number }>("/api/proposals/sources/2026/projects/" + selected + "/create-proposal", { method: "POST", headers: roleHeaders(role), body: JSON.stringify({}) });
      let editorReady = data.editor_ready;
      let editorRevisionId = data.editor_revision_id;
      if (data.proposal_id) {
        for (const pending of pendingSources) {
          const body = new FormData(); body.append("source_type", CATEGORY_DEFS.find((item) => item.key === pending.category)?.sourceType || "TENDER_DOCUMENT"); body.append("logical_category", pending.category); body.append("file", pending.file);
          await api("/api/bd/proposals/" + data.proposal_id + "/sources", { method: "POST", headers: roleHeaders(role), body });
        }
        // Owner-added sources are linked after the JSON promotion request. A
        // single explicit regeneration makes those files part of the exact AI
        // context before the editor opens.
        if (pendingSources.length) {
          const regenerated = await api<{ editor_ready?: boolean; editor_revision_id?: string }>("/api/proposals/sources/proposals/" + data.proposal_id + "/regenerate", { method: "POST", headers: roleHeaders(role) });
          editorReady = regenerated.editor_ready;
          editorRevisionId = regenerated.editor_revision_id;
        }
      }
      setPendingSources([]); setCreatedProposal(data.proposal_reference || data.proposal_id || "created"); setMessage("Proposal created from " + (data.source_count || 0) + " included Synology source files" + (pendingSources.length ? " and " + pendingSources.length + " Owner source(s)." : "."));
      if (editorReady && data.proposal_id && editorRevisionId && onOpenEditor) onOpenEditor(data.proposal_id, editorRevisionId, selected);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Proposal creation failed."); }
  };
  const categoryFor = (entry: Entry): CategoryKey => (categoryDrafts[entry.id] || entry.logical_category || classify(entry)) as CategoryKey;
  const persistedCategoryFor = (entry: Entry): CategoryKey => (entry.logical_category || classify(entry)) as CategoryKey;
  const categoryDirty = (entry: Entry) => !entry.is_directory && categoryFor(entry) !== persistedCategoryFor(entry);
  const saveCategory = async (entry: Entry) => {
    if (!categoryDirty(entry)) return;
    setSavingCategory((current) => ({ ...current, [entry.id]: true })); setError("");
    try {
      const saved = await api<{ logical_category: CategoryKey; category_source?: string }>("/api/proposals/sources/2026/projects/" + selected + "/files/" + entry.id + "/category", { method: "PATCH", headers: roleHeaders(role), body: JSON.stringify({ logical_category: categoryFor(entry) }) });
      setEntries((current) => current.map((item) => item.id === entry.id ? { ...item, logical_category: saved.logical_category, category_source: saved.category_source || "OWNER_OVERRIDE" } : item));
      setCategoryDrafts((current) => ({ ...current, [entry.id]: saved.logical_category }));
      setMessage(entry.name + " category saved.");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Category could not be saved."); }
    finally { setSavingCategory((current) => ({ ...current, [entry.id]: false })); }
  };
  const addPendingSource = () => { const file = fileInput.current?.files?.[0]; if (!file) return; setPendingSources((current) => [...current, { file, category: sourceCategory }]); if (fileInput.current) fileInput.current.value = ""; setMessage(file.name + " staged as an Owner source. It will be linked when you create the Proposal."); };
  const physicalFiles = useMemo(() => entries.filter((entry) => !entry.is_directory && (!activeFolder || entry.path.startsWith(activeFolder + "/"))), [entries, activeFolder]);
  const folders = useMemo(() => entries.filter((entry) => entry.is_directory && entry.path !== projectName && entry.path !== projectName.replace(/^\d+\s*-\s*/, "")), [entries, projectName]);
  const visibleFiles = useMemo(() => physicalFiles.filter((entry) => category === "ALL" || categoryFor(entry) === category), [physicalFiles, category, categoryDrafts]);
  const counts = useMemo(() => Object.fromEntries(CATEGORY_DEFS.map((item) => [item.key, physicalFiles.filter((entry) => categoryFor(entry) === item.key).length])), [physicalFiles, categoryDrafts]) as Record<CategoryKey, number>;
  const hasDirtyCategories = physicalFiles.some(categoryDirty);
  const hasSavingChanges = Object.values(savingCategory).some(Boolean) || Object.values(savingInclusion).some(Boolean);
  const hasIncompleteManifest = manifest.completeness_state === "INCOMPLETE";
  const openFile = async (entry: Entry) => { try { const blob = await apiBlob("/api/proposals/sources/2026/projects/" + selected + "/files/" + entry.id + "/content", { headers: roleHeaders(role) }); const url = URL.createObjectURL(blob); if (entry.content_type.startsWith("image/") || entry.content_type === "application/pdf") setPreview(url); else { const opened = window.open(url, "_blank"); if (!opened) { const link = document.createElement("a"); link.href = url; link.target = "_blank"; link.rel = "noreferrer"; link.click(); } } } catch (cause) { setError(cause instanceof Error ? cause.message : "File could not be opened."); } };
  const download = async (entry: Entry) => { try { const blob = await apiBlob("/api/proposals/sources/2026/projects/" + selected + "/files/" + entry.id + "/download", { headers: roleHeaders(role) }); const link = document.createElement("a"); link.href = URL.createObjectURL(blob); link.download = entry.name; link.click(); } catch (cause) { setError(cause instanceof Error ? cause.message : "File could not be downloaded."); } };
  const toggleIncluded = async (entry: Entry) => {
    const included = entry.included_in_proposal !== false;
    setSavingInclusion((current) => ({ ...current, [entry.id]: true })); setError("");
    try {
      const saved = await api<{ included_in_proposal: boolean; inclusion_origin?: string }>("/api/proposals/sources/2026/projects/" + selected + "/files/" + entry.id + "/inclusion", { method: "PATCH", headers: roleHeaders(role), body: JSON.stringify({ included_in_proposal: !included }) });
      setEntries((current) => current.map((item) => item.id === entry.id ? { ...item, included_in_proposal: saved.included_in_proposal, inclusion_origin: saved.inclusion_origin || "OWNER" } : item));
      setMessage(entry.name + (saved.included_in_proposal ? " added back to the Proposal source set." : " removed from the Proposal source set. Synology was not changed."));
      const currentManifest = await api<Manifest>("/api/proposals/sources/2026/projects/" + selected + "/manifest", { headers: roleHeaders(role) }); setManifest(currentManifest || {});
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Source inclusion could not be saved."); }
    finally { setSavingInclusion((current) => ({ ...current, [entry.id]: false })); }
  };

  return <section className="panel proposal-source-workspace" aria-label="Proposal source workspace">
    <div className="panel-head"><div><span className="eyebrow">PROPOSALS V1 · SOURCE WORKSPACE</span><h3>{projectName}</h3><p className="muted">Tenders &gt; 1- Proposal &gt; 2026 · exact Synology source names and read-only capture</p></div>{onBack && <button className="button-secondary" onClick={onBack}>Back to Proposals V1</button>}</div>
    {error && <div className="error-state" role="alert">{error}<button className="button-secondary" onClick={() => { setError(""); void loadTree(); }}>Retry</button></div>}
    {message && <div className="inline-message" role="status">{message}</div>}
    <div className="source-workspace-toolbar"><button className="button-secondary" onClick={() => void sync()}>Sync now</button><button className="button-primary" onClick={() => void createProposal()} disabled={!selected || hasDirtyCategories || hasSavingChanges || hasIncompleteManifest}>Create Proposal</button><span className="muted">Draft · Synology read-only · writes: 0{hasDirtyCategories ? " · Save category changes before creating" : hasIncompleteManifest ? " · Sync all sources before creating" : ""}</span></div>
    {manifest.completeness_state && <div className={hasIncompleteManifest ? "error-state" : "inline-message"} role="status">Source completeness: {manifest.completeness_state}{hasIncompleteManifest && manifest.completeness_reasons?.length ? " · " + manifest.completeness_reasons.join(", ") : ""}</div>}
    {createdProposal && <div className="inline-message" role="status">Created Proposal {createdProposal}</div>}
    <div className="source-workspace-projects" role="tablist" aria-label="Synced source projects">{projects.map((project) => <button key={project.number} role="tab" aria-selected={selected === project.number} className={selected === project.number ? "active" : ""} onClick={() => setSelected(project.number)}><b>{project.number} · {project.name.replace(/^\d+\s*-\s*/, "")}</b><small>Draft · {project.file_count} files</small></button>)}</div>
    <div className="source-breadcrumb">Tenders <span>›</span> 1- Proposal <span>›</span> 2026 <span>›</span> <b>{projectName.replace(/^\d+\s*-\s*/, "")}</b></div>
    {loading ? <p className="muted">Loading source tree…</p> : <div className="source-tree">
      <div className="source-tree-folders">{folders.map((entry) => <button className={"source-folder " + (activeFolder === entry.path ? "active" : "")} key={entry.id} onClick={() => setActiveFolder(entry.path)}><b>{entry.name}</b><small>{entries.filter((child) => child.path.startsWith(entry.path + "/")).length} items</small></button>)}</div>
      <div className="source-category-grid" role="tablist" aria-label="Logical source categories"><button className={category === "ALL" ? "active" : ""} onClick={() => setCategory("ALL")}>All sources <b>{physicalFiles.length}</b></button>{CATEGORY_DEFS.map((item) => <button key={item.key} className={category === item.key ? "active" : ""} onClick={() => setCategory(item.key)}>{item.label} <b>{counts[item.key]}</b></button>)}</div>
      <div className="source-file-list">{visibleFiles.length ? visibleFiles.map((entry) => { const itemCategory = categoryFor(entry); const included = entry.included_in_proposal !== false; const dirty = categoryDirty(entry); return <div className={"source-file " + (!included ? "excluded" : "")} key={entry.id}><div className="source-file-copy"><b>{entry.name}</b><small><span className="source-badge">Synology</span> {entry.path} · {formatSize(entry.size)} · {entry.content_type}{entry.category_source === "OWNER_OVERRIDE" ? " · Owner category" : " · Suggested category"}{!included ? " · Excluded from Proposal" : ""}</small><label className="source-category-select">Logical category<select value={itemCategory} onChange={(event) => setCategoryDrafts((current) => ({ ...current, [entry.id]: event.target.value as CategoryKey }))}>{CATEGORY_DEFS.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}</select></label></div><div className="source-file-actions"><button className="source-file-action" onClick={() => void saveCategory(entry)} disabled={!dirty || savingCategory[entry.id]}>{savingCategory[entry.id] ? "Saving…" : dirty ? "Save category" : "Saved"}</button><button className="source-file-action" onClick={() => void openFile(entry)}>View</button><button className="source-file-action" onClick={() => download(entry)}>Download</button><button className="source-file-action" onClick={() => void toggleIncluded(entry)} disabled={savingInclusion[entry.id]}>{savingInclusion[entry.id] ? "Saving…" : included ? "Remove from Proposal" : "Add back to Proposal"}</button></div></div>; }) : <p className="muted">No sources in this category.</p>}</div>
    </div>}
    <div className="source-add-row"><label>Owner source category<select value={sourceCategory} onChange={(event) => setSourceCategory(event.target.value as CategoryKey)}>{CATEGORY_DEFS.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}</select></label><input ref={fileInput} aria-label="Add source file" type="file" /><button type="button" className="button-secondary" onClick={addPendingSource}>＋ Add Source</button>{pendingSources.length > 0 && <span className="muted">{pendingSources.length} Owner source{pendingSources.length === 1 ? "" : "s"} staged</span>}</div>
    {preview && <div className="source-preview"><div className="panel-head"><h4>Source preview</h4><button className="button-secondary" onClick={() => setPreview("")}>Close</button></div><iframe title="Source file preview" src={preview} /></div>}
  </section>;
}
