import { useEffect, useState } from "react";
import { api } from "./api";
import { PermitWorkspacePage, type Project, type WorkflowStage } from "./WorkflowFirst";
import type { Persona } from "./PersonaIssuesNotifications";

const stageBySlug: Record<string, WorkflowStage> = {
  "project-and-sources": "PROJECT_AND_SOURCES",
  "verify-data": "VERIFY_DATA",
  "prepare-package": "PREPARE_PACKAGE",
  "municipality-preparation": "MUNICIPALITY_PREPARATION",
  "final-review": "FINAL_REVIEW",
  "authority-review": "AUTHORITY_REVIEW",
  "comments-and-corrections": "COMMENTS_AND_CORRECTIONS",
  history: "HISTORY",
};

const slugByStage = Object.fromEntries(Object.entries(stageBySlug).map(([slug, stage]) => [stage, slug])) as Record<WorkflowStage, string>;

function personaForRole(role: string): Persona {
  if (role === "COMMERCIAL_APPROVER") return "BUSINESS_DEVELOPMENT";
  if (role === "RESPONSIBLE_ENGINEER") return "ENGINEERING";
  return "OWNER";
}

export function PermitCompatibilityPage({ role }: { role: string }) {
  const match = window.location.pathname.match(/^\/(projects|permits|proposals-contracts)\/([^/]+)(?:\/([^/]+))?$/);
  const routePrefix = match?.[1] || "projects";
  const projectId = match?.[2] || "";
  const initialStage = stageBySlug[match?.[3] || ""] || "PROJECT_AND_SOURCES";
  const [project, setProject] = useState<Project | null>(null);
  const [activeStage, setActiveStage] = useState<WorkflowStage>(initialStage);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!projectId) {
      setError("The Permit workspace reference is missing.");
      return;
    }
    api<Project[]>('/api/projects').then((projects) => {
      const resolved = projects.find((item) => item.id === projectId);
      if (!resolved) throw new Error("The Permit workspace could not be resolved.");
      setProject(resolved);
    }).catch((cause) => setError(cause instanceof Error ? cause.message : "The Permit workspace is unavailable."));
  }, [projectId]);

  useEffect(() => {
    const syncStage = () => {
      const next = window.location.pathname.match(/^\/(projects|permits|proposals-contracts)\/[^/]+(?:\/([^/]+))?$/);
      setActiveStage(stageBySlug[next?.[2] || ""] || "PROJECT_AND_SOURCES");
    };
    window.addEventListener("popstate", syncStage);
    return () => window.removeEventListener("popstate", syncStage);
  }, []);

  const openStage = (stage: WorkflowStage) => {
    setActiveStage(stage);
    window.history.pushState({}, "", `/${routePrefix}/${projectId}/${slugByStage[stage]}`);
  };
  const go = (route: string) => {
    window.history.pushState({}, "", route);
    window.dispatchEvent(new PopStateEvent("popstate"));
  };

  if (error) return <section className="panel error-state" role="alert"><h2>Permit workspace unavailable</h2><p>{error}</p></section>;
  if (!project) return <section className="panel"><b>Loading Permit workspace…</b></section>;
  return <PermitWorkspacePage project={project} persona={personaForRole(role)} activeStage={activeStage} openStage={openStage} openLegacy={(page) => go(`/contract-mobilization?context=${encodeURIComponent(page)}`)} backToPermits={() => go("/opportunities")} />;
}
