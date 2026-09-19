import { useEffect, useMemo, useState } from "react";
import { NewProposalPage } from "./NewProposalPage";
import { ProposalRegisterPage } from "./ProposalRegisterPage";
import { ProposalWorkspacePage } from "./ProposalWorkspacePage";
import { ProposalSourceWorkspace } from "../../ProposalSourceWorkspace";
import { ProposalDocumentEditor } from "../../ProposalDocumentEditor";
import { api } from "../../api";
import type { ProposalRole } from "./types";
import "./proposal.css";

export function canonicalPath(pathname: string): string {
  const parts = pathname.split("/").filter(Boolean);
  if (pathname === "/proposals" || pathname === "/proposals/") return "/proposals";
  if (pathname === "/proposals/new") return "/proposals/new";
  if (pathname === "/proposals/sources") return "/proposals/sources";
  if (parts[0] === "proposals" && parts[1] && parts[2] === "editor") return `/proposals/${parts[1]}/editor`;
  if (parts[0] === "proposals" && parts[1]) return `/proposals/${parts[1]}`;
  if (parts[0] === "opportunities" && parts[1] === "new") return "/proposals/new";
  if (parts[0] === "opportunities" && parts[1]) return `/proposals/${parts[1]}`;
  return "/proposals";
}

export function ProposalRoutes({ role }: { role: ProposalRole }) {
  const [path, setPath] = useState(() => canonicalPath(window.location.pathname));
  useEffect(() => {
    const next = canonicalPath(window.location.pathname);
    if (window.location.pathname !== next) window.history.replaceState({}, "", `${next}${window.location.search}${window.location.hash}`);
    setPath(next);
    const sync = () => setPath(canonicalPath(window.location.pathname));
    window.addEventListener("popstate", sync);
    return () => window.removeEventListener("popstate", sync);
  }, []);
  const navigate = (next: string) => {
    window.history.pushState({}, "", next);
    setPath(canonicalPath(next));
    window.dispatchEvent(new PopStateEvent("popstate"));
    if (!navigator.userAgent.toLowerCase().includes("jsdom")) window.scrollTo?.({ top: 0, behavior: "auto" });
  };
  const match = useMemo(() => path.match(/^\/proposals\/([^/]+)$/), [path]);
  const editorMatch = useMemo(() => path.match(/^\/proposals\/([^/]+)\/editor$/), [path]);
  if (path === "/proposals/new") return <NewProposalPage role={role} onBack={() => navigate("/proposals")} onCreated={(id) => navigate(`/proposals/${id}`)} />;
  if (path === "/proposals/sources") return <ProposalSourceWorkspace role={role} onBack={() => navigate("/proposals")} onOpenEditor={(proposalId, revisionId, projectNumber) => navigate(`/proposals/${proposalId}/editor?revision=${encodeURIComponent(revisionId)}&project=${encodeURIComponent(String(projectNumber))}`)} onOpenProposal={(proposalId) => navigate(`/proposals/${proposalId}`)} />;
  if (editorMatch) {
    const revisionId = new URLSearchParams(window.location.search).get("revision");
    return <ProposalEditorEntryRedirect role={role} proposalId={editorMatch[1]} requestedRevisionId={revisionId} navigate={navigate} />;
  }
  if (match) return <ProposalEditorEntryRedirect role={role} proposalId={match[1]} navigate={navigate} />;
  return <ProposalRegisterPage role={role} onOpen={(id) => navigate(`/proposals/${id}`)} onNew={() => navigate("/proposals/sources")} onOpenDraft={(number) => navigate(`/proposals/sources?project=${number}`)} />;
}

type ProposalV1Entry = {
  revision_id?: string | null;
  project_number?: number;
  generation_state?: string;
  editor_mode?: string;
  retry_allowed?: boolean;
  blocker?: string | null;
  generation_summary?: { state?: string; generation_review_reason?: string | null; published_ai_mutation_count?: number };
};

function ProposalEditorEntryRedirect({ role, proposalId, requestedRevisionId, navigate }: { role: ProposalRole; proposalId: string; requestedRevisionId?: string | null; navigate: (next: string) => void }) {
  const [state, setState] = useState<"loading" | "legacy" | "v1" | "editor" | "error">("loading");
  const [entry, setEntry] = useState<ProposalV1Entry | null>(null);
  const headers = { "X-Dev-Role": role };
  const resolve = () => api<ProposalV1Entry>(`/api/proposals-v1/editor/proposals/${encodeURIComponent(proposalId)}/entry`, { headers });
  const applyEntry = (next: ProposalV1Entry) => {
    // A malformed compatibility response is not a V1 entry contract.  The
    // production V1 endpoint always includes generation_state/editor_mode;
    // keeping this guard preserves explicitly legacy adapters while ensuring
    // every valid V1 200 response stays on the V1 surface.
    if (!("generation_state" in next) && !("editor_mode" in next) && !("revision_id" in next)) {
      setState("legacy");
      return;
    }
    // HTTP 200 from the V1 entry endpoint is authoritative.  A missing
    // revision is a generation/provenance state, never evidence of legacy.
    if (["READY_FOR_EDIT", "NO_AI_CHANGES_REQUIRED"].includes(next.generation_state || "") && next.revision_id) {
      if (requestedRevisionId && requestedRevisionId === next.revision_id) {
        setEntry(next);
        setState("editor");
        return;
      }
      navigate(`/proposals/${proposalId}/editor?revision=${encodeURIComponent(next.revision_id)}${next.project_number ? `&project=${encodeURIComponent(String(next.project_number))}` : ""}`);
      return;
    }
    setEntry(next);
    setState("v1");
  };
  useEffect(() => {
    let active = true;
    resolve()
      .then((next) => { if (active) applyEntry(next); })
      .catch((cause: unknown) => { if (!active) return; const status = cause && typeof cause === "object" && "status" in cause ? Number((cause as { status?: number }).status) : 404; setState(status === 404 ? "legacy" : "error"); });
    return () => { active = false; };
  }, [proposalId, requestedRevisionId, role]);
  const retry = async () => {
    setState("loading");
    try {
      await api(`/api/proposals/sources/proposals/${encodeURIComponent(proposalId)}/regenerate`, { method: "POST", headers });
      applyEntry(await resolve());
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : "Proposal V1 generation could not be retried.";
      setEntry((current) => ({ ...(current || {}), generation_state: "FAILED_RETRYABLE", blocker: message, retry_allowed: true }));
      setState("v1");
    }
  };
  if (state === "editor" && entry?.revision_id) return <ProposalDocumentEditor role={role} proposalId={proposalId} revisionId={entry.revision_id} onBack={() => navigate("/proposals")} />;
  if (state === "legacy") return <ProposalWorkspacePage role={role} proposalId={proposalId} onBack={() => navigate("/proposals")} />;
  if (state === "error") return <div className="proposal-alert error-state" role="alert">Proposal could not be opened.</div>;
  if (state === "v1" && entry) return <ProposalV1EntryState entry={entry} onBack={() => navigate("/proposals")} onRetry={entry.retry_allowed ? () => void retry() : undefined} />;
  return <div className="proposal-empty"><b>Opening Proposal V1 editor…</b><span>Resolving the canonical server revision.</span></div>;
}

function ProposalV1EntryState({ entry, onBack, onRetry }: { entry: ProposalV1Entry; onBack: () => void; onRetry?: () => void }) {
  const state = entry.generation_state || "GENERATION_PENDING";
  const progress = ["PENDING_OWNER_SOURCES", "GENERATION_PENDING", "RUNNING"].includes(state);
  const copy: Record<string, { title: string; detail: string; action?: string }> = {
    BASELINE_READY: { title: "Proposal V1 generation is required", detail: "A baseline document is captured, but the AI-generated revision is not ready yet." },
    BLOCKED_BASELINE: { title: "Proposal V1 baseline is blocked", detail: "A recognized Proposal DOCX baseline is required before generation can run." },
    FAILED_RETRYABLE: { title: "Proposal V1 generation failed", detail: "The generated document was not published. Retry generation when the source set is ready.", action: "Retry generation" },
    GENERATION_REVIEW_REQUIRED: { title: "Proposal V1 needs Owner review", detail: entry.generation_summary?.generation_review_reason || "AI produced no valid document changes. Review the baseline and source set, then retry generation.", action: "Retry generation" },
    NO_AI_CHANGES_REQUIRED: { title: "Proposal V1 is ready for editing", detail: "The validated Proposal already matches the selected source evidence." },
    FAILED_VALIDATION: { title: "Proposal V1 validation failed", detail: "The generated DOCX did not pass validation. Review the source set before retrying." },
    STALE_SOURCE_MANIFEST: { title: "Proposal V1 sources changed", detail: "The active source set changed after generation. Regenerate to produce a current document.", action: "Regenerate" },
    PENDING_OWNER_SOURCES: { title: "Proposal V1 is waiting for Owner sources", detail: "Finish source selection before generation can begin." },
    GENERATION_PENDING: { title: "Proposal V1 generation is queued", detail: "The source set is captured and generation is waiting to start." },
    RUNNING: { title: "Proposal V1 is generating", detail: "AI is preparing the source-grounded DOCX revision." },
  };
  const message = copy[state] || { title: "Proposal V1 is not ready", detail: "The Proposal V1 record needs attention before the document editor can open." };
  return <section className="panel proposal-v1-entry-state" aria-label="Proposal V1 generation state"><div className="panel-head"><div><span className="eyebrow">PROPOSALS V1 · DOCUMENT GENERATION</span><h2>{message.title}</h2><p>{message.detail}</p></div><span className="tag">{state.replaceAll("_", " ")}</span></div>{entry.blocker && <div className="proposal-alert warning-copy" role="status">{entry.blocker}</div>}<div className="proposal-modal-actions"><button type="button" className="button-secondary" onClick={onBack}>Back to Proposals V1</button>{onRetry && <button type="button" className="button-primary" onClick={onRetry}>{message.action || "Retry generation"}</button>}</div>{progress && <small className="muted">This Proposal remains in Proposal V1 while generation is in progress.</small>}</section>;
}
