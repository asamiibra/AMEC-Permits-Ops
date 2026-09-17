import { useEffect, useMemo, useState } from "react";
import { NewProposalPage } from "./NewProposalPage";
import { ProposalRegisterPage } from "./ProposalRegisterPage";
import { ProposalWorkspacePage } from "./ProposalWorkspacePage";
import { ProposalSourceWorkspace } from "../../ProposalSourceWorkspace";
import { ProposalDocumentEditor } from "../../ProposalDocumentEditor";
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
  if (path === "/proposals/sources") return <ProposalSourceWorkspace role={role} onBack={() => navigate("/proposals")} onOpenEditor={(proposalId, revisionId) => navigate(`/proposals/${proposalId}/editor?revision=${encodeURIComponent(revisionId)}`)} />;
  if (editorMatch) return <ProposalDocumentEditor role={role} proposalId={editorMatch[1]} revisionId={new URLSearchParams(window.location.search).get("revision") || undefined} onBack={() => navigate(`/proposals/${editorMatch[1]}`)} />;
  if (match) return <ProposalWorkspacePage role={role} proposalId={match[1]} onBack={() => navigate("/proposals")} />;
  return <ProposalRegisterPage role={role} onOpen={(id) => navigate(`/proposals/${id}`)} onNew={() => navigate("/proposals/new")} />;
}
