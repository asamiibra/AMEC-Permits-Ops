import { useEffect, useMemo, useState } from "react";
import { api, apiBlob } from "./api";

type EditorNode = { id: string; anchor: string; part: string; text: string; xml_hash: string; editable: boolean; block_type: string };
type EditorModel = { version: string; nodes: EditorNode[]; editable_node_count: number; read_only_node_count: number; read_only_block_types: string[]; [key: string]: any };
type ProposalSource = { link_id: string; filename: string; logical_category?: string; source_role: string; sha256: string; view_route?: string; download_route?: string };

const headers = (role: string) => ({ "X-Dev-Role": role });

/** Option B canvas: the browser edits server-imported nodes, never a DOCX. */
export function ProposalDocumentEditor({ role = "OWNER_SPONSOR", proposalId, revisionId, onBack }: { role?: string; proposalId?: string; revisionId?: string; onBack?: () => void }) {
  const canonical = Boolean(proposalId);
  const [file, setFile] = useState<File | null>(null);
  const [model, setModel] = useState<EditorModel | null>(null);
  const [nodes, setNodes] = useState<EditorNode[]>([]);
  const [changes, setChanges] = useState<any[]>([]);
  const [evidenceRefs, setEvidenceRefs] = useState<string[]>([]);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [previewUrl, setPreviewUrl] = useState("");
  const [sources, setSources] = useState<ProposalSource[]>([]);
  const load = async () => {
    if (!file) return;
    setBusy(true); setStatus("");
    try {
      const form = new FormData(); form.append("file", file);
      const imported = await api<EditorModel>("/api/proposals-v1/editor/import", { method: "POST", headers: headers(role), body: form });
      setModel(imported); setNodes(imported.nodes); setChanges([]); setEvidenceRefs([]); setPreviewUrl(""); setStatus("Imported by server. The canvas is an editing view; true render is available before export.");
    } catch (error) { setStatus(error instanceof Error ? error.message : "DOCX import failed"); }
    finally { setBusy(false); }
  };
  useEffect(() => {
    if (!canonical || !proposalId || !revisionId) {
      if (canonical && !revisionId) setStatus("Resolving the canonical Proposal V1 revision…");
      return;
    }
    let cancelled = false;
    const loadCanonical = async () => {
      setBusy(true); setStatus("");
      try {
        // Use the shared API client for every canonical request. Relative
        // fetch() calls hit the web host in production and receive its HTML
        // shell, which is the source of the "Unexpected token '<'" error.
        const revision = await api<any>(`/api/proposals-v1/editor/proposals/${proposalId}/revisions/${revisionId}`, { headers: headers(role) });
        const documentBlob = await apiBlob(`/api/proposals-v1/editor/proposals/${proposalId}/revisions/${revisionId}/document`, { headers: headers(role) });
        const canonicalFile = new File([documentBlob], "proposal-revision.docx", { type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" });
        const form = new FormData(); form.append("file", canonicalFile);
        const imported = await api<EditorModel>("/api/proposals-v1/editor/import", { method: "POST", headers: headers(role), body: form });
        if (cancelled) return;
        setFile(canonicalFile); setModel(imported); setNodes(imported.nodes); setChanges([]); setEvidenceRefs(revision.ai_provenance?.evidence_refs || []); setPreviewUrl("");
        setStatus(`Loaded canonical Proposal revision ${revision.revision_number}. Owner edits remain reviewable and revisioned.`);
      } catch (error) { if (!cancelled) setStatus(error instanceof Error ? error.message : "Canonical Proposal revision could not be loaded"); }
      finally { if (!cancelled) setBusy(false); }
    };
    void loadCanonical();
    return () => { cancelled = true; };
  }, [canonical, proposalId, revisionId, role]);
  useEffect(() => {
    if (!canonical || !proposalId) return;
    let cancelled = false;
    api<{ sources?: ProposalSource[] }>(`/api/proposals-v1/editor/proposals/${proposalId}/sources`, { headers: headers(role) })
      .then((result) => { if (!cancelled) setSources(result.sources || []); })
      .catch(() => { if (!cancelled) setSources([]); });
    return () => { cancelled = true; };
  }, [canonical, proposalId, role]);
  const current = useMemo(() => model && ({ ...model, nodes }), [model, nodes]);
  const inspectChanges = async () => {
    if (!file || !model || !current) return;
    const form = new FormData(); form.append("file", file); form.append("imported_model", JSON.stringify(model)); form.append("current_model", JSON.stringify(current));
    try { const response = await api<any>("/api/proposals-v1/editor/changes", { method: "POST", headers: headers(role), body: form }); setChanges(response.changes || []); setStatus(`${response.mutation_count} anchored change(s) ready for review.`); }
    catch (error) { setStatus(error instanceof Error ? error.message : "Change review failed"); }
  };
  const saveCanonical = async (): Promise<any | null> => {
    if (!canonical || !proposalId || !revisionId || !file || !model || !current) return null;
    setBusy(true);
    try {
      const form = new FormData(); form.append("file", file); form.append("imported_model", JSON.stringify(model)); form.append("current_model", JSON.stringify(current));
      form.append("change_plan", JSON.stringify({ mode: "OWNER_REVIEWED_EDIT", anchors: changes.map((change) => change.anchor) }));
      form.append("evidence_refs", JSON.stringify(evidenceRefs));
      const result = await api<any>(`/api/proposals-v1/editor/proposals/${proposalId}/revisions/${revisionId}/save`, { method: "POST", headers: headers(role), body: form });
      setStatus(`Saved Proposal revision ${result.revision_id}; ${result.tracked_changes?.length || 0} anchored change(s) recorded.`);
      return result;
    } catch (error) { setStatus(error instanceof Error ? error.message : "Canonical Proposal revision could not be saved"); return null; }
    finally { setBusy(false); }
  };
  const exportDocx = async () => {
    if (!file || !model || !current) return;
    setBusy(true);
    try {
      if (canonical && proposalId && revisionId) {
        setBusy(false);
        const saved = await saveCanonical();
        if (!saved) return;
        const blob = await apiBlob(`/api/proposals-v1/editor/proposals/${proposalId}/revisions/${revisionId}/document`, { headers: headers(role) }); const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = "proposal-revised.docx"; link.click(); URL.revokeObjectURL(url);
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
  return <section className="panel proposal-editor" aria-label="Proposal document editor">
    <div className="panel-head"><div><span className="eyebrow">PROPOSAL · DOCUMENT WORKSPACE</span><h3>Anchored editing canvas</h3><p className="muted">Server-owned import · original OOXML package preserved on export</p></div>{onBack && <button className="text-button" onClick={onBack}>Back</button>}</div>
    <div className="proposal-editor-toolbar">{canonical ? <span className="muted">Canonical server revision · source DOCX loaded and verified</span> : <><label>Open baseline DOCX<input type="file" accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document" onChange={(event) => setFile(event.target.files?.[0] || null)} /></label><button className="button-secondary" disabled={!file || busy} onClick={() => void load()}>Import</button></>}{model && <><button className="button-secondary" onClick={() => void inspectChanges()}>Review changes</button><button className="button-secondary" onClick={() => void truePreview()}>Preview true render</button>{canonical && <button className="button-secondary" disabled={busy} onClick={() => void saveCanonical()}>Save revision</button>}<button className="button-primary" disabled={busy} onClick={() => void exportDocx()}>{canonical ? "Save & download DOCX" : "Export DOCX"}</button></>}</div>
    {status && <div className="inline-message" role="status">{status}</div>}
    {model && <div className="proposal-editor-meta"><span>Editable nodes: <b>{model.editable_node_count}</b></span><span>Read-only blocks: <b>{model.read_only_node_count}</b></span><span>Import: <b>server</b></span><span>Export: <b>preserved package</b></span></div>}
    {canonical && <aside className="proposal-editor-sources" aria-label="Active Proposal sources"><h4>Active Proposal sources</h4>{sources.length ? sources.map((source) => <div key={source.link_id}><b>{source.filename}</b><small>{source.logical_category || "Source"} · {source.source_role}</small><button className="text-button" onClick={() => void openSource(source)}>View</button><button className="text-button" onClick={() => void openSource(source, true)}>Download</button></div>) : <p className="muted">No active sources recorded.</p>}</aside>}
    {model && <div className="proposal-editor-grid"><div className="proposal-editor-canvas">{nodes.map((node, index) => <div key={node.id} className={`proposal-editor-node ${node.editable ? "editable" : "readonly"}`} data-anchor={node.anchor}><small>{node.editable ? "Editable text" : `Read-only ${node.block_type.toLowerCase().replaceAll("_", " ")}`} · {node.part}</small>{node.editable ? <div contentEditable suppressContentEditableWarning role="textbox" aria-label={`Editable paragraph ${index + 1}`} onInput={(event) => { const text = event.currentTarget.textContent || ""; setNodes((items) => items.map((item) => item.id === node.id ? { ...item, text } : item)); }}>{node.text}</div> : <div aria-label="Read-only document block">{node.text || "[layout / media block]"}</div>}</div>)}</div><aside className="proposal-editor-review"><h4>Change review</h4>{changes.length ? changes.map((change) => <div className="proposal-editor-change" key={change.anchor}><del>{change.before}</del><ins>{change.after}</ins><small>{change.anchor}</small><div><button className="text-button" onClick={() => setNodes((items) => items.map((node) => node.id === change.anchor ? { ...node, text: change.before } : node))}>Reject</button><button className="text-button" onClick={() => setStatus("Change accepted; export will apply this anchor.")}>Accept</button><button className="text-button" onClick={() => setStatus("Source evidence is shown from the Proposal provenance panel.")}>Show source</button></div></div>) : <p className="muted">No proposed changes. Owner edits appear here after Review changes.</p>}</aside></div>}
    {previewUrl && <iframe className="proposal-editor-preview" title="True rendered proposal preview" src={previewUrl} />}
  </section>;
}
