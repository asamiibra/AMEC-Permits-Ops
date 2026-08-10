export type DemoRole = "SYSTEM_ADMIN" | "RESPONSIBLE_ENGINEER" | "COMMERCIAL_APPROVER";

export const DEMO_PERSONAS: Array<{ value: DemoRole; label: string }> = [
  { value: "SYSTEM_ADMIN", label: "Owner" },
  { value: "RESPONSIBLE_ENGINEER", label: "Engineering" },
  { value: "COMMERCIAL_APPROVER", label: "Business Development" },
];

const legacyRoleMap: Record<string, DemoRole> = {
  SYSTEM_ADMIN: "SYSTEM_ADMIN",
  REQUIREMENT_STEWARD: "SYSTEM_ADMIN",
  PORTAL_MAINTAINER: "SYSTEM_ADMIN",
  RESPONSIBLE_ENGINEER: "RESPONSIBLE_ENGINEER",
  AUTHORIZED_ENGINEER: "RESPONSIBLE_ENGINEER",
  COMMERCIAL_APPROVER: "COMMERCIAL_APPROVER",
  BD_ASSISTANT: "COMMERCIAL_APPROVER",
  PERMIT_PREPARER: "COMMERCIAL_APPROVER",
  DATA_VERIFIER: "RESPONSIBLE_ENGINEER",
  PACKAGE_APPROVER: "SYSTEM_ADMIN",
  FINAL_SUBMITTER: "SYSTEM_ADMIN",
};

export function readDemoRole(): DemoRole {
  if (typeof window === "undefined") return "SYSTEM_ADMIN";
  const stored = sessionStorage.getItem("proposalops-role") || sessionStorage.getItem("permitops-role");
  return legacyRoleMap[stored || ""] || "SYSTEM_ADMIN";
}

export function visibleRebrandText(value: string): string {
  return value
    .replaceAll("About PermitOps", "Operating Guide")
    .replaceAll("How PermitOps Works", "Operating Guide")
    .replaceAll("Permit Authority Simulator", "Authority Simulator")
    .replaceAll("PERMIT INTEGRITY & WORKFLOW", "PROPOSAL • CONTRACT • PERMIT")
    .replaceAll("PERMIT WORKFLOW", "AMEC WORKFLOW")
    .replaceAll("SYNTHETIC PROTOTYPE · NO PORTAL WRITES · HUMAN SUBMISSION REQUIRED", "SYNTHETIC PROTOTYPE · TEST DATA · SIMULATED INTEGRATIONS")
    .replaceAll("No portal writes", "Simulated integrations")
    .replaceAll("No closure automation", "Human-controlled transitions")
    .replaceAll("Safe boundary", "Synthetic environment")
    .replaceAll("Synthetic data only", "Test data only")
    .replaceAll("PermitOps", "ProposalOps")
    .replaceAll("permitops", "proposalops")
    .replaceAll("My Work", "AMEC Work")
    .replaceAll("my work", "AMEC Work")
    .replaceAll("MY WORK", "AMEC WORK")
    .replaceAll("Permit Preparer", "Engineering")
    // Permit remains a legitimate downstream execution domain. Do not use a
    // global replacement here: Permit Workspace, Permit Application,
    // Municipality Preparation, and Authority Review are owner-facing terms.
    .replaceAll("Four assistant", "Three-persona")
    .replaceAll("four assistants", "three personas")
    .replaceAll("four-assistant", "three-persona");
}

function rewriteTextNodes(root: Node) {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const nodes: Text[] = [];
  let current: Node | null;
  while ((current = walker.nextNode())) nodes.push(current as Text);
  nodes.forEach((node) => {
    const next = visibleRebrandText(node.nodeValue || "");
    if (next !== node.nodeValue) node.nodeValue = next;
  });
}

function rewriteAttributes() {
  document.title = "ProposalOps · Proposal & Contract Workflow";
  document.querySelectorAll<HTMLElement>("[aria-label], [title], input[placeholder]").forEach((element) => {
    ["aria-label", "title", "placeholder"].forEach((attribute) => {
      const value = element.getAttribute(attribute);
      if (value) element.setAttribute(attribute, visibleRebrandText(value));
    });
  });
}

function rewritePersonaSelector() {
  const selectors = Array.from(document.querySelectorAll<HTMLSelectElement>("select"));
  const selector = selectors.find((item) => item.getAttribute("aria-label") === "Role" || Array.from(item.options).some((option) => option.value === "PERMIT_PREPARER"));
  if (!selector) return;
  selector.setAttribute("aria-label", "Persona");
  const selected = legacyRoleMap[selector.value] || "SYSTEM_ADMIN";
  const signature = DEMO_PERSONAS.map((persona) => persona.value).join("|");
  if (Array.from(selector.options).map((option) => option.value).join("|") !== signature) {
    selector.replaceChildren(...DEMO_PERSONAS.map((persona) => new Option(persona.label, persona.value)));
  }
  selector.value = selected;
  const parent = selector.parentElement;
  if (parent?.firstChild?.nodeType === Node.TEXT_NODE) parent.firstChild.nodeValue = "Demo as ";
}

/** Applies the final visible naming boundary while legacy implementation identifiers remain compatible. */
export function RebrandSurface() {
  useEffect(() => {
    if (typeof document === "undefined") return;
    const apply = () => {
      rewriteTextNodes(document.body);
      rewriteAttributes();
      rewritePersonaSelector();
    };
    queueMicrotask(apply);
    const observer = new MutationObserver(apply);
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
    return () => observer.disconnect();
  }, []);
  return null;
}
import { useEffect } from "react";
