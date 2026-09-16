import { useMemo, useState } from "react";
import { api } from "./api";

type EditorNode = { id: string; anchor: string; part: string; text: string; xml_hash: string; editable: boolean; block_type: string };
type EditorModel = { version: string; nodes: EditorNode[]; editable_node_count: number; read_only_node_count: number; read_only_block_types: string[]; [key: string]: any };

const headers = (role: string) => ({ "X-Dev-Role": role });

/** Option B canvas: the browser edits server-imported nodes, never a DOCX. */
export function ProposalDocumentEditor({ role = "OWNER_SPONSOR", onBack }: { role?: string; onBack?: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [model, setModel] = useState<EditorModel | null>(null);
  const [nodes, setNodes] = useState<EditorNode[]>([]);
  const [changes, setChanges] = useState<any[]>([]);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [previewUrl, setPreviewUrl] = useState("");
  const load = async () => {
    if (!file) return;
    setBusy(true); setStatus("");
    try {
      const form = new FormData(); form.append("file", file);
      const imported = await api<EditorModel>("/api/proposals-v1/editor/import", { method: "POST", headers: headers(role), body: form });
      setModel(imported); setNodes(imported.nodes); setChanges([]); setPreviewUrl(""); setStatus("Imported by server. The canvas is an editing view; true render is available before export.");
    } catch (error) { setStatus(error instanceof Error ? error.message : "DOCX import failed"); }
    finally { setBusy(false); }
  };
  const current = useMemo(() => model && ({ ...model, nodes }), [model, nodes]);
  const inspectChanges = async () => {
    if (!file || !model || !current) return;
    const form = new FormData(); form.append("file", file); form.append("imported_model", JSON.stringify(model)); form.append("current_model", JSON.stringify(current));
    try { const response = await api<any>("/api/proposals-v1/editor/changes", { method: "POST", headers: headers(role), body: form }); setChanges(response.changes || []); setStatus(`${response.mutation_count} anchored change(s) ready for review.`); }
    catch (error) { setStatus(error instanceof Error ? error.message : "Change review failed"); }
  };
  const exportDocx = async () => {
    if (!file || !model || !current) return;
    setBusy(true);
    try {
      const form = new FormData(); form.append("file", file); form.append("imported_model", JSON.stringify(model)); form.append("current_model", JSON.stringify(current));
      const response = await fetch("/api/proposals-v1/editor/export", { method: "POST", headers: headers(role), body: form });
      if (!response.ok) throw new Error(await response.text());
      const blob = await response.blob(); const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = "proposal-edited.docx"; link.click(); URL.revokeObjectURL(url); setStatus("Exported from the preserved original package using anchored mutations.");
    } catch (error) { setStatus(error instanceof Error ? error.message : "DOCX export failed"); }
    finally { setBusy(false); }
  };
  const truePreview = async () => {
    if (!file || !model || !current) return;
    const form = new FormData(); form.append("file", file); form.append("imported_model", JSON.stringify(model)); form.append("current_model", JSON.stringify(current));
    try { const response = await fetch("/api/proposals-v1/editor/preview", { method: "POST", headers: headers(role), body: form }); if (!response.ok) throw new Error(await response.text()); const url = URL.createObjectURL(await response.blob()); setPreviewUrl(url); setStatus("True render generated from the actual mutated DOCX package."); }
    catch (error) { setStatus(error instanceof Error ? error.message : "True render unavailable"); }
  };
  return <section className="panel proposal-editor" aria-label="Proposal document editor">
    <div className="panel-head"><div><span className="eyebrow">PROPOSAL · DOCUMENT WORKSPACE</span><h3>Anchored editing canvas</h3><p className="muted">Server-owned import · original OOXML package preserved on export</p></div>{onBack && <button className="text-button" onClick={onBack}>Back</button>}</div>
    <div className="proposal-editor-toolbar"><label>Open baseline DOCX<input type="file" accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document" onChange={(event) => setFile(event.target.files?.[0] || null)} /></label><button className="button-secondary" disabled={!file || busy} onClick={() => void load()}>Import</button>{model && <><button className="button-secondary" onClick={() => void inspectChanges()}>Review changes</button><button className="button-secondary" onClick={() => void truePreview()}>Preview true render</button><button className="button-primary" onClick={() => void exportDocx()}>Export DOCX</button></>}</div>
    {status && <div className="inline-message" role="status">{status}</div>}
    {model && <div className="proposal-editor-meta"><span>Editable nodes: <b>{model.editable_node_count}</b></span><span>Read-only blocks: <b>{model.read_only_node_count}</b></span><span>Import: <b>server</b></span><span>Export: <b>preserved package</b></span></div>}
    {model && <div className="proposal-editor-grid"><div className="proposal-editor-canvas">{nodes.map((node, index) => <div key={node.id} className={`proposal-editor-node ${node.editable ? "editable" : "readonly"}`} data-anchor={node.anchor}><small>{node.editable ? "Editable text" : `Read-only ${node.block_type.toLowerCase().replaceAll("_", " ")}`} · {node.part}</small>{node.editable ? <div contentEditable suppressContentEditableWarning role="textbox" aria-label={`Editable paragraph ${index + 1}`} onInput={(event) => { const text = event.currentTarget.textContent || ""; setNodes((items) => items.map((item) => item.id === node.id ? { ...item, text } : item)); }}>{node.text}</div> : <div aria-label="Read-only document block">{node.text || "[layout / media block]"}</div>}</div>)}</div><aside className="proposal-editor-review"><h4>Change review</h4>{changes.length ? changes.map((change) => <div className="proposal-editor-change" key={change.anchor}><del>{change.before}</del><ins>{change.after}</ins><small>{change.anchor}</small><div><button className="text-button" onClick={() => setNodes((items) => items.map((node) => node.id === change.anchor ? { ...node, text: change.before } : node))}>Reject</button><button className="text-button" onClick={() => setStatus("Change accepted; export will apply this anchor.")}>Accept</button><button className="text-button" onClick={() => setStatus("Source evidence is shown from the Proposal provenance panel.")}>Show source</button></div></div>) : <p className="muted">No proposed changes. Owner edits appear here after Review changes.</p>}</aside></div>}
    {previewUrl && <iframe className="proposal-editor-preview" title="True rendered proposal preview" src={previewUrl} />}
  </section>;
}
