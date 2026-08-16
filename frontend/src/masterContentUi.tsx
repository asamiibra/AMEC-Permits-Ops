import { ReactNode } from "react";
import { Icon } from "./Icon";

export type ContentType = "FORM" | "REPORT" | "ENGINEERING_WORK" | "DEFINITION";

export const CONTENT_LABELS: Record<ContentType, string> = {
  FORM: "Form",
  REPORT: "Report",
  ENGINEERING_WORK: "Engineering Work",
  DEFINITION: "Definition",
};

export const MODULE_LABELS: Record<string, string> = {
  MY_WORK: "My Work",
  BD: "Business Development",
  ADMIN: "Administration",
  ENGINEERING: "Engineering",
  PERMIT: "Permit",
  COMPLETION: "Completion",
  HANDOVER: "Completion / Handover",
  BILLING: "Billing",
  ISSUES: "Issues",
  NOTIFICATIONS: "Notifications",
  REPORTS: "Reports",
  PROPOSAL: "Proposals",
  CONTRACT: "Contracts",
};

export const MODULE_OPTIONS: Record<ContentType, string[]> = {
  FORM: ["MY_WORK", "BD", "ADMIN", "ENGINEERING", "PERMIT", "COMPLETION", "HANDOVER", "BILLING", "PROPOSAL", "CONTRACT"],
  REPORT: ["BD", "ENGINEERING", "PERMIT", "REPORTS", "PROPOSAL", "CONTRACT", "ADMIN"],
  ENGINEERING_WORK: ["ENGINEERING", "PERMIT", "ISSUES", "REPORTS"],
  DEFINITION: ["BD", "ADMIN", "ENGINEERING", "PERMIT", "REPORTS", "PROPOSAL", "CONTRACT"],
};

export function moduleLabel(value: string) {
  return MODULE_LABELS[value] || value;
}

export function friendlyStatus(value?: string, hasVersion = true) {
  if (!hasVersion || value === "NO_VERSION") return "Draft";
  if (value === "CURRENT" || value === "ACTIVE") return "Current";
  if (value === "ARCHIVED") return "Inactive";
  if (value === "Needs Review" || value === "NEEDS_REVIEW") return "Needs Review";
  if (value === "SUPERSEDED") return "Superseded";
  return value ? value.replaceAll("_", " ").toLowerCase().replace(/^./, char => char.toUpperCase()) : "Draft";
}

export function versionLabel(value?: number, definition = false) {
  if (!value) return definition ? "Draft" : "No source file";
  return `${definition ? "Revision " : "Version "}${value}`;
}

export function UsedInPicker({ type, value, onChange }: { type: ContentType; value: string[]; onChange: (next: string[]) => void }) {
  const options = MODULE_OPTIONS[type];
  return <fieldset className="used-in-picker">
    <legend>Used In</legend>
    <p>Choose where this content is available. These links do not create work automatically.</p>
    <div className="used-in-options">{options.map(module => <label key={module} className="module-choice"><input type="checkbox" checked={value.includes(module)} onChange={event => onChange(event.target.checked ? [...value, module] : value.filter(item => item !== module))} /> <span>{moduleLabel(module)}</span></label>)}</div>
  </fieldset>;
}

export function AIAssistCompact() {
  return <section className="ai-assist-compact" aria-label="AI Assist"><div><strong>✨ AI Assist</strong><span>Coming soon</span></div><p>Future help for category suggestions, description writing, and gap checks.</p><div className="ai-assist-compact-actions"><button type="button" disabled>Suggest category</button><button type="button" disabled>Improve description</button><button type="button" disabled>Highlight gaps</button></div><small>Suggestions will always require your review before applying.</small></section>;
}

export function Drawer({ title, eyebrow, children, footer, onClose, wide = false }: { title: string; eyebrow: string; children: ReactNode; footer: ReactNode; onClose: () => void; wide?: boolean }) {
  const submitEditor = (event: React.MouseEvent<HTMLElement>) => { const target = (event.target as HTMLElement).closest("button") as HTMLButtonElement | null; if (target && target.type !== "button" && !target.disabled) (target.closest(".content-drawer-backdrop") as HTMLElement | null)?.querySelector<HTMLFormElement>("form.content-editor-form")?.requestSubmit(); };
  const historyDrawer = eyebrow.includes("HISTORY");
  return <div className="content-drawer-backdrop" role="presentation"><section className={`content-drawer ${wide ? "content-drawer-wide" : ""}`} role="dialog" aria-modal="true" aria-label={title}><header className="content-drawer-header"><div>{historyDrawer && <span className="eyebrow">IMMUTABLE HISTORY</span>}<span className="eyebrow">{eyebrow}</span><h2>{title}</h2></div><button type="button" className="drawer-close" aria-label="Close" onClick={onClose}><Icon name="close" size={16} /></button></header><div className="content-drawer-body">{children}</div><footer className="content-drawer-footer" onClick={submitEditor}>{footer}</footer></section></div>;
}
