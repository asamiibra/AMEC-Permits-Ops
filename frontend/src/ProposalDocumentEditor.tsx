import { useEffect, useMemo, useState } from "react";
import { api, apiBlob } from "./api";

type EditorNode = { id: string; anchor: string; part: string; text: string; xml_hash: string; editable: boolean; block_type: string; heading_level?: number | null; heading_style?: string | null };
type EditorSection = { section_id: string; title: string; level: number; heading_anchor?: string | null; node_ids: string[] };
type EditorModel = { version: string; nodes: EditorNode[]; sections?: EditorSection[]; editable_node_count: number; read_only_node_count: number; read_only_block_types: string[]; [key: string]: any };
type ProposalSource = { link_id: string; filename: string; logical_category?: string; source_role: string; sha256: string; included_in_proposal?: boolean; view_route?: string; download_route?: string };
type RevisionData = { revision_number?: number; change_plan?: Record<string, any>; ai_provenance?: Record<string, any>; source_set_hash?: string };
type MutationEvidence = { mutation?: Record<string, any>; citations?: Array<Record<string, any>> };
type EditorMode = "DOCUMENT" | "EDIT_SECTIONS" | "AI_CHANGES" | "SOURCES";
type RenderState = "IDLE" | "RENDERING" | "RENDERED" | "ERROR";
type SaveState = "IDLE" | "SAVING" | "SAVED" | "ERROR";
type OperationState = "IDLE" | "RUNNING" | "DONE" | "ERROR";
const SOURCE_CATEGORIES = ["TENDER_DOCUMENTS", "PHOTOS_IMAGES", "EMAIL", "CLIENT_DATA", "CLIENT_DOCUMENTS", "PROJECT_INFORMATION", "OTHER_UNCLASSIFIED"];
const CATEGORY_LABELS: Record<string, string> = { TENDER_DOCUMENTS: "Tender Documents", PHOTOS_IMAGES: "Photos / Images", EMAIL: "Email", CLIENT_DATA: "Client Data", CLIENT_DOCUMENTS: "Client Documents", PROJECT_INFORMATION: "Project Information", OTHER_UNCLASSIFIED: "Other / Unclassified", BASELINE_TEMPLATE: "Proposal baseline" };
const categoryLabel = (category?: string) => CATEGORY_LABELS[category || "OTHER_UNCLASSIFIED"] || "Other / Unclassified";

const headers = (role: string) => ({ "X-Dev-Role": role });

/** Option B canvas: the browser edits server-imported nodes, never a DOCX. */
export function ProposalDocumentEditor({ role = "OWNER_SPONSOR", proposalId, revisionId, onBack }: { role?: string; proposalId?: string; revisionId?: string; onBack?: () => void }) {
  const canonical = Boolean(proposalId);
  const [resolvedRevisionId, setResolvedRevisionId] = useState(revisionId);
  const [revisionOverride, setRevisionOverride] = useState<string>();
  const [file, setFile] = useState<File | null>(null);
  const [model, setModel] = useState<EditorModel | null>(null);
  const [nodes, setNodes] = useState<EditorNode[]>([]);
  const [changes, setChanges] = useState<any[]>([]);
  const [evidenceRefs, setEvidenceRefs] = useState<string[]>([]);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [previewUrl, setPreviewUrl] = useState("");
  const [renderError, setRenderError] = useState("");
  const [renderState, setRenderState] = useState<RenderState>("IDLE");
  const [saveState, setSaveState] = useState<SaveState>("IDLE");
  const [downloadState, setDownloadState] = useState<OperationState>("IDLE");
  const [regenerateState, setRegenerateState] = useState<OperationState>("IDLE");
  const [sources, setSources] = useState<ProposalSource[]>([]);
  const [sourceCategoryDrafts, setSourceCategoryDrafts] = useState<Record<string, string>>({});
  const [sourceState, setSourceState] = useState("");
  const [sourceManifestHash, setSourceManifestHash] = useState<string>();
  const [sourceCategoryFilter, setSourceCategoryFilter] = useState("ALL");
  const [savedCategoryLinks, setSavedCategoryLinks] = useState<Record<string, boolean>>({});
  const [revisionData, setRevisionData] = useState<RevisionData | null>(null);
  const [mode, setMode] = useState<EditorMode>("DOCUMENT");
  const [mutationEvidence, setMutationEvidence] = useState<MutationEvidence | null>(null);
  const [showOwnerReview, setShowOwnerReview] = useState(false);
  const [selectedSectionId, setSelectedSectionId] = useState("document-body");
  const [pendingNavigation, setPendingNavigation] = useState<{ sectionId?: string; mode?: EditorMode; back?: boolean } | null>(null);
  const [reloadNonce, setReloadNonce] = useState(0);
  const load = async () => {
    if (!file) return;
    setBusy(true); setStatus("");
    try {
      const form = new FormData(); form.append("file", file);
      const imported = await api<EditorModel>("/api/proposals-v1/editor/import", { method: "POST", headers: headers(role), body: form });
      setModel(imported); setNodes(imported.nodes); setChanges([]); setEvidenceRefs([]); setPreviewUrl(""); setMode("EDIT_SECTIONS"); setSelectedSectionId(imported.sections?.[0]?.section_id || "document-body"); setStatus("Imported by server. Select a section to edit.");
    } catch (error) { setStatus(error instanceof Error ? error.message : "DOCX import failed"); }
    finally { setBusy(false); }
  };
  useEffect(() => {
    if (!canonical || !proposalId) {
      return;
    }
    let cancelled = false;
    const loadCanonical = async () => {
      setBusy(true); setStatus(""); setRenderState("RENDERING"); setRenderError(""); setPreviewUrl("");
      try {
        // Use the shared API client for every canonical request. Relative
        // fetch() calls hit the web host in production and receive its HTML
        // shell, which is the source of the "Unexpected token '<'" error.
        let canonicalRevisionId = revisionOverride || revisionId || resolvedRevisionId;
        if (!canonicalRevisionId) {
          const entry = await api<any>(`/api/proposals-v1/editor/proposals/${proposalId}/entry`, { headers: headers(role) });
          if (!entry.revision_id) {
            setRenderState("IDLE");
            setStatus(entry.generation_state === "FAILED_RETRYABLE" ? "Generation failed. Retry is available from the Proposal workspace." : `Proposal generation state: ${entry.generation_state || "PENDING"}.`);
            return;
          }
          canonicalRevisionId = entry.revision_id;
          setResolvedRevisionId(canonicalRevisionId);
          setRevisionOverride(canonicalRevisionId);
        }
        const revision = await api<any>(`/api/proposals-v1/editor/proposals/${proposalId}/revisions/${canonicalRevisionId}`, { headers: headers(role) });
        const documentBlob = await apiBlob(`/api/proposals-v1/editor/proposals/${proposalId}/revisions/${canonicalRevisionId}/document`, { headers: headers(role) });
        const canonicalFile = new File([documentBlob], "proposal-revision.docx", { type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" });
        const form = new FormData(); form.append("file", canonicalFile);
        const imported = await api<EditorModel>("/api/proposals-v1/editor/import", { method: "POST", headers: headers(role), body: form });
        if (cancelled) return;
        setFile(canonicalFile); setModel(imported); setNodes(imported.nodes); setChanges([]); setShowOwnerReview(false); setRevisionData(revision); setEvidenceRefs(revision.ai_provenance?.evidence_refs || []); setMode("DOCUMENT"); setSelectedSectionId(imported.sections?.[0]?.section_id || "document-body"); setRenderError("");
        let renderNotice = "";
        try {
          const rendered = await apiBlob(`/api/proposals-v1/editor/proposals/${proposalId}/revisions/${canonicalRevisionId}/render`, { headers: headers(role) });
          if (!cancelled) { setPreviewUrl(URL.createObjectURL(rendered)); setRenderError(""); setRenderState("RENDERED"); }
        } catch (renderError) {
          renderNotice = renderError instanceof Error ? renderError.message : "The generated DOCX could not be rendered.";
          if (!cancelled) { setPreviewUrl(""); setRenderError(renderNotice); setRenderState("ERROR"); }
        }
        setStatus(`Loaded canonical Proposal revision ${revision.revision_number}. Owner edits remain reviewable and revisioned.${renderNotice ? ` Render unavailable: ${renderNotice}` : ""}`);
      } catch (error) {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : "Canonical Proposal revision could not be loaded";
          setRenderError(message); setRenderState("ERROR"); setStatus(message);
        }
      }
      finally { if (!cancelled) setBusy(false); }
    };
    void loadCanonical();
    return () => { cancelled = true; };
  }, [canonical, proposalId, revisionId, revisionOverride, resolvedRevisionId, role, reloadNonce]);
  useEffect(() => {
    if (!canonical || !proposalId) return;
    let cancelled = false;
    api<{ sources?: ProposalSource[]; generation_state?: string; source_manifest_hash?: string }>(`/api/proposals-v1/editor/proposals/${proposalId}/sources`, { headers: headers(role) })
      .then((result) => { if (!cancelled) { const next = result.sources || []; setSources(next); setSourceCategoryDrafts(Object.fromEntries(next.map((item) => [item.link_id, item.logical_category || "OTHER_UNCLASSIFIED"]))); setSourceState(result.generation_state || ""); setSourceManifestHash(result.source_manifest_hash); } })
      .catch(() => { if (!cancelled) setSources([]); });
    return () => { cancelled = true; };
  }, [canonical, proposalId, role]);
  const current = useMemo(() => model && ({ ...model, nodes }), [model, nodes]);
  const activeRevisionId = revisionOverride || revisionId || resolvedRevisionId;
  const plan = revisionData?.change_plan || {};
  const provenance = revisionData?.ai_provenance || {};
  const mutations = Array.isArray(plan.mutations) ? plan.mutations : [];
  const sections = model?.sections?.length ? model.sections : [{ section_id: "document-body", title: "Document body", level: 0, heading_anchor: null, node_ids: nodes.filter((node) => node.part === "word/document.xml").map((node) => node.id) }];
  const selectedSection = (sections.find((section) => section.section_id === selectedSectionId) || sections[0])!;
  const selectedNodeIds = new Set(selectedSection?.node_ids || []);
  const selectedNodes = nodes.filter((node) => selectedNodeIds.has(node.id));
  const importedNodes = new Map((model?.nodes || []).map((node) => [node.id, node]));
  const sectionDirty = selectedNodes.some((node) => importedNodes.get(node.id)?.text !== node.text);
  const groupedMutations = sections.map((section) => {
    const sectionNodeIds = new Set(section.node_ids.map(String));
    const sectionAnchors = new Set(nodes.filter((node) => sectionNodeIds.has(node.id)).map((node) => node.anchor));
    return { section, mutations: mutations.filter((mutation: any) => sectionNodeIds.has(String(mutation.anchor)) || sectionAnchors.has(String(mutation.anchor))) };
  }).filter((group) => group.mutations.length);
  const groupedMutationAnchors = new Set(groupedMutations.flatMap((group) => group.mutations.map((mutation: any) => String(mutation.anchor))));
  const ungroupedMutations = mutations.filter((mutation: any) => !groupedMutationAnchors.has(String(mutation.anchor)));
  if (ungroupedMutations.length) groupedMutations.push({ section: { section_id: "document-body", title: "Document body", level: 0, heading_anchor: null, node_ids: [] }, mutations: ungroupedMutations });
  const applyNavigation = (navigation: { sectionId?: string; mode?: EditorMode; back?: boolean }) => {
    if (navigation.sectionId) setSelectedSectionId(navigation.sectionId);
    if (navigation.mode) setMode(navigation.mode);
    if (navigation.back) onBack?.();
  };
  const requestNavigation = (navigation: { sectionId?: string; mode?: EditorMode; back?: boolean }) => {
    if (sectionDirty) setPendingNavigation(navigation);
    else applyNavigation(navigation);
  };
  const requestSection = (sectionId: string) => { if (sectionId === selectedSection?.section_id) return; requestNavigation({ sectionId }); };
  const saveSourceCategory = async (source: ProposalSource, logicalCategory: string) => {
    if (!proposalId || source.source_role === "BASELINE_TEMPLATE") return;
    try {
      const saved = await api<any>(`/api/proposals-v1/editor/proposals/${proposalId}/sources/${source.link_id}/category`, { method: "PATCH", headers: headers(role), body: JSON.stringify({ logical_category: logicalCategory }) });
      setSources((items) => items.map((item) => item.link_id === source.link_id ? { ...item, logical_category: saved.logical_category || logicalCategory } : item));
      setSourceCategoryDrafts((items) => ({ ...items, [source.link_id]: logicalCategory }));
      setSavedCategoryLinks((items) => ({ ...items, [source.link_id]: true }));
      setSourceState(saved.generation_state || "STALE_SOURCE_MANIFEST"); setStatus(`Saved category ${saved.logical_category || logicalCategory}. Regenerate the Proposal to apply it.`);
    } catch (error) { setStatus(error instanceof Error ? error.message : "Source category could not be saved"); }
  };
  const toggleSourceInclusion = async (source: ProposalSource) => {
    if (!proposalId || source.source_role === "BASELINE_TEMPLATE") return;
    try {
      const included = !(source.included_in_proposal !== false);
      await api(`/api/proposals-v1/editor/proposals/${proposalId}/sources/${source.link_id}/inclusion`, { method: "PATCH", headers: headers(role), body: JSON.stringify({ included_in_proposal: included }) });
      setSources((items) => items.map((item) => item.link_id === source.link_id ? { ...item, included_in_proposal: included } : item));
      setSourceState("STALE_SOURCE_MANIFEST"); setStatus(`Source ${included ? "added back to" : "removed from"} the Proposal. Regenerate to apply it.`);
    } catch (error) { setStatus(error instanceof Error ? error.message : "Source inclusion could not be saved"); }
  };
  const regenerateProposal = async () => {
    if (!proposalId) return;
    setBusy(true); setRegenerateState("RUNNING"); setStatus("Regenerating Proposal…");
    try {
      const result = await api<any>(`/api/proposals/sources/proposals/${proposalId}/regenerate`, { method: "POST", headers: headers(role) });
      if (result.editor_revision_id) setRevisionOverride(result.editor_revision_id);
      setSourceState("READY_FOR_EDIT"); setRegenerateState("DONE"); setStatus("Proposal regenerated from the current active source set.");
      await api<{ sources?: ProposalSource[]; generation_state?: string; source_manifest_hash?: string }>(`/api/proposals-v1/editor/proposals/${proposalId}/sources`, { headers: headers(role) }).then((next) => { const refreshed = next.sources || []; setSources(refreshed); setSourceCategoryDrafts(Object.fromEntries(refreshed.map((item) => [item.link_id, item.logical_category || "OTHER_UNCLASSIFIED"]))); setSourceState(next.generation_state || "READY_FOR_EDIT"); setSourceManifestHash(next.source_manifest_hash); });
    } catch (error) { setRegenerateState("ERROR"); setStatus(error instanceof Error ? error.message : "Proposal regeneration failed"); }
    finally { setBusy(false); }
  };
  const reviewOwnerEdits = async () => {
    if (!file || !model || !current) return;
    setBusy(true); setShowOwnerReview(true); setStatus("Reviewing my edits…");
    const form = new FormData(); form.append("file", file); form.append("imported_model", JSON.stringify(model)); form.append("current_model", JSON.stringify(current));
    try {
      const response = await api<any>("/api/proposals-v1/editor/changes", { method: "POST", headers: headers(role), body: form });
      const sectionAnchors = new Set(selectedNodes.map((node) => node.anchor));
      const ownerChanges = (response.changes || []).filter((change: any) => sectionAnchors.has(String(change.anchor)));
      setChanges(ownerChanges); setStatus(ownerChanges.length ? `${ownerChanges.length} unsaved change(s) in this section.` : "No unsaved changes in this section.");
    } catch (error) { setStatus(error instanceof Error ? error.message : "Owner edit review failed"); }
    finally { setBusy(false); }
  };
  const saveCanonical = async (): Promise<any | null> => {
    if (!canonical || !proposalId || !activeRevisionId || !file || !model || !current) return null;
    setBusy(true); setSaveState("SAVING"); setStatus("Saving…");
    try {
      const form = new FormData(); form.append("file", file); form.append("imported_model", JSON.stringify(model)); form.append("current_model", JSON.stringify(current));
      form.append("change_plan", JSON.stringify({ mode: "OWNER_REVIEWED_EDIT", anchors: changes.map((change) => change.anchor) }));
      form.append("evidence_refs", JSON.stringify(evidenceRefs));
      const result = await api<any>(`/api/proposals-v1/editor/proposals/${proposalId}/revisions/${activeRevisionId}/save`, { method: "POST", headers: headers(role), body: form });
      setStatus(`Saved Proposal revision ${result.revision_id}; ${result.tracked_changes?.length || 0} anchored change(s) recorded.`);
      setSaveState("SAVED"); setChanges([]); setShowOwnerReview(false);
      if (result.revision_id) setRevisionOverride(result.revision_id);
      else setReloadNonce((value) => value + 1);
      return result;
    } catch (error) { setSaveState("ERROR"); setStatus(error instanceof Error ? error.message : "Canonical Proposal revision could not be saved"); return null; }
    finally { setBusy(false); }
  };
  const saveSection = async () => { if (!sectionDirty) { setStatus("Section is already saved."); return true; } return saveCanonical(); };
  const retryRender = async () => {
    if (!proposalId || !activeRevisionId) return;
    setBusy(true); setRenderState("RENDERING"); setRenderError(""); setStatus("Rendering document…");
    try {
      const rendered = await apiBlob(`/api/proposals-v1/editor/proposals/${proposalId}/revisions/${activeRevisionId}/render`, { headers: headers(role) });
      setPreviewUrl(URL.createObjectURL(rendered)); setRenderError(""); setRenderState("RENDERED"); setStatus("Document preview loaded.");
    } catch (error) {
      const message = error instanceof Error ? error.message : "The generated DOCX could not be rendered.";
      setRenderError(message); setRenderState("ERROR"); setStatus(`Document preview unavailable: ${message}`);
    } finally { setBusy(false); }
  };
  const discardSection = () => { if (model) setNodes(model.nodes); const navigation = pendingNavigation; setPendingNavigation(null); setStatus("Unsaved section changes discarded."); if (navigation) applyNavigation(navigation); };
  const savePendingNavigation = async () => {
    const navigation = pendingNavigation;
    const saved = await saveSection();
    if (saved !== null) {
      setPendingNavigation(null);
      if (navigation) applyNavigation(navigation);
    }
  };
  const downloadDocx = async () => {
    if (!file || !model || !current) return;
    setBusy(true); setDownloadState("RUNNING"); setStatus("Preparing DOCX…");
    try {
      if (canonical && proposalId && activeRevisionId) {
        const blob = await apiBlob(`/api/proposals-v1/editor/proposals/${proposalId}/revisions/${activeRevisionId}/document`, { headers: headers(role) }); const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = "proposal-revised.docx"; link.click(); URL.revokeObjectURL(url);
        setDownloadState("DONE"); setStatus("DOCX downloaded.");
        return;
      }
      const form = new FormData(); form.append("file", file); form.append("imported_model", JSON.stringify(model)); form.append("current_model", JSON.stringify(current));
      const blob = await apiBlob("/api/proposals-v1/editor/export", { method: "POST", headers: headers(role), body: form }); const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = "proposal-edited.docx"; link.click(); URL.revokeObjectURL(url); setDownloadState("DONE"); setStatus("DOCX downloaded from the preserved original package.");
    } catch (error) { setDownloadState("ERROR"); setStatus(error instanceof Error ? error.message : "DOCX download failed"); }
    finally { setBusy(false); }
  };
  const revertOwnerChange = (change: any) => {
    setNodes((items) => items.map((node) => node.anchor === String(change.anchor) ? { ...node, text: String(change.before || "") } : node));
    setChanges((items) => items.filter((item) => String(item.anchor) !== String(change.anchor)));
    setStatus("Reverted this Owner edit. Save section to persist the revision.");
  };
  const keepOwnerChange = (anchor: string) => {
    setChanges((items) => items.map((item) => String(item.anchor) === anchor ? { ...item, review_state: "KEPT" } : item));
    setStatus("Kept this Owner edit in the working section. Save section to persist it.");
  };
  const openSource = async (source: ProposalSource, download = false) => {
    const route = download ? source.download_route : source.view_route;
    if (!route) return;
    try {
      const blob = await apiBlob(route, { headers: headers(role) });
      const url = URL.createObjectURL(blob);
      if (download) { const link = document.createElement("a"); link.href = url; link.download = source.filename; link.click(); }
      else window.open(url, "_blank", "noopener,noreferrer");
      window.setTimeout(() => URL.revokeObjectURL(url), 30_000);
    } catch (error) { setStatus(error instanceof Error ? error.message : "Source could not be opened"); }
  };
  const showMutationSource = async (anchor: string) => {
    if (!proposalId || !activeRevisionId) return;
    try {
      const evidence = await api<any>(`/api/proposals-v1/editor/proposals/${proposalId}/revisions/${activeRevisionId}/mutations/${encodeURIComponent(anchor)}/evidence`, { headers: headers(role) });
      setMutationEvidence(evidence); setMode("AI_CHANGES"); setStatus(evidence.citations?.length ? "Exact source evidence loaded." : "No exact citation evidence was recorded for this change.");
    } catch (error) { setStatus(error instanceof Error ? error.message : "Source evidence could not be opened"); }
  };
  const renderNode = (node: EditorNode, index: number) => <div key={node.id} className={`proposal-editor-node ${node.editable ? "editable" : "readonly"}`} data-anchor={node.anchor}><small>{node.editable ? "Editable text" : node.block_type === "COMPLEX_PARAGRAPH" ? "[Table / complex content — preserved in document]" : node.block_type === "DRAWING" || node.block_type === "EMBEDDED_MEDIA" || node.block_type === "VML_TEXTBOX" ? "[Image / media — preserved in document]" : "Protected document content"}</small>{node.editable ? <div contentEditable suppressContentEditableWarning role="textbox" aria-label={`Editable paragraph ${index + 1}`} onInput={(event) => { const text = event.currentTarget.textContent || ""; setSaveState("IDLE"); setShowOwnerReview(false); setNodes((items) => items.map((item) => item.id === node.id ? { ...item, text } : item)); }}>{node.text}</div> : <div aria-label="Preserved document block">{node.text || "[Complex content preserved in document]"}</div>}</div>;
  const sourceCounts = ["ALL", ...SOURCE_CATEGORIES].map((category) => [category, category === "ALL" ? sources.length : sources.filter((source) => (source.logical_category || "OTHER_UNCLASSIFIED") === category).length] as const);
  const visibleSources = sourceCategoryFilter === "ALL" ? sources : sources.filter((source) => (source.logical_category || "OTHER_UNCLASSIFIED") === sourceCategoryFilter);
  const renderSourcePanel = () => <aside className="proposal-editor-sources" aria-label="Active Proposal sources"><div className="proposal-source-summary">{sourceCounts.map(([category, count]) => <button key={category} type="button" className={sourceCategoryFilter === category ? "active" : ""} onClick={() => setSourceCategoryFilter(category)}><b>{count}</b> {category === "ALL" ? "All" : categoryLabel(category)}</button>)}</div><div className="proposal-editor-sources-head"><h4>Active Proposal sources</h4>{sourceState === "STALE_SOURCE_MANIFEST" && <span className="source-stale">Source changes available · regeneration required</span>}{regenerateState === "RUNNING" && <span className="document-operation-state">Regenerating…</span>}{regenerateState === "DONE" && <span className="document-operation-state">Regenerated ✓</span>}<button className="button-secondary" disabled={busy || sourceState !== "STALE_SOURCE_MANIFEST"} onClick={() => void regenerateProposal()}>{regenerateState === "RUNNING" ? "Regenerating…" : "Regenerate Proposal"}</button></div>{visibleSources.length ? visibleSources.map((source) => { const included = source.included_in_proposal !== false; const category = sourceCategoryDrafts[source.link_id] || source.logical_category || "OTHER_UNCLASSIFIED"; const baseline = source.source_role === "BASELINE_TEMPLATE"; return <div key={source.link_id} className={`proposal-source-row ${!included ? "source-excluded" : ""}`}><b>{source.filename}</b><small>{categoryLabel(category)}{!included ? " · Excluded" : " · Included"}</small>{!baseline && <label>Category<select aria-label={`Category for ${source.filename}`} value={SOURCE_CATEGORIES.includes(category) ? category : "OTHER_UNCLASSIFIED"} onChange={(event) => { setSavedCategoryLinks((items) => ({ ...items, [source.link_id]: false })); setSourceCategoryDrafts((items) => ({ ...items, [source.link_id]: event.target.value })); }}>{SOURCE_CATEGORIES.map((item) => <option key={item} value={item}>{categoryLabel(item)}</option>)}</select><button className="text-button" disabled={sourceCategoryDrafts[source.link_id] === source.logical_category} onClick={() => void saveSourceCategory(source, sourceCategoryDrafts[source.link_id] || category)}>{savedCategoryLinks[source.link_id] ? "Saved ✓" : "Save category"}</button></label>}<span><button className="text-button" onClick={() => void openSource(source)}>View</button><button className="text-button" onClick={() => void openSource(source, true)}>Download</button>{!baseline && <button className="text-button" onClick={() => void toggleSourceInclusion(source)}>{included ? "Remove from Proposal" : "Add back to Proposal"}</button>}</span></div>; }) : <p className="muted">No sources in this category.</p>}</aside>;
  return <section className="panel proposal-editor" aria-label="Proposal document editor">
    <div className="panel-head"><div><span className="eyebrow">PROPOSAL · DOCUMENT WORKSPACE</span><h3>{mode === "DOCUMENT" ? "Proposal Document" : mode === "AI_CHANGES" ? "AI Changes" : mode === "SOURCES" ? "Proposal sources" : "Edit Proposal sections"}</h3><p className="muted">Server-owned DOCX render · original OOXML package preserved on export</p></div>{onBack && <button className="text-button" onClick={() => requestNavigation({ back: true })}>Back</button>}</div>
    <div className="proposal-editor-toolbar">{canonical ? <span className="muted">Canonical server revision · generated DOCX loaded and verified</span> : <><label>Open baseline DOCX<input type="file" accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document" onChange={(event) => setFile(event.target.files?.[0] || null)} /></label><button className="button-secondary" disabled={!file || busy} onClick={() => void load()}>Import</button></>}{model && canonical && mode === "DOCUMENT" && <><button className="button-secondary" disabled={busy} onClick={() => void retryRender()}>{renderState === "RENDERING" ? "Rendering…" : "Refresh render"}</button><button className="button-primary" disabled={busy} onClick={() => void downloadDocx()}>{downloadState === "RUNNING" ? "Preparing DOCX…" : downloadState === "DONE" ? "Downloaded ✓" : "Download DOCX"}</button></>}{model && canonical && mode === "EDIT_SECTIONS" && <><button className="button-secondary" disabled={busy} onClick={() => void reviewOwnerEdits()}>Review my edits</button><button className="button-primary" disabled={busy || !sectionDirty} onClick={() => void saveSection()}>{saveState === "SAVING" ? "Saving…" : saveState === "SAVED" ? "Saved ✓" : "Save section"}</button></>}</div>
    {status && <div className="inline-message" role="status">{status}</div>}
    {canonical && <><div className="proposal-editor-meta"><span>Revision <b>R{revisionData?.revision_number ?? "—"}</b></span><span>Generation <b>{String(provenance.generation_state || sourceState || "READY_FOR_EDIT").replaceAll("_", " ")}</b></span><span>Sources <b>{Array.isArray(provenance.evidence_refs) ? provenance.evidence_refs.length : sources.filter((source) => source.included_in_proposal !== false).length}</b></span><span>AI changes <b>{provenance.mutation_count ?? mutations.length}</b></span><span>Manifest <b>{sourceState === "STALE_SOURCE_MANIFEST" || (sourceManifestHash && revisionData?.source_set_hash && sourceManifestHash !== revisionData.source_set_hash) ? "stale" : "current"}</b></span>{sourceState === "STALE_SOURCE_MANIFEST" && <span className="source-stale">Source changes available</span>}</div><nav className="proposal-editor-modes" aria-label="Proposal V1 document modes">{([["DOCUMENT", "Document"], ["EDIT_SECTIONS", "Edit Sections"], ["AI_CHANGES", "AI Changes"], ["SOURCES", "Sources"]] as Array<[EditorMode, string]>).map(([value, label]) => <button key={value} className={mode === value ? "active" : ""} onClick={() => requestNavigation({ mode: value })}>{label}</button>)}</nav></>}
    {mode === "DOCUMENT" && <div className="proposal-document-view">{renderState === "RENDERING" && <div className="inline-message" role="status">Rendering document…</div>}{renderState === "RENDERED" && previewUrl && <><div className="document-operation-state">Rendered ✓</div><iframe className="proposal-editor-preview" title="Rendered generated proposal DOCX" src={previewUrl} /></>}{renderState === "ERROR" && <div className="inline-message" role="alert"><b>Document preview unavailable</b><p>{renderError}</p><button className="button-secondary" disabled={busy} onClick={() => void retryRender()}>Retry</button><button className="button-primary" disabled={busy} onClick={() => void downloadDocx()}>Download DOCX</button></div>}</div>}
    {mode === "EDIT_SECTIONS" && model && <div className="proposal-sections-layout"><nav className="proposal-section-nav" aria-label="Proposal sections">{sections.map((section) => <button key={section.section_id} className={selectedSection?.section_id === section.section_id ? "active" : ""} onClick={() => requestSection(section.section_id)}>{section.title}<small>{section.node_ids.length} block{section.node_ids.length === 1 ? "" : "s"}</small></button>)}</nav><section className="proposal-section-editor"><div className="proposal-section-heading"><div><span className="eyebrow">SECTION {selectedSection?.level || ""}</span><h4>{selectedSection?.title || "Document body"}</h4></div><span className="muted">{sectionDirty ? "Unsaved changes" : "Saved ✓"}</span></div><div className="proposal-editor-canvas">{selectedNodes.map(renderNode)}</div>{showOwnerReview && <aside className="proposal-owner-review" aria-label="My edits"><h4>Review my edits</h4>{changes.length ? changes.map((change: any) => <article className="proposal-editor-change" key={change.anchor}><del>{change.before || "(empty)"}</del><ins>{change.after || "(empty)"}</ins>{change.review_state === "KEPT" ? <span className="document-operation-state">Kept</span> : <div><button className="text-button" onClick={() => keepOwnerChange(String(change.anchor))}>Keep change</button><button className="text-button" onClick={() => revertOwnerChange(change)}>Revert</button></div>}</article>) : <p className="muted">No unsaved changes in this section.</p>}</aside>}<div className="proposal-section-actions"><button className="button-secondary" disabled={!selectedSection || sections.findIndex((section) => section.section_id === selectedSection.section_id) <= 0} onClick={() => { const index = sections.findIndex((section) => section.section_id === selectedSection.section_id); if (index > 0) requestSection(sections[index - 1].section_id); }}>Previous section</button><button className="button-secondary" disabled={!selectedSection || sections.findIndex((section) => section.section_id === selectedSection.section_id) >= sections.length - 1} onClick={() => { const index = sections.findIndex((section) => section.section_id === selectedSection.section_id); if (index < sections.length - 1) requestSection(sections[index + 1].section_id); }}>Next section</button></div></section></div>}
    {mode === "AI_CHANGES" && <section className="proposal-ai-changes" aria-label="AI changes"><h4>AI Changes</h4><p className="muted">Stored generation plan and citations from the canonical revision.</p>{mutations.length ? groupedMutations.map(({ section, mutations: sectionMutations }) => <section key={section.section_id} className="proposal-ai-section"><h5>{section.title} <small>{sectionMutations.length} AI change{sectionMutations.length === 1 ? "" : "s"}</small></h5>{sectionMutations.map((change: any) => <article className="proposal-editor-change" key={change.anchor}><b>{change.anchor}</b><del>{change.before || change.expected_text || "(no prior text recorded)"}</del><ins>{change.after || change.replacement || "(no replacement recorded)"}</ins><p>{change.reason || "Source-grounded Proposal change"}</p><button className="text-button" onClick={() => void showMutationSource(String(change.anchor))}>Show source</button></article>)}</section>) : <div className="inline-message">{plan.status === "NO_AI_CHANGES_REQUIRED" ? "NO_AI_CHANGES_REQUIRED · validated existing Proposal has no source-backed document changes." : "GENERATION_REVIEW_REQUIRED · no document mutations were published for this revision."}</div>}{mutationEvidence && <div className="proposal-mutation-evidence"><h4>Source evidence</h4>{mutationEvidence.citations?.length ? mutationEvidence.citations.map((citation, index) => <div key={`${citation.citation_key || "citation"}-${index}`}><b>{citation.filename || "Source file"}</b><small>{categoryLabel(citation.logical_category)} · {citation.document_version_id || "version unavailable"}</small><p>{citation.locator?.excerpt || citation.locator?.text || citation.excerpt || citation.locator?.page || "Exact locator retained in the revision evidence."}</p>{(() => { const source = sources.find((item) => item.filename === citation.filename); return source ? <span><button className="text-button" onClick={() => void openSource(source)}>View</button><button className="text-button" onClick={() => void openSource(source, true)}>Download</button></span> : null; })()}</div>) : <p className="muted">No exact citation evidence was recorded.</p>}</div>}</section>}
    {mode === "SOURCES" && canonical && renderSourcePanel()}
    {pendingNavigation && <div className="proposal-section-guard" role="dialog" aria-label="Save section changes"><h4>Save changes to this section?</h4><p>Your edits are not saved yet.</p><div><button className="button-primary" onClick={() => void savePendingNavigation()}>Save</button><button className="button-secondary" onClick={discardSection}>Discard</button><button className="text-button" onClick={() => setPendingNavigation(null)}>Cancel</button></div></div>}
    {mode === "SOURCES" && !canonical && model && <p className="muted">Sources are available after a Proposal V1 revision is created.</p>}
  </section>;
}
