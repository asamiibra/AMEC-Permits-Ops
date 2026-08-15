import { useEffect, useState } from "react";
import { api } from "./api";

type WorkFilters = { team: string; domain: string; kpi: string };

const KPI = [
  ["needs_action", "Needs Action", "Current actions, handoffs, and exceptions"],
  ["waiting_review", "Waiting for Review", "A person needs to review something"],
  ["blocked", "Blocked", "Work cannot continue until resolved"],
  ["overdue", "Overdue", "Past a configured due time"],
] as const;

const domains = [["all", "All work"], ["proposal", "Proposals"], ["contract", "Contracts"], ["permit", "Permits"], ["system", "System"]];

function readFilters(): WorkFilters {
  const query = new URLSearchParams(window.location.search);
  return { team: query.get("team") || "all", domain: query.get("domain") || "all", kpi: query.get("kpi") || "all" };
}

function workUrl(filters: WorkFilters) {
  const query = new URLSearchParams();
  if (filters.team !== "all") query.set("team", filters.team);
  if (filters.domain !== "all") query.set("domain", filters.domain);
  if (filters.kpi !== "all") query.set("kpi", filters.kpi);
  const suffix = query.toString();
  return `/work${suffix ? `?${suffix}` : ""}`;
}

function dueCopy(item: any) {
  if (!item.overdue && !item.due_at) return "";
  if (item.overdue) {
    const days = Math.max(1, Math.ceil((Date.now() - new Date(item.due_at).getTime()) / 86400000));
    return `Overdue ${days} day${days === 1 ? "" : "s"}`;
  }
  const days = Math.ceil((new Date(item.due_at).getTime() - Date.now()) / 86400000);
  return days <= 0 ? "Due today" : days === 1 ? "Due tomorrow" : `Due in ${days} days`;
}

function label(value: string) { return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase()); }

export function AMECWorkPage({ openAbout }: { openAbout?: () => void }) {
  const [filters, setFilters] = useState<WorkFilters>(readFilters);
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [demoRole, setDemoRole] = useState(() => sessionStorage.getItem("proposalops-role") || "SYSTEM_ADMIN");
  const isOwner = !["COMMERCIAL_APPROVER", "RESPONSIBLE_ENGINEER"].includes(demoRole);

  const load = () => {
    setLoading(true); setError("");
    const query = new URLSearchParams();
    if (filters.team !== "all") query.set("team", filters.team);
    if (filters.domain !== "all") query.set("domain", filters.domain);
    if (filters.kpi !== "all") query.set("kpi", filters.kpi);
    api<any>(`/api/work${query.toString() ? `?${query}` : ""}`).then(setData).catch((cause) => setError(cause instanceof Error ? cause.message : "Some work data could not be loaded.")).finally(() => setLoading(false));
  };

  useEffect(() => { const timer = window.setInterval(() => setDemoRole(sessionStorage.getItem("proposalops-role") || "SYSTEM_ADMIN"), 100); return () => window.clearInterval(timer); }, []);
  useEffect(() => { load(); }, [filters.team, filters.domain, filters.kpi, demoRole]);
  useEffect(() => { const sync = () => setFilters(readFilters()); window.addEventListener("popstate", sync); return () => window.removeEventListener("popstate", sync); }, []);

  const update = (next: Partial<WorkFilters>) => {
    const value = { ...filters, ...next };
    setFilters(value); window.history.pushState({}, "", workUrl(value));
  };
  const summary = data?.summary || {};
  const items = (data?.items || []) as any[];
  const hasActiveFilter = filters.team !== "all" || filters.domain !== "all" || filters.kpi !== "all";
  const filterLabel = [filters.team !== "all" ? label(filters.team) : "", filters.domain !== "all" ? domains.find(([value]) => value === filters.domain)?.[1] || label(filters.domain) : "", filters.kpi !== "all" ? KPI.find(([value]) => value === filters.kpi)?.[1] || label(filters.kpi) : ""].filter(Boolean).join(" · ");
  const clearFilters = () => update({ team: "all", domain: "all", kpi: "all" });

  return <div className="workflow-page amec-work-page">
    <div className="page-intro amec-work-intro"><div><span className="eyebrow">AMEC WORK</span><span className="eyebrow">PROPOSAL • CONTRACT • PERMIT</span><h2>What needs attention</h2><p>One prioritized worklist across proposals, contracts, permits, and handoffs.</p></div><span className="tag">SYNTHETIC PROTOTYPE</span></div>
    <div className="amec-work-helper">Test data and simulated integrations · Open each item in its exact business context.</div>
    {openAbout && <section className="about-entry-card amec-work-guide"><div className="about-entry-mark">?</div><div><span className="eyebrow">NEW TO PROPOSALOPS?</span><h3>See how ProposalOps works</h3><p>Follow the flow from proposal intake through contract and permit delivery.</p></div><button className="button-primary" onClick={openAbout}>Open Operating Guide →</button></section>}
    <section className="dashboard-destination-grid" aria-label="Dashboards">
      <a className="dashboard-destination-card" href="/dashboard"><span className="eyebrow">MASTER CONTENT</span><h3>Dashboard</h3><p>Existing Forms, Reports, Engineering Works, and Definitions workspace.</p><span className="button-secondary">Open Dashboard →</span></a>
    </section>
    <div className="amec-work-kpis" aria-label="Work summary">
      {KPI.map(([key, title, hint]) => <button key={key} className={`amec-work-kpi ${filters.kpi === key ? "selected" : ""}`} aria-pressed={filters.kpi === key} onClick={() => update({ kpi: filters.kpi === key ? "all" : key })}><span>{title}</span><strong>{loading || error ? "—" : summary[key] ?? 0}</strong><small>{hint}</small></button>)}
    </div>
    <div className="amec-work-toolbar"><div className="amec-work-filters">
      {isOwner && <label>Team<select aria-label="Team" value={filters.team} onChange={(event) => update({ team: event.target.value, kpi: filters.kpi })}><option value="all">All teams</option><option value="business_development">Business Development</option><option value="engineering">Engineering</option><option value="owner">Owner</option>{data?.has_unassigned && <option value="unassigned">Unassigned</option>}</select></label>}
      <label>Work<select aria-label="Work" value={filters.domain} onChange={(event) => update({ domain: event.target.value, kpi: filters.kpi })}>{domains.map(([value, text]) => <option value={value} key={value}>{text}</option>)}</select></label>
    </div>{hasActiveFilter && <div className="amec-work-active-filter"><span>Showing: {filterLabel || "All work"} · {items.length} result{items.length === 1 ? "" : "s"}</span><button className="text-button" onClick={clearFilters}>Clear filters</button></div>}</div>
    {loading && <section className="panel amec-work-loading" role="status" aria-live="polite">Loading AMEC Work…</section>}
    {!loading && error && <section className="panel amec-work-error" role="alert"><h3>Some work data could not be loaded.</h3><p>The work list did not return a valid result, so no zero or caught-up state is shown.</p><button className="button-primary" onClick={load}>Retry</button></section>}
    {!loading && !error && <section className="panel amec-work-list"><div className="panel-head"><div><span className="eyebrow">PRIORITY WORK</span><h3>{items.length ? `${items.length} open item${items.length === 1 ? "" : "s"}` : hasActiveFilter ? `No ${filterLabel || "work"} matches these filters` : data.unfiltered_visible_count ? "No work matches this view" : "You're caught up"}</h3>{data.context_visible_count > 0 && <small className="amec-work-overlap-note">{data.summary.needs_action} actions · {data.summary.waiting_review} reviews · Blocked and Overdue are overlapping conditions.</small>}</div></div>{items.length ? items.map((item) => <WorkCard item={item} key={item.id} />) : hasActiveFilter ? <div className="amec-work-empty"><b>No {filterLabel || "work"} matches these filters.</b><p>Clear the active filters to return to the full AMEC Work queue.</p><button className="button-secondary" onClick={clearFilters}>Clear filters</button></div> : <div className="amec-work-empty"><b>{data.unfiltered_visible_count ? "No work matches this view." : "No AMEC work currently needs action."}</b><p>{data.unfiltered_visible_count ? "The current work context has no matching items." : "New actions, reviews, handoffs, and exceptions will appear here when a human decision is required."}</p><a className="button-secondary" href="/proposals-contracts">View Proposals &amp; Contracts</a></div>}</section>}
    {!loading && !error && data?.recent_changes?.length > 0 && <section className="panel amec-work-changes"><div className="panel-head"><div><span className="eyebrow">RECENT IMPORTANT CHANGES</span><h3>What changed</h3></div><a className="text-button" href="/notifications">View all notifications →</a></div>{data.recent_changes.slice(0, 3).map((change: any) => <a className="amec-work-change" href={change.deep_link || "/notifications"} key={change.id}><div><b>{change.title}</b><small>{change.detail}</small></div><span>{change.when ? new Date(change.when).toLocaleDateString() : "Recent"}</span></a>)}</section>}
  </div>;
}

function WorkCard({ item }: { item: any }) {
  const urgency = dueCopy(item);
  return <article className="amec-work-card"><div className="amec-work-card-main"><div className="amec-work-card-top"><span className="amec-domain">{label(item.domain)}</span>{item.blocking && <span className="amec-blocking">Blocking</span>}{urgency && <span className={item.overdue ? "amec-overdue" : "amec-due"}>{urgency}</span>}</div><h4>{item.title}</h4><p>{item.business_context}</p><div className="amec-work-card-meta"><span>{item.reference || "System"}</span><span>{item.assigned_team}{item.assigned_user ? ` · ${item.assigned_user}` : ""}</span>{item.stage && <span>{item.stage}</span>}</div></div><a className="button-secondary" href={item.deep_link}>{item.cta_label || "Review source"}</a></article>;
}
