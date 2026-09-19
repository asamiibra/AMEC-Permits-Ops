import { useEffect, useMemo, useRef, useState } from "react";
import { api, apiBlob } from "./api";
import { BidiCode, BidiText } from "./BidiText";

type Project = { number: number; name: string; state: string; discovery_class?: string; folder_count: number; file_count: number; completeness_state?: "COMPLETE" | "INCOMPLETE"; completeness_reasons?: string[]; scan_status?: string; snapshot_at?: string };
type Entry = { id: string; path: string; name: string; is_directory: boolean; size: number; modified_ns: number; content_type: string; logical_category?: CategoryKey; category_source?: string; included_in_proposal?: boolean; inclusion_origin?: string };
type Manifest = { completeness_state?: "COMPLETE" | "INCOMPLETE"; completeness_reasons?: string[]; scan_status?: string; source_manifest_hash?: string; snapshot_at?: string; entries?: Array<{ document_version_id?: string | null }> };
type CategoryKey = "TENDER_DOCUMENTS" | "PHOTOS_IMAGES" | "EMAIL" | "CLIENT_DATA" | "CLIENT_DOCUMENTS" | "PROJECT_INFORMATION" | "OTHER_UNCLASSIFIED";
type PendingSource = { file: File; category: CategoryKey };
type SyncStatus = "NOT_SYNCED" | "SYNCING" | "COMPLETE" | "NEEDS_ATTENTION" | "FAILED";
type CreateStatus = "NOT_CREATED" | "READY_TO_CREATE" | "CREATING" | "GENERATING" | "DRAFT_READY" | "NEEDS_ATTENTION";

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

export function ProposalSourceWorkspace({ role = "OWNER_SPONSOR", onBack, onOpenEditor, onOpenProposal }: { role?: string; onBack?: () => void; onOpenEditor?: (proposalId: string, revisionId: string, projectNumber: number) => void; onOpenProposal?: (proposalId: string) => void }) {
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
  const [stagingSessionId, setStagingSessionId] = useState("");
  const [savingInclusion, setSavingInclusion] = useState<Record<string, boolean>>({});
  const [manifest, setManifest] = useState<Manifest>({});
  const [manifestLoaded, setManifestLoaded] = useState(false);
  const [syncStatus, setSyncStatus] = useState<SyncStatus>("NOT_SYNCED");
  const [syncSummary, setSyncSummary] = useState("");
  const [createStatus, setCreateStatus] = useState<CreateStatus>("NOT_CREATED");
  const [sourceCategory, setSourceCategory] = useState<CategoryKey>("OTHER_UNCLASSIFIED");
  const fileInput = useRef<HTMLInputElement>(null);

  const projectName = projects.find((project) => project.number === selected)?.name || (selected ? String(selected) : "Synology source projects");
  const loadProjects = () => api<{ projects?: Project[] }>("/api/proposals/sources/2026/projects", { headers: roleHeaders(role) }).then((data) => {
    const next = data.projects || [];
    setProjects(next);
    if (!hasQueryProject && (!selected || !next.some((project) => project.number === selected))) setSelected(next[0]?.number || 0);
  }).catch((cause) => setError(cause instanceof Error ? cause.message : "Source projects unavailable."));
  const applyManifest = (currentManifest: Manifest) => {
    setManifest(currentManifest || {});
    setManifestLoaded(true);
    setSyncStatus(currentManifest?.completeness_state === "COMPLETE" ? "COMPLETE" : "NEEDS_ATTENTION");
  };
  const loadTree = async () => {
    if (!selected) { setEntries([]); setManifestLoaded(false); setSyncStatus("NOT_SYNCED"); return null; }
    setLoading(true); setPreview(""); setActiveFolder(""); setCategory("ALL"); setManifest({}); setManifestLoaded(false);
    try {
      const [data, currentManifest] = await Promise.all([
        api<{ entries?: Entry[] }>("/api/proposals/sources/2026/projects/" + selected + "/tree", { headers: roleHeaders(role) }),
        api<Manifest>("/api/proposals/sources/2026/projects/" + selected + "/manifest", { headers: roleHeaders(role) }),
      ]);
      const next = data.entries || [];
      setEntries(next); applyManifest(currentManifest || {});
      setCategoryDrafts(Object.fromEntries(next.filter((entry) => !entry.is_directory).map((entry) => [entry.id, (entry.logical_category || classify(entry)) as CategoryKey])));
      return currentManifest || {};
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Source tree unavailable.");
      return null;
    } finally { setLoading(false); }
  };
  useEffect(() => { void loadProjects(); }, [role]);
  useEffect(() => { void loadTree(); }, [selected]);

  const sync = async () => {
    if (!selected || syncStatus === "SYNCING" || createStatus === "CREATING" || createStatus === "GENERATING") return;
    setError(""); setMessage(""); setSyncStatus("SYNCING"); setSyncSummary("");
    try {
      const data = await api<{ runs?: Array<{ project_number: number; captured_count: number; unchanged_count: number }> }>(`/api/proposals/sources/2026/sync?project=${encodeURIComponent(String(selected))}`, { method: "POST", headers: roleHeaders(role) });
      await loadProjects();
      const latest = await loadTree();
      const run = data.runs?.find((item) => item.project_number === selected) || data.runs?.[0];
      if (latest?.completeness_state === "COMPLETE") {
        setSyncStatus("COMPLETE");
        const totalFiles = latest?.entries?.length ?? entries.filter((entry) => !entry.is_directory).length;
        setSyncSummary(`${totalFiles} files · ${run?.captured_count || 0} new · ${run?.unchanged_count || 0} unchanged`);
        setMessage("");
      } else {
        setSyncStatus("NEEDS_ATTENTION");
        setSyncSummary(latest?.completeness_reasons?.[0] || "Source snapshot needs attention");
      }
    } catch (cause) { setSyncStatus("FAILED"); setSyncSummary(cause instanceof Error ? cause.message : "Source sync failed."); setError(""); }
  };
  const createProposal = async () => {
    if (!selected || syncStatus !== "COMPLETE" || !manifestLoaded || manifest.completeness_state !== "COMPLETE" || hasDirtyCategories || hasSavingChanges) return;
    setError(""); setCreatedProposal(""); setCreateStatus("CREATING"); setMessage("Creating Proposal…");
    try {
      let durableStagingSessionId = stagingSessionId;
      if (pendingSources.length && !durableStagingSessionId) {
        const stagingBody = new FormData();
        pendingSources.forEach((pending) => stagingBody.append("files", pending.file));
        stagingBody.append("logical_categories", JSON.stringify(pendingSources.map((pending) => pending.category)));
        const staged = await api<{ staging_session_id: string }>("/api/proposals/sources/2026/projects/" + selected + "/staging", { method: "POST", headers: roleHeaders(role), body: stagingBody });
        durableStagingSessionId = staged.staging_session_id;
        setStagingSessionId(durableStagingSessionId);
      }
      const data = await api<{ proposal_id?: string; proposal_reference?: string; editor_ready?: boolean; editor_revision_id?: string; generation_state?: string; source_count?: number }>("/api/proposals/sources/2026/projects/" + selected + "/create-proposal", { method: "POST", headers: roleHeaders(role), body: JSON.stringify({ defer_generation: false, staging_session_id: durableStagingSessionId || undefined }) });
      let editorReady = data.editor_ready;
      let editorRevisionId = data.editor_revision_id;
      if (data.proposal_id) {
        // Owner-added sources are linked after the JSON promotion request. A
        // single explicit regeneration makes those files part of the exact AI
        // context before the editor opens.
        setStagingSessionId("");
      }
      setPendingSources([]); setCreatedProposal(data.proposal_reference || data.proposal_id || "created");
      setCreateStatus(["READY_FOR_EDIT", "NO_AI_CHANGES_REQUIRED"].includes(data.generation_state || "") ? "DRAFT_READY" : "GENERATING");
      setMessage(data.generation_state && !["READY_FOR_EDIT", "NO_AI_CHANGES_REQUIRED"].includes(data.generation_state) ? "Proposal created · generation in progress" : "Proposal draft ready");
      if (data.proposal_id) {
        if (["READY_FOR_EDIT", "NO_AI_CHANGES_REQUIRED"].includes(data.generation_state || "") && editorReady && editorRevisionId && onOpenEditor) onOpenEditor(data.proposal_id, editorRevisionId, selected);
        else if (onOpenProposal) onOpenProposal(data.proposal_id);
      }
    } catch (cause) {
      const code = cause && typeof cause === "object" && "code" in cause ? String((cause as { code?: unknown }).code || "") : "";
      if (code === "SOURCE_SNAPSHOT_INCOMPLETE") {
        const latest = await loadTree();
        setSyncStatus(latest?.completeness_state === "COMPLETE" ? "COMPLETE" : "NEEDS_ATTENTION");
        setCreateStatus("NEEDS_ATTENTION");
        setMessage("");
      } else { setCreateStatus("NEEDS_ATTENTION"); setError(cause instanceof Error ? cause.message : "Proposal creation failed."); }
    }
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
  // Filtering and counts use the persisted category.  A dropdown edit is a
  // pending Owner decision and must not move a source until Save category
  // returns the authoritative server value.
  const visibleFiles = useMemo(() => physicalFiles.filter((entry) => category === "ALL" || persistedCategoryFor(entry) === category), [physicalFiles, category, entries]);
  const counts = useMemo(() => Object.fromEntries(CATEGORY_DEFS.map((item) => [item.key, physicalFiles.filter((entry) => persistedCategoryFor(entry) === item.key).length])), [physicalFiles, entries]) as Record<CategoryKey, number>;
  const hasDirtyCategories = physicalFiles.some(categoryDirty);
  const hasSavingChanges = Object.values(savingCategory).some(Boolean) || Object.values(savingInclusion).some(Boolean);
  const hasIncompleteManifest = !manifestLoaded || manifest.completeness_state !== "COMPLETE";
  const showSnapshotIncomplete = manifestLoaded && hasIncompleteManifest && syncStatus !== "SYNCING";
  const operationBusy = syncStatus === "SYNCING" || createStatus === "CREATING" || createStatus === "GENERATING";
  const createDisabledReason = !selected || !manifestLoaded || syncStatus === "NOT_SYNCED" ? "Finish source sync first" : syncStatus === "FAILED" ? "Source sync failed" : syncStatus !== "COMPLETE" || hasIncompleteManifest ? "Source snapshot needs attention" : hasDirtyCategories ? "Save category changes first" : hasSavingChanges ? "Finish source changes first" : "";
  const showSyncFailure = syncStatus === "FAILED" && Boolean(syncSummary);
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
    <div className="panel-head"><div><span className="eyebrow">PROPOSALS V1 · SOURCE WORKSPACE</span><h3><BidiText>{projectName}</BidiText></h3><p className="muted">Tenders &gt; 1- Proposal &gt; 2026 · exact Synology source names and read-only capture</p></div>{onBack && <button className="button-secondary" onClick={onBack}>Back to Proposals V1</button>}</div>
    {error && <div className="error-state" role="alert"><BidiText>{error}</BidiText></div>}
    <div className="source-workspace-status-grid">
      <div className="source-operation-status"><span className="eyebrow">SOURCE SYNC</span><b>{syncStatus === "SYNCING" ? "Syncing…" : syncStatus.replaceAll("_", " ")}</b><small>{syncStatus === "SYNCING" ? "Scanning and capturing this project" : syncSummary || (manifestLoaded && manifest.completeness_state === "COMPLETE" ? `${entries.filter((entry) => !entry.is_directory).length} files · snapshot current` : "Sync this project before creating a Proposal")}</small></div>
      <div className="source-operation-status"><span className="eyebrow">PROPOSAL CREATION</span><b>{createStatus === "READY_TO_CREATE" || createStatus === "NOT_CREATED" ? "Ready to create" : createStatus.replaceAll("_", " ")}</b><small>{createdProposal ? `Proposal ${createdProposal}` : createStatus === "GENERATING" ? "AI is generating the canonical DOCX" : createStatus === "DRAFT_READY" ? "Draft Proposal is ready" : "No Proposal exists for this source project"}</small></div>
    </div>
    <div className="source-workspace-toolbar"><button className="button-secondary" onClick={() => void sync()} disabled={!selected || operationBusy}>{syncStatus === "SYNCING" ? "Syncing…" : "Sync sources"}</button><button className={createDisabledReason ? "button-primary button-disabled" : "button-primary"} onClick={() => void createProposal()} disabled={!selected || operationBusy || syncStatus !== "COMPLETE" || hasIncompleteManifest || hasDirtyCategories || hasSavingChanges} aria-disabled={Boolean(createDisabledReason)}>Create Proposal</button><span className="muted" role="status">{createDisabledReason || (createStatus === "CREATING" ? "Creating Proposal…" : createStatus === "GENERATING" ? "Generating Proposal…" : "Ready to create")}</span></div>
    {showSyncFailure && <div className="error-state" role="alert"><b>Source sync failed</b><p>{syncSummary}</p><button className="button-secondary" onClick={() => void sync()} disabled={operationBusy}>Retry sync</button></div>}
    {showSnapshotIncomplete && <div className="error-state" role="alert"><b>Source snapshot needs attention</b>{manifest.completeness_reasons?.length ? <ul>{manifest.completeness_reasons.map((reason) => <li key={reason}><BidiText>{reason}</BidiText></li>)}</ul> : <p>Sync has not produced a complete source snapshot.</p>}{manifest.scan_status && <BidiText as="small">Scan status: {manifest.scan_status}</BidiText>}<button className="button-secondary" onClick={() => void sync()} disabled={operationBusy}>Retry Sync</button></div>}
    {message && !showSnapshotIncomplete && <div className="inline-message" role="status"><BidiText>{message}</BidiText></div>}
    {createdProposal && createStatus === "DRAFT_READY" && <div className="inline-message" role="status"><BidiText>Draft Proposal {createdProposal} is ready.</BidiText></div>}
    <div className="source-breadcrumb">Tenders <span>›</span> 1- Proposal <span>›</span> 2026 <span>›</span> <BidiText as="b">{projectName.replace(/^\d+\s*-\s*/, "")}</BidiText></div>
    {loading ? <p className="muted">Loading source tree…</p> : <div className="source-tree">
      <div className="source-tree-folders">{folders.map((entry) => <button className={"source-folder " + (activeFolder === entry.path ? "active" : "")} key={entry.id} onClick={() => setActiveFolder(entry.path)}><BidiCode as="b">{entry.name}</BidiCode><small>{entries.filter((child) => child.path.startsWith(entry.path + "/")).length} items</small></button>)}</div>
      <div className="source-category-grid" role="tablist" aria-label="Logical source categories"><button className={category === "ALL" ? "active" : ""} onClick={() => setCategory("ALL")}>All sources <b>{physicalFiles.length}</b></button>{CATEGORY_DEFS.map((item) => <button key={item.key} className={category === item.key ? "active" : ""} onClick={() => setCategory(item.key)}>{item.label} <b>{counts[item.key]}</b></button>)}</div>
      <div className="source-file-list">{visibleFiles.length ? visibleFiles.map((entry) => { const itemCategory = categoryFor(entry); const included = entry.included_in_proposal !== false; const dirty = categoryDirty(entry); return <div className={"source-file " + (!included ? "excluded" : "")} key={entry.id}><div className="source-file-copy"><BidiCode as="b">{entry.name}</BidiCode><small><span className="source-badge">Synology</span> <BidiCode>{entry.path}</BidiCode> · {formatSize(entry.size)} · {entry.content_type}{entry.category_source === "OWNER_OVERRIDE" ? " · Owner category" : " · Suggested category"}{!included ? " · Excluded from Proposal" : ""}</small><label className="source-category-select">Logical category<select value={itemCategory} disabled={operationBusy} onChange={(event) => setCategoryDrafts((current) => ({ ...current, [entry.id]: event.target.value as CategoryKey }))}>{CATEGORY_DEFS.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}</select></label></div><div className="source-file-actions"><button className="source-file-action" onClick={() => void saveCategory(entry)} disabled={!dirty || savingCategory[entry.id] || operationBusy}>{savingCategory[entry.id] ? "Saving…" : dirty ? "Save category" : "Saved"}</button><button className="source-file-action" onClick={() => void openFile(entry)} disabled={operationBusy}>View</button><button className="source-file-action" onClick={() => download(entry)} disabled={operationBusy}>Download</button><button className="source-file-action" onClick={() => void toggleIncluded(entry)} disabled={savingInclusion[entry.id] || operationBusy}>{savingInclusion[entry.id] ? "Saving…" : included ? "Remove from Proposal" : "Add back to Proposal"}</button></div></div>; }) : <p className="muted">No sources in this category.</p>}</div>
    </div>}
    <div className="source-add-row"><label>Owner source category<select value={sourceCategory} onChange={(event) => setSourceCategory(event.target.value as CategoryKey)} disabled={operationBusy}>{CATEGORY_DEFS.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}</select></label><input ref={fileInput} aria-label="Add source file" type="file" disabled={operationBusy} /><button type="button" className="button-secondary" onClick={addPendingSource} disabled={operationBusy}>＋ Add Source</button>{pendingSources.length > 0 && <span className="muted">{pendingSources.length} Owner source{pendingSources.length === 1 ? "" : "s"} staged</span>}</div>
    {preview && <div className="source-preview"><div className="panel-head"><h4>Source preview</h4><button className="button-secondary" onClick={() => setPreview("")}>Close</button></div><iframe title="Source file preview" src={preview} /></div>}
  </section>;
}
