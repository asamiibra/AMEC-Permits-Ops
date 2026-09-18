import { useEffect, useMemo, useState } from "react";
import { api, apiBlob } from "./api";

type EditorNode = { id: string; anchor: string; part: string; text: string; xml_hash: string; editable: boolean; block_type: string };
type EditorModel = { version: string; nodes: EditorNode[]; editable_node_count: number; read_only_node_count: number; read_only_block_types: string[]; [key: string]: any };
type ProposalSource = { link_id: string; filename: string; logical_category?: string; source_role: string; sha256: string; included_in_proposal?: boolean; view_route?: string; download_route?: string };
type RevisionData = { revision_number?: number; change_plan?: Record<string, any>; ai_provenance?: Record<string, any>; source_set_hash?: string };
type MutationEvidence = { mutation?: Record<string, any>; citations?: Array<Record<string, any>> };
type EditorMode = "DOCUMENT" | "AI_CHANGES" | "SOURCES" | "EDIT_TEXT";
const SOURCE_CATEGORIES = ["TENDER_DOCUMENTS", "PHOTOS_IMAGES", "EMAIL", "CLIENT_DATA", "CLIENT_DOCUMENTS", "PROJECT_INFORMATION", "OTHER_UNCLASSIFIED"];

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
  const [sources, setSources] = useState<ProposalSource[]>([]);
  const [sourceCategoryDrafts, setSourceCategoryDrafts] = useState<Record<string, string>>({});
  const [sourceState, setSourceState] = useState("");
  const [sourceManifestHash, setSourceManifestHash] = useState<string>();
  const [revisionData, setRevisionData] = useState<RevisionData | null>(null);
  const [mode, setMode] = useState<EditorMode>("DOCUMENT");
  const [mutationEvidence, setMutationEvidence] = useState<MutationEvidence | null>(null);
  const load = async () => {
    if (!file) return;
    setBusy(true); setStatus("");
    try {
      const form = new FormData(); form.append("file", file);
      const imported = await api<EditorModel>("/api/proposals-v1/editor/import", { method: "POST", headers: headers(role), body: form });
      setModel(imported); setNodes(imported.nodes); setChanges([]); setEvidenceRefs([]); setPreviewUrl(""); setMode("EDIT_TEXT"); setStatus("Imported by server. The anchored editor is ready.");
    } catch (error) { setStatus(error instanceof Error ? error.message : "DOCX import failed"); }
    finally { setBusy(false); }
  };
  useEffect(() => {
    if (!canonical || !proposalId) {
      return;
    }
    let cancelled = false;
    const loadCanonical = async () => {
      setBusy(true); setStatus("");
      try {
        // Use the shared API client for every canonical request. Relative
        // fetch() calls hit the web host in production and receive its HTML
        // shell, which is the source of the "Unexpected token '<'" error.
        let canonicalRevisionId = revisionOverride || revisionId || resolvedRevisionId;
        if (!canonicalRevisionId) {
          const entry = await api<any>(`/api/proposals-v1/editor/proposals/${proposalId}/entry`, { headers: headers(role) });
          if (!entry.revision_id) {
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
        setFile(canonicalFile); setModel(imported); setNodes(imported.nodes); setChanges([]); setRevisionData(revision); setEvidenceRefs(revision.ai_provenance?.evidence_refs || []); setMode("DOCUMENT");
        let renderNotice = "";
        try {
          const rendered = await apiBlob(`/api/proposals-v1/editor/proposals/${proposalId}/revisions/${canonicalRevisionId}/render`, { headers: headers(role) });
          if (!cancelled) setPreviewUrl(URL.createObjectURL(rendered));
        } catch (renderError) {
          renderNotice = renderError instanceof Error ? renderError.message : "The generated DOCX could not be rendered.";
        }
        setStatus(`Loaded canonical Proposal revision ${revision.revision_number}. Owner edits remain reviewable and revisioned.${renderNotice ? ` Render unavailable: ${renderNotice}` : ""}`);
      } catch (error) { if (!cancelled) setStatus(error instanceof Error ? error.message : "Canonical Proposal revision could not be loaded"); }
      finally { if (!cancelled) setBusy(false); }
    };
    void loadCanonical();
    return () => { cancelled = true; };
  }, [canonical, proposalId, revisionId, revisionOverride, resolvedRevisionId, role]);
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
  const saveSourceCategory = async (source: ProposalSource, logicalCategory: string) => {
    if (!proposalId || source.source_role === "BASELINE_TEMPLATE") return;
    try {
      const saved = await api<any>(`/api/proposals-v1/editor/proposals/${proposalId}/sources/${source.link_id}/category`, { method: "PATCH", headers: headers(role), body: JSON.stringify({ logical_category: logicalCategory }) });
      setSources((items) => items.map((item) => item.link_id === source.link_id ? { ...item, logical_category: logicalCategory } : item));
      setSourceCategoryDrafts((items) => ({ ...items, [source.link_id]: logicalCategory }));
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
    setBusy(true);
    try {
      const result = await api<any>(`/api/proposals/sources/proposals/${proposalId}/regenerate`, { method: "POST", headers: headers(role) });
      if (result.editor_revision_id) setRevisionOverride(result.editor_revision_id);
      setSourceState("READY_FOR_EDIT"); setStatus("Proposal regenerated from the current active source set.");
      await api<{ sources?: ProposalSource[]; generation_state?: string; source_manifest_hash?: string }>(`/api/proposals-v1/editor/proposals/${proposalId}/sources`, { headers: headers(role) }).then((next) => { const refreshed = next.sources || []; setSources(refreshed); setSourceCategoryDrafts(Object.fromEntries(refreshed.map((item) => [item.link_id, item.logical_category || "OTHER_UNCLASSIFIED"]))); setSourceState(next.generation_state || "READY_FOR_EDIT"); setSourceManifestHash(next.source_manifest_hash); });
    } catch (error) { setStatus(error instanceof Error ? error.message : "Proposal regeneration failed"); }
    finally { setBusy(false); }
  };
  const inspectChanges = async () => {
    if (!file || !model || !current) return;
    const form = new FormData(); form.append("file", file); form.append("imported_model", JSON.stringify(model)); form.append("current_model", JSON.stringify(current));
    try { const response = await api<any>("/api/proposals-v1/editor/changes", { method: "POST", headers: headers(role), body: form }); setChanges(response.changes || []); setStatus(`${response.mutation_count} anchored change(s) ready for review.`); }
    catch (error) { setStatus(error instanceof Error ? error.message : "Change review failed"); }
  };
  const saveCanonical = async (): Promise<any | null> => {
    if (!canonical || !proposalId || !activeRevisionId || !file || !model || !current) return null;
    setBusy(true);
    try {
      const form = new FormData(); form.append("file", file); form.append("imported_model", JSON.stringify(model)); form.append("current_model", JSON.stringify(current));
      form.append("change_plan", JSON.stringify({ mode: "OWNER_REVIEWED_EDIT", anchors: changes.map((change) => change.anchor) }));
      form.append("evidence_refs", JSON.stringify(evidenceRefs));
      const result = await api<any>(`/api/proposals-v1/editor/proposals/${proposalId}/revisions/${activeRevisionId}/save`, { method: "POST", headers: headers(role), body: form });
      setStatus(`Saved Proposal revision ${result.revision_id}; ${result.tracked_changes?.length || 0} anchored change(s) recorded.`);
      return result;
    } catch (error) { setStatus(error instanceof Error ? error.message : "Canonical Proposal revision could not be saved"); return null; }
    finally { setBusy(false); }
  };
  const exportDocx = async () => {
    if (!file || !model || !current) return;
    setBusy(true);
    try {
      if (canonical && proposalId && activeRevisionId) {
        setBusy(false);
        const saved = await saveCanonical();
        if (!saved) return;
        const blob = await apiBlob(`/api/proposals-v1/editor/proposals/${proposalId}/revisions/${activeRevisionId}/document`, { headers: headers(role) }); const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = "proposal-revised.docx"; link.click(); URL.revokeObjectURL(url);
        setStatus("Saved and downloaded the server-owned revised DOCX.");
        return;
      }
      const form = new FormData(); form.append("file", file); form.append("imported_model", JSON.stringify(model)); form.append("current_model", JSON.stringify(current));
      const blob = await apiBlob("/api/proposals-v1/editor/export", { method: "POST", headers: headers(role), body: form }); const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = "proposal-edited.docx"; link.click(); URL.revokeObjectURL(url); setStatus("Exported from the preserved original package using anchored mutations.");
    } catch (error) { setStatus(error instanceof Error ? error.message : "DOCX export failed"); }
    finally { setBusy(false); }
  };
  const truePreview = async () => {
    if (!file || !model || !current) return;
    const form = new FormData(); form.append("file", file); form.append("imported_model", JSON.stringify(model)); form.append("current_model", JSON.stringify(current));
    try { const url = URL.createObjectURL(await apiBlob("/api/proposals-v1/editor/preview", { method: "POST", headers: headers(role), body: form })); setPreviewUrl(url); setStatus("True render generated from the actual mutated DOCX package."); }
    catch (error) { setStatus(error instanceof Error ? error.message : "True render unavailable"); }
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
  const plan = revisionData?.change_plan || {};
  const provenance = revisionData?.ai_provenance || {};
  const mutations = Array.isArray(plan.mutations) ? plan.mutations : [];
  const renderSourcePanel = () => <aside className="proposal-editor-sources" aria-label="Active Proposal sources"><div className="proposal-editor-sources-head"><h4>Active Proposal sources</h4>{sourceState === "STALE_SOURCE_MANIFEST" && <span className="source-stale">Source changes available · regeneration required</span>}<button className="button-secondary" disabled={busy || sourceState !== "STALE_SOURCE_MANIFEST"} onClick={() => void regenerateProposal()}>Regenerate Proposal</button></div>{sources.length ? sources.map((source) => { const included = source.included_in_proposal !== false; const category = sourceCategoryDrafts[source.link_id] || source.logical_category || "OTHER_UNCLASSIFIED"; const baseline = source.source_role === "BASELINE_TEMPLATE"; return <div key={source.link_id} className={`proposal-source-row ${!included ? "source-excluded" : ""}`}><b>{source.filename}</b><small>{category} · {source.source_role}{!included ? " · Removed from Proposal" : ""}</small>{!baseline && <label>Category<select value={SOURCE_CATEGORIES.includes(category) ? category : "OTHER_UNCLASSIFIED"} onChange={(event) => setSourceCategoryDrafts((items) => ({ ...items, [source.link_id]: event.target.value }))}>{SOURCE_CATEGORIES.map((item) => <option key={item} value={item}>{item.replaceAll("_", " ")}</option>)}</select><button className="text-button" disabled={sourceCategoryDrafts[source.link_id] === source.logical_category} onClick={() => void saveSourceCategory(source, sourceCategoryDrafts[source.link_id] || category)}>Save category</button></label>}<span><button className="text-button" onClick={() => void openSource(source)}>View</button><button className="text-button" onClick={() => void openSource(source, true)}>Download</button>{!baseline && <button className="text-button" onClick={() => void toggleSourceInclusion(source)}>{included ? "Remove from Proposal" : "Add back to Proposal"}</button>}</span></div>; }) : <p className="muted">No active sources recorded.</p>}</aside>;
  return <section className="panel proposal-editor" aria-label="Proposal document editor">
    <div className="panel-head"><div><span className="eyebrow">PROPOSAL · DOCUMENT WORKSPACE</span><h3>{mode === "DOCUMENT" ? "Generated Proposal document" : mode === "AI_CHANGES" ? "AI Changes" : mode === "SOURCES" ? "Proposal sources" : "Anchored editing canvas"}</h3><p className="muted">Server-owned DOCX render · original OOXML package preserved on export</p></div>{onBack && <button className="text-button" onClick={onBack}>Back</button>}</div>
    <div className="proposal-editor-toolbar">{canonical ? <span className="muted">Canonical server revision · generated DOCX loaded and verified</span> : <><label>Open baseline DOCX<input type="file" accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document" onChange={(event) => setFile(event.target.files?.[0] || null)} /></label><button className="button-secondary" disabled={!file || busy} onClick={() => void load()}>Import</button></>}{model && <><button className="button-secondary" onClick={() => void inspectChanges()}>Review changes</button>{canonical && <button className="button-secondary" disabled={busy} onClick={() => void saveCanonical()}>Save revision</button>}<button className="button-primary" disabled={busy} onClick={() => void exportDocx()}>{canonical ? "Save & download DOCX" : "Export DOCX"}</button></>}</div>
    {status && <div className="inline-message" role="status">{status}</div>}
    {canonical && <><div className="proposal-editor-meta"><span>Revision <b>R{revisionData?.revision_number ?? "—"}</b></span><span>Generation <b>{String(provenance.generation_state || sourceState || "READY_FOR_EDIT").replaceAll("_", " ")}</b></span><span>Sources <b>{Array.isArray(provenance.evidence_refs) ? provenance.evidence_refs.length : sources.filter((source) => source.included_in_proposal !== false).length}</b></span><span>AI changes <b>{provenance.mutation_count ?? mutations.length}</b></span><span>Manifest <b>{sourceState === "STALE_SOURCE_MANIFEST" || (sourceManifestHash && revisionData?.source_set_hash && sourceManifestHash !== revisionData.source_set_hash) ? "stale" : "current"}</b></span>{sourceState === "STALE_SOURCE_MANIFEST" && <span className="source-stale">Source changes available</span>}</div><nav className="proposal-editor-modes" aria-label="Proposal V1 document modes">{([["DOCUMENT", "Document"], ["AI_CHANGES", "AI Changes"], ["SOURCES", "Sources"], ["EDIT_TEXT", "Edit Text"]] as Array<[EditorMode, string]>).map(([value, label]) => <button key={value} className={mode === value ? "active" : ""} onClick={() => setMode(value)}>{label}</button>)}</nav></>}
    {mode === "DOCUMENT" && <div className="proposal-document-view">{previewUrl ? <iframe className="proposal-editor-preview" title="Rendered generated proposal DOCX" src={previewUrl} /> : <p className="muted">The generated DOCX render is loading…</p>}</div>}
    {mode === "AI_CHANGES" && <section className="proposal-ai-changes" aria-label="AI changes"><h4>AI Changes</h4><p className="muted">Stored generation plan and citations from the canonical revision.</p>{mutations.length ? mutations.map((change: any) => <article className="proposal-editor-change" key={change.anchor}><b>{change.anchor}</b><small>{change.section || change.part || "Document section"}</small><del>{change.before || change.expected_text || "(no prior text recorded)"}</del><ins>{change.after || change.replacement || "(no replacement recorded)"}</ins><p>{change.reason || "Source-grounded Proposal change"}</p><button className="text-button" onClick={() => void showMutationSource(String(change.anchor))}>Show source</button></article>) : <div className="inline-message">{plan.status === "NO_AI_CHANGES_REQUIRED" ? "NO_AI_CHANGES_REQUIRED · validated existing Proposal has no source-backed document changes." : "GENERATION_REVIEW_REQUIRED · no document mutations were published for this revision."}</div>}{mutationEvidence && <div className="proposal-mutation-evidence"><h4>Source evidence</h4>{mutationEvidence.citations?.length ? mutationEvidence.citations.map((citation, index) => <div key={`${citation.citation_key || "citation"}-${index}`}><b>{citation.filename || "Source file"}</b><small>{citation.logical_category || "Unclassified"} · {citation.document_version_id || "version unavailable"}</small><p>{citation.locator?.excerpt || citation.locator?.text || citation.excerpt || citation.locator?.page || "Exact locator retained in the revision evidence."}</p>{(() => { const source = sources.find((item) => item.filename === citation.filename); return source ? <span><button className="text-button" onClick={() => void openSource(source)}>View</button><button className="text-button" onClick={() => void openSource(source, true)}>Download</button></span> : null; })()}</div>) : <p className="muted">No exact citation evidence was recorded.</p>}</div>}</section>}
    {mode === "SOURCES" && canonical && renderSourcePanel()}
    {mode === "EDIT_TEXT" && model && <div className="proposal-editor-grid"><div className="proposal-editor-canvas">{nodes.map((node, index) => <div key={node.id} className={`proposal-editor-node ${node.editable ? "editable" : "readonly"}`} data-anchor={node.anchor}><small>{node.editable ? "Editable text" : `Read-only ${node.block_type.toLowerCase().replaceAll("_", " ")}`} · {node.part}</small>{node.editable ? <div contentEditable suppressContentEditableWarning role="textbox" aria-label={`Editable paragraph ${index + 1}`} onInput={(event) => { const text = event.currentTarget.textContent || ""; setNodes((items) => items.map((item) => item.id === node.id ? { ...item, text } : item)); }}>{node.text}</div> : <div aria-label="Read-only document block">{node.text || "[layout / media block]"}</div>}</div>)}</div><aside className="proposal-editor-review"><h4>Owner edit review</h4>{changes.length ? changes.map((change) => <div className="proposal-editor-change" key={change.anchor}><del>{change.before}</del><ins>{change.after}</ins><small>{change.anchor}</small><div><button className="text-button" onClick={() => setNodes((items) => items.map((node) => node.id === change.anchor ? { ...node, text: change.before } : node))}>Reject</button><button className="text-button" onClick={() => setStatus("Change accepted; save revision to persist it.")}>Accept</button><button className="text-button" onClick={() => void showMutationSource(change.anchor)}>Show source</button></div></div>) : <p className="muted">Use Review changes after editing to inspect anchored Owner edits.</p>}</aside></div>}
    {mode === "SOURCES" && !canonical && model && <p className="muted">Sources are available after a Proposal V1 revision is created.</p>}
  </section>;
}
