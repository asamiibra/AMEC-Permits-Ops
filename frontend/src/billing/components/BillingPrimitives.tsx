import type { ReactNode } from "react";
import { Icon } from "../../Icon";

export const humanize = (value: unknown) => String(value ?? "—").replaceAll("_", " ").toLowerCase().replace(/(^|\s)\S/g, (letter) => letter.toUpperCase());
export const money = (value: unknown, currency?: string | null) => value == null || value === "" ? "—" : `${value}${currency ? ` ${currency}` : ""}`;

export function StatusSet({ items }: { items: Array<[string, unknown]> }) {
  return <div className="billing-status-set" aria-label="Billing status dimensions">{items.map(([label, value]) => <span className="billing-status" key={label}><small>{label}</small><b>{humanize(value)}</b></span>)}</div>;
}

export function MetricCard({ label, value, tone = "default", detail }: { label: string; value: ReactNode; tone?: "default" | "warning" | "danger"; detail?: string }) {
  return <article className={`billing-metric billing-metric-${tone}`}><span>{label}</span><strong>{value}</strong>{detail && <small>{detail}</small>}</article>;
}

export function Panel({ title, eyebrow, children, action }: { title: string; eyebrow?: string; children: ReactNode; action?: ReactNode }) {
  return <section className="billing-panel"><div className="billing-panel-head"><div>{eyebrow && <span className="eyebrow">{eyebrow}</span>}<h3>{title}</h3></div>{action}</div>{children}</section>;
}

export function StateMessage({ kind, title, detail, onRetry }: { kind: "loading" | "empty" | "error" | "denied" | "policy"; title: string; detail: string; onRetry?: () => void }) {
  return <div className={`billing-state billing-state-${kind}`} role={kind === "error" || kind === "denied" ? "alert" : undefined}><Icon name={kind === "error" || kind === "denied" ? "alert" : kind === "loading" ? "refresh" : "help"} size={18} /><div><b>{title}</b><p>{detail}</p>{onRetry && <button className="button-secondary" onClick={onRetry}>Retry</button>}</div></div>;
}

export function PolicyUnresolved({ label, detail }: { label: string; detail?: string }) {
  return <div className="billing-policy-unresolved"><b>Owner decision required</b><span>{label}</span>{detail && <small>{detail}</small>}</div>;
}

export function TechnicalDetails({ children }: { children: ReactNode }) {
  return <details className="billing-technical"><summary>Technical metadata</summary><div>{children}</div></details>;
}
