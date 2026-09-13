import { useEffect, useState, type ReactNode } from "react";
import { api } from "./api";
import { CanonicalFormsLibrary } from "./MasterContentForms";
import { readDemoRole } from "./rebrand";
import { Icon } from "./Icon";
import { OwnerDecisionCenterPage } from "./OwnerDecisionCenter";
import { ContractMobilizationFeature } from "./contract/ContractMobilizationFeature";

type AdminCategory = { key: string; label: string; route: string; status: string };

const groups = [
  { label: "People & Access", keys: ["people-access"] },
  { label: "Data & Connections", keys: ["data-connections"] },
  { label: "Project & Folder Setup", keys: ["project-folder-setup"] },
  { label: "Proposal & Contract Configuration", keys: ["proposal-setup", "contract-setup", "forms", "templates", "owner-decisions"] },
  { label: "Permit Workflow", keys: ["permit-setup"] },
  { label: "Operations", keys: ["notifications"] },
  { label: "System", keys: ["security", "integration-health", "audit"] },
  { label: "Advanced", keys: ["advanced-diagnostics"] },
];

const endpointFor = (path: string) => {
  const key = path.replace(/^\/admin\/?/, "");
  const apiKeys: Record<string, string> = {
    "data-connections": "connections", "project-folder-setup": "project-setup", "proposal-setup": "proposal-setup",
    "contract-setup": "contract-setup", "permit-setup": "permit-setup", templates: "templates", forms: "master-content-forms", notifications: "notifications",
    security: "security", "integration-health": "integration-health", audit: "audit", "people-access": "users",
  };
  if (key === "advanced-diagnostics" || key.startsWith("advanced-diagnostics/") || key === "control-diagnostics") return "/api/admin/advanced-diagnostics";
  if (key === "owner-decisions") return "/api/owner-decisions";
  if (key === "forms") return "/api/master-content?content_type=FORM";
  return key ? `/api/admin/${apiKeys[key] || "summary"}` : "/api/admin/summary";
};

const human = (value: unknown, fallback = "Needs AMEC Input") => {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value).replaceAll("_", " ").replaceAll("QUOTATION", "PROPOSAL").replaceAll("Quotation", "Proposal");
};

const statusText = (value: unknown) => human(value, "Needs AMEC Input");

export function AdministrationOwnerPage() {
  const [path, setPath] = useState(window.location.pathname);
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const endpoint = endpointFor(path);
  const load = () => { setLoading(true); setError(""); api<any>(endpoint).then(setData).catch((cause) => setError(cause instanceof Error ? cause.message : "Administration is unavailable.")).finally(() => setLoading(false)); };
  const go = (route: string) => { window.history.pushState({}, "", route); window.dispatchEvent(new PopStateEvent("popstate")); };
  useEffect(() => { const sync = () => setPath(window.location.pathname); window.addEventListener("popstate", sync); return () => window.removeEventListener("popstate", sync); }, []);
  useEffect(() => { setData(null); load(); }, [endpoint]);
  if (loading) return <AdminShell path={path} onNavigate={go}><section className="admin-owner-panel"><b>Loading Admin…</b></section></AdminShell>;
  if (error) return <AdminShell path={path} onNavigate={go}><section className="admin-owner-panel admin-owner-error" role="alert"><h2>Admin unavailable</h2><p>{error}</p><button className="button-primary" onClick={load}>Retry</button></section></AdminShell>;
  if (path === "/admin/owner-decisions") return <AdminShell path={path} onNavigate={go}><OwnerDecisionCenterPage /></AdminShell>;
  return <AdminShell path={path} onNavigate={go}>{path === "/admin" || path === "/admin/" ? <Landing data={data} onNavigate={go} /> : <Section path={path} data={data} onNavigate={go} onRefresh={load} />}</AdminShell>;
}

export function ContractMobilizationPage() {
  return <ContractMobilizationFeature />;
}

function ContractMobilizationShell({ onNavigate, children }: { onNavigate: (route: string) => void; children: ReactNode }) {
  return <div className="workflow-page proposals-main contract-mobilization-page"><div className="page-intro proposals-main-intro"><div><span className="eyebrow">AMEC · BUSINESS STAGE 2</span><h2>Contract &amp; Mobilization</h2><p>Contracts, revisions, commercial terms, client inputs, Project Activation, and Service Scope context stay together. Finance remains the operational owner for billing and payment work.</p></div><span className="tag">Owner-controlled business work</span></div>{children}<div className="admin-owner-secondary-links"><button className="admin-owner-secondary-link" onClick={() => onNavigate("/billing")}><b>Related Finance</b><span>Billing Plans, Milestones, Invoices, Receivables, Payments, and Settlement.</span>Open Finance <Icon name="arrow-up-right" size={14} /></button><button className="admin-owner-secondary-link" onClick={() => onNavigate("/admin") }><b>System Administration</b><span>Access, integrations, readiness, notifications, and configuration only.</span>Open Admin <Icon name="arrow-up-right" size={14} /></button></div></div>;
}

function AdminShell({ path, onNavigate, children }: { path: string; onNavigate: (route: string) => void; children: ReactNode }) {
  const label = path === "/admin" || path === "/admin/" ? "Admin" : path.split("/").pop()?.replaceAll("-", " ").replace(/\b\w/g, (letter) => letter.toUpperCase()) || "Admin";
  return <div className="workflow-page admin-owner-page"><div className="page-intro admin-owner-intro"><div><span className="eyebrow">AMEC · SYSTEM ADMINISTRATION</span><h2>{label}</h2><p>{path === "/admin" || path === "/admin/" ? "Configure ProposalOps access, integrations, notifications, environment readiness, and system settings." : "System configuration and readiness; Contract, Project Activation, and Finance work remain in their owning workspaces."}</p></div><span className="tag admin-context-chip">System Configuration</span></div><div className="admin-owner-environment">SYNTHETIC PROTOTYPE · Test data and simulated connections</div>{path !== "/admin" && path !== "/admin/" && <button className="admin-owner-back" onClick={() => onNavigate("/admin")}><Icon name="arrow-left" size={14} /> Admin</button>}{children}</div>;
}

function Landing({ data, onNavigate }: { data: any; onNavigate: (route: string) => void }) {
  const categories = (data.categories || []) as AdminCategory[];
  return <>
    <div className="admin-owner-lead"><div><h3>System administration</h3><p>Configure access, notifications, integrations, environment readiness, reference rules, and system settings. Contract, Project Activation, Invoice, and payment work remain in their owning workspaces.</p></div><button className="button-secondary" onClick={() => onNavigate(data.go_live?.route || "/admin/go-live-readiness")}>Inputs &amp; Go-Live</button></div>
    <section className="admin-owner-panel admin-system-boundary"><div className="admin-owner-panel-heading"><div><span className="eyebrow">SYSTEM BOUNDARY</span><h3>Admin owns configuration, not business records</h3></div><span className="admin-owner-status">Business registers: 0</span></div><div className="admin-owner-chip-grid"><div><b>Users &amp; Access</b><small>Roles and capability permissions</small><span>{categories.find((item) => item.key === "people-access")?.status || "Configured"}</span></div><div><b>Integrations &amp; Connectivity</b><small>Source systems, storage, and health</small><span>{categories.find((item) => item.key === "data-connections")?.status || "Configured"}</span></div><div><b>Environment &amp; Readiness</b><small>Inputs, go-live, and safe operating state</small><span>Owner-controlled</span></div><div><b>Audit &amp; System Activity</b><small>Configuration and access history</small><span>{categories.find((item) => item.key === "audit")?.status || "Available"}</span></div></div></section>
    <SetupControls data={data} onNavigate={onNavigate} />
  </>;
}

function OperationalPreview({ title, eyebrow, counts, countKeys, columns, children, onViewAll, onCreate, createLabel, createHint }: { title: string; eyebrow: string; counts: Record<string, number>; countKeys: readonly (readonly [string, string])[]; columns: string[]; children: ReactNode; onViewAll: () => void; onCreate?: () => void; createLabel?: string; createHint?: string }) {
  const hasChildren = Array.isArray(children) ? children.length > 0 : Boolean(children);
  if (counts.ERROR) return <section className="admin-owner-panel admin-operational-preview"><div className="admin-owner-panel-heading"><div><span className="eyebrow">{eyebrow}</span><h3>{title}</h3></div><span className="admin-owner-status">Unavailable</span></div><div className="admin-owner-error" role="status"><b>{title} summary unavailable</b><p>Use Retry above to reload the live register.</p></div></section>;
  return <section className="admin-owner-panel admin-operational-preview"><div className="admin-owner-panel-heading"><div><span className="eyebrow">{eyebrow}</span><h3>{title}</h3></div><div className="admin-operational-preview-actions">{onCreate && <button className="button-primary" onClick={onCreate} title={createHint}> {createLabel} </button>}<button className="button-secondary" onClick={onViewAll}>View all {title}</button></div></div><div className="filter-row admin-operational-preview-lanes" role="group" aria-label={`${title} lanes`}>{countKeys.map(([key, label]) => <span className="filter" key={key}>{label}<strong>{counts[key] ?? 0}</strong></span>)}</div><div className="admin-owner-table admin-operational-preview-table"><div className="admin-permission-head">{columns.map((column) => <b key={column}>{column}</b>)}</div>{children}{!hasChildren && <div className="empty-state">No {title.toLowerCase()} are currently available.</div>}</div></section>;
}

const ownerStage = (value: unknown) => ({ DRAFT: "Contract Draft", NEEDS_ACTION: "Needs Action", AUTHORITY_REVIEW: "Authority Review", READY: "Ready for activation", READY_CLOSE: "Ready / Close", ACTIVE: "Active", CLOSED: "Closed", FINALIZED: "Accepted", APPROVED: "Approved", ACCEPTED_INTERNAL: "Accepted internally", ISSUED: "Issued", NOT_ISSUED: "Not issued", NEED_ACTION: "Needs Action", NOT_READY: "Not ready", AWAITING_DUE_EVENT: "Awaiting due event", PARTIALLY_PAID: "Partially paid", PAID: "Paid" }[String(value || "").toUpperCase()] || human(value, "Not configured"));
const ownerNextAction = (value: unknown, stage: unknown) => value ? human(value) : String(stage || "").toUpperCase() === "DRAFT" ? "Review Contract" : "No action recorded";

const contractLanes = [["ALL", "All"], ["NEEDS_ACTION", "Need Action"], ["AUTHORITY_REVIEW", "Authority Review"], ["READY_CLOSE", "Ready / Close"]] as const;

function OperationalContracts({ onNavigate }: { onNavigate: (route: string) => void }) {
  const [lane, setLane] = useState("ALL");
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<any[]>([]);
  const [counts, setCounts] = useState<Record<string, number>>({ ALL: 0, NEEDS_ACTION: 0, AUTHORITY_REVIEW: 0, READY_CLOSE: 0 });
  const [proposals, setProposals] = useState<any[]>([]);
  const [proposalId, setProposalId] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const load = async (nextLane = lane, nextQuery = query) => {
    setError("");
    try {
      const laneResponses = await Promise.all(contractLanes.map(([key]) => api<any>(`/api/admin/contracts?q=${encodeURIComponent(nextQuery)}&filter=${key}`)));
      setCounts(Object.fromEntries(contractLanes.map(([key], index) => [key, laneResponses[index].count ?? laneResponses[index].items?.length ?? 0])));
      setItems(laneResponses[contractLanes.findIndex(([key]) => key === nextLane)]?.items || []);
      const proposalData = await api<any>("/api/bd/proposals");
      setProposals((proposalData.items || []).filter((item: any) => item.contract_eligible));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Contracts could not be loaded.");
    }
  };
  useEffect(() => { void load("ALL", ""); }, []);
  const selectLane = (nextLane: string) => { setLane(nextLane); void load(nextLane, query); };
  const search = () => { void load(lane, query); };
  const create = async () => {
    if (!proposalId) { setMessage("Select an accepted Proposal revision before creating a Contract."); return; }
    setMessage("");
    try {
      const result = await api<any>("/api/admin/contracts", { method: "POST", body: JSON.stringify({ proposal_id: proposalId }) });
      onNavigate(`/admin/contracts/${result.id}`);
    } catch (cause) { setMessage(cause instanceof Error ? cause.message : "Contract could not be created. The accepted Proposal remains unchanged."); }
  };
  return <section className="admin-owner-panel admin-operational-register"><div className="admin-owner-panel-heading"><div><span className="eyebrow">CONTRACT &amp; MOBILIZATION · CONTRACTS</span><h3>Contracts</h3><p className="admin-owner-copy">One canonical Contract register sourced from the accepted Proposal revision and current Contract readiness.</p></div><span className="admin-owner-status">{counts.ALL} accessible</span></div><div className="admin-operational-toolbar"><div className="filter-row" role="tablist" aria-label="Contract lanes">{contractLanes.map(([key, label]) => <button key={key} className={`filter ${lane === key ? "active" : ""}`} role="tab" aria-selected={lane === key} onClick={() => selectLane(key)}>{label}<strong>{counts[key]}</strong></button>)}</div><div className="admin-operational-actions"><input aria-label="Search Contracts" placeholder="Search Contract, Client, or Project ref" value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") search(); }} /><button className="button-secondary" onClick={search}>Search</button><select aria-label="Accepted Proposal for new Contract" value={proposalId} onChange={(event) => setProposalId(event.target.value)}><option value="">Select accepted Proposal…</option>{proposals.map((item) => <option key={item.id} value={item.id}>{item.proposal || item.proposal_description || "Proposal"} · {item.proposal_reference || item.reference || "Accepted"}</option>)}</select><button className="button-primary" onClick={create} disabled={!proposalId} title={!proposalId ? "Select an accepted Proposal first" : "Create a Contract draft"}>+ New Contract</button></div></div>{error && <div className="admin-owner-error" role="alert"><b>Could not load Contracts</b><p>{error}</p><button className="button-primary" onClick={() => void load(lane, query)}>Retry</button></div>}{message && <div className="admin-owner-message" role="status">{message}</div>}<div className="admin-owner-table contract-owner-list"><div className="admin-permission-head"><b>Contract</b><b>Contract Ref</b><b>Stage</b><b>Amount</b><b>Close Date</b><b>Open</b></div>{items.map((item) => <div className="admin-owner-row" key={item.id}><div><b>{item.contract_name || item.contract || "Unnamed Contract"}</b><small>{item.client?.name || "Client pending"} · {item.project_opportunity_ref || "Project / Opportunity Ref pending"}{item.project_code ? ` · Project Code: ${item.project_code}` : ""}</small></div><span>{item.contract_reference || item.contract_ref || "Pending"}</span><em>{String(item.stage || "DRAFT").replaceAll("_", " ")}</em><span>{item.amount ? `${item.amount} ${item.currency || ""}` : "—"}</span><span>{item.close_date || "—"}</span><button className="text-button" onClick={() => onNavigate(`/admin/contracts/${item.id}`)}>Open <Icon name="arrow-up-right" size={14} /></button></div>)}{!items.length && !error && <div className="empty-state"><b>No Contracts in this lane.</b><p>Use + New Contract with an accepted Proposal, or choose another lane.</p></div>}</div><div className="admin-owner-safe"><b>Contract control boundary</b><span>Open shows the same canonical Contract workspace. It does not activate a Project, close a Contract, or create an Invoice.</span></div></section>;
}

function SetupControls({ data, onNavigate }: { data: any; onNavigate: (route: string) => void }) {
  const categories = (data.categories || []) as AdminCategory[];
  return <section className="admin-owner-panel admin-setup-controls"><div className="admin-owner-panel-heading"><div><span className="eyebrow">ADMINISTRATION · SECONDARY</span><h3>Setup &amp; Controls</h3><p className="admin-owner-copy">Configuration and governance surfaces remain available here; Contract and Invoice records stay in the primary workspaces.</p></div><button className="button-secondary" onClick={() => onNavigate("/admin/go-live-readiness")}>View Inputs &amp; Go-Live</button></div><div className="admin-owner-groups">{groups.map((group) => <section className={`admin-owner-group ${group.label === "Advanced" ? "secondary" : ""}`} key={group.label}><div className="admin-owner-group-heading"><h3>{group.label}</h3></div><div className="admin-owner-cards">{group.keys.map((key) => { const item = categories.find((category) => category.key === key); return item ? <button className="admin-owner-card" key={key} onClick={() => onNavigate(item.route)}><span><b>{item.label}</b><small>{cardCopy(key)}</small></span><em>{item.status}</em><strong><Icon name="arrow-up-right" size={14} /></strong></button> : null; })}</div></section>)}</div></section>;
}

function cardCopy(key: string) {
  const copy: Record<string, string> = { "people-access": "Users, roles, and capability permissions", "data-connections": "Source systems with simulator and production status", "project-folder-setup": "References, folder structure, and semantic mappings", "proposal-setup": "Proposal fields, intake sources, stages, and handoffs", "contract-setup": "Contract numbering, fields, templates, and lifecycle policy configuration", forms: "Canonical Forms used across AMEC workflows", templates: "Controlled Proposal, Contract, and Permit templates", "permit-setup": "Requirements, applicability, attachments, and Municipality mode", notifications: "Audiences, reminders, and follow-up rules", security: "Data mode, access, MFA, retention, and backups", "integration-health": "Cross-system checks using the canonical status truth", audit: "Owner-readable system activity", "advanced-diagnostics": "Technical evidence and adapter diagnostics" }; return copy[key] || "Configuration and status";
}

function Section({ path, data, onNavigate, onRefresh }: { path: string; data: any; onNavigate: (route: string) => void; onRefresh: () => void }) {
  const key = path.replace(/^\/admin\//, "");
  if (key === "setup-controls") return <SetupControls data={data} onNavigate={onNavigate} />;
  if (key === "people-access") return <People data={data} onNavigate={onNavigate} />;
  if (key === "data-connections") return <Connections data={data} onRefresh={onRefresh} />;
  if (key === "project-folder-setup") return <ProjectSetup data={data} onNavigate={onNavigate} />;
  if (key === "proposal-setup") return <ProposalSetup data={data} onNavigate={onNavigate} />;
  if (key === "contract-setup") return <ContractSetup data={data} onNavigate={onNavigate} />;
  if (key === "forms") return <CanonicalFormsLibrary role={readDemoRole()} surface="ADMINISTRATION" compact />;
  if (key === "permit-setup") return <PermitSetup data={data} />;
  if (key === "templates") return <Templates data={data} />;
  if (key === "notifications") return <Notifications data={data} onRefresh={onRefresh} />;
  if (key === "security") return <Security data={data} />;
  if (key === "integration-health") return <IntegrationHealth data={data} onNavigate={onNavigate} />;
  if (key === "audit") return <Audit data={data} onNavigate={onNavigate} />;
  if (key === "advanced-diagnostics" || key.startsWith("advanced-diagnostics/") || key === "control-diagnostics") return <Advanced data={data} onNavigate={onNavigate} />;
  return <section className="admin-owner-panel"><h3>Admin route unavailable</h3><p>This route is not part of the system administration surface.</p><button className="button-primary" onClick={() => onNavigate("/admin")}>Back to Admin</button></section>;
}

function People({ data, onNavigate }: { data: any; onNavigate: (route: string) => void }) { return <div className="admin-owner-two-col"><section className="admin-owner-panel"><div className="admin-owner-panel-heading"><div><span className="eyebrow">PEOPLE &amp; ACCESS</span><h3>Users &amp; Roles</h3></div><span className="admin-owner-status">{statusText(data.production_user_management)}</span></div><div className="admin-owner-table">{(data.users || []).map((user: any) => <div className="admin-owner-row" key={user.id}><div><b>{user.name}</b><small>{user.email} · {user.office}</small></div><span>{user.role}</span><em>{user.status}</em></div>)}</div><p className="admin-owner-note">Synthetic users illustrate the current role model. Production provisioning remains an AMEC setup input.</p><button className="text-button" onClick={() => onNavigate(data.inputs_route || "/admin/go-live-readiness")}>View what we need from AMEC <Icon name="arrow-up-right" size={14} /></button></section><section className="admin-owner-panel"><span className="eyebrow">CAPABILITY MATRIX</span><h3>What each role can do</h3><div className="admin-permission-table"><div className="admin-permission-head"><b>Capability</b><b>Owner</b><b>Business Development</b><b>Engineering</b></div>{(data.permissions || []).map((row: any) => <div className="admin-permission-row" key={row.capability}><span>{row.capability}</span><span>{row.owner}</span><span>{row.business_development}</span><span>{row.engineering}</span></div>)}</div></section></div>; }

function Connections({ data, onRefresh: _onRefresh }: { data: any; onRefresh: () => void }) { const [message, setMessage] = useState(""); const test = async (name: string) => { setMessage(""); try { const result = await api<any>("/api/admin/connections/test", { method: "POST", body: JSON.stringify({ name }) }); setMessage(`${result.name}: ${result.status} · tested ${new Date(result.tested_at).toLocaleString()}`); } catch (cause) { setMessage(cause instanceof Error ? cause.message : "Connection test failed."); } }; return <section className="admin-owner-panel"><div className="admin-owner-panel-heading"><div><span className="eyebrow">DATA &amp; CONNECTIONS</span><h3>Source Connections</h3></div><span className="admin-owner-status">Credentials masked</span></div><div className="admin-owner-connection-grid">{(data.connections || []).map((connection: any) => <article key={connection.name}><div><b>{connection.name}</b><p>{connection.purpose}</p></div><span className="admin-owner-health">{connection.status}</span><small>{connection.environment} · {connection.production_status}</small><small>{connection.affected_workflow}{connection.last_tested ? ` · Last tested ${new Date(connection.last_tested).toLocaleString()}` : ""}</small><button className="button-secondary" onClick={() => test(connection.name)}>Test connection</button></article>)}</div>{message && <div className="admin-owner-message" role="status">{message}</div>}<p className="admin-owner-note">Simulator status is not production connectivity. Production setup details remain in Inputs &amp; Go-Live.</p></section>; }

function ProjectSetup({ data, onNavigate }: { data: any; onNavigate: (route: string) => void }) { return <div className="admin-owner-two-col"><section className="admin-owner-panel"><span className="eyebrow">PROJECT &amp; FOLDER SETUP</span><h3>References and project identity</h3><div className="admin-owner-definition-list"><b>Proposal before Project</b><span>{data.reference_behavior?.proposal_before_project}</span><b>Canonical Project Reference</b><span>{data.reference_behavior?.project_reference}</span><b>Lineage</b><span>{data.reference_behavior?.lineage}</span><b>Demo scenario</b><span>{data.scenario?.project_type} · {data.scenario?.municipality} · {data.scenario?.status}</span></div><p className="admin-owner-note">The displayed references and folders are synthetic examples; AMEC production numbering and root location remain setup inputs.</p></section><section className="admin-owner-panel"><span className="eyebrow">FOLDER STRUCTURE</span><h3>Semantic source mappings</h3>{(data.folder_structure || []).map((item: any) => <div className="admin-owner-row" key={item.category}><div><b>{item.category}</b><small>{item.mapping} · {item.reconciliation}</small></div><em>{item.status}</em></div>)}<div className="admin-owner-definition-list"><b>Root mapping</b><span>{data.root_mapping}</span><b>Template version</b><span>{data.folder_template_version}</span><b>Excel project register</b><span>{data.excel_mapping?.status}{data.excel_mapping?.project_reference ? ` · ${data.excel_mapping.project_reference}` : ""}</span></div><button className="text-button" onClick={() => onNavigate("/admin/go-live-readiness")}>View what we need from AMEC <Icon name="arrow-up-right" size={14} /></button></section></div>; }

function ProposalSetup({ data, onNavigate }: { data: any; onNavigate: (route: string) => void }) { return <section className="admin-owner-panel"><span className="eyebrow">PROPOSAL SETUP</span><h3>Proposal workflow configuration</h3><p className="admin-owner-copy">These fields, sources, and handoffs are derived from the current Proposal intake and preparation contract. Requiredness remains backend-controlled.</p><h4>Required Proposal intake fields</h4><div className="admin-owner-chip-grid">{(data.required_fields || []).map((item: any) => <div key={item.key}><b>{item.label}</b><span>{item.status}</span></div>)}</div><h4>Allowed intake sources</h4><div className="admin-owner-chip-grid">{(data.source_types || []).map((item: any) => <div key={item.key}><b>{item.label}</b><small>{item.purpose}</small><span>{item.status}</span></div>)}</div><div className="admin-owner-definition-list"><b>Current demo stage</b><span>{data.lifecycle?.current_demo_stage}</span><b>Readiness</b><span>{data.lifecycle?.readiness}</span><b>Handoffs</b><span>{(data.handoffs || []).map((item: any) => `${item.from} → ${item.to}: ${item.when}`).join(" · ")}</span><b>Reference rule</b><span>{data.reference_rule}</span></div><button className="text-button" onClick={() => onNavigate(data.template_route || "/admin/templates")}>View templates <Icon name="arrow-up-right" size={14} /></button></section>; }

function ContractSetup({ data, onNavigate }: { data: any; onNavigate: (route: string) => void }) {
  return <section className="admin-owner-panel"><span className="eyebrow">CONTRACT CONFIGURATION</span><h3>Contract reference and policy settings</h3><p className="admin-owner-copy">Admin configures numbering, templates, required fields, and lifecycle policy. Contract records, revisions, commercial terms, and activation are managed in Contract &amp; Mobilization.</p><div className="admin-owner-definition-list"><b>Contract reference rule</b><span>{data.contract_reference_rule || "Needs AMEC Input"}</span><b>Lifecycle prerequisite</b><span>{data.eligibility || "Accepted Proposal revision required; no automatic legal Contract."}</span><b>Project Activation rule</b><span>Explicit human activation remains separate from Contract creation.</span></div><div className="admin-owner-chip-grid">{(data.required_fields || []).map((item: any) => <div key={item.label}><b>{item.label}</b><span>{item.status}</span></div>)}</div><button className="text-button" onClick={() => onNavigate(data.template_route || "/admin/templates")}>View canonical templates <Icon name="arrow-up-right" size={14} /></button></section>;
}

function ContractInputs({ data }: { data: any }) { return <section className="admin-owner-panel"><span className="eyebrow">INPUTS &amp; GO-LIVE · ADMINISTRATION CONTRACTS</span><h3>Contract and Project setup inputs</h3><p className="admin-owner-copy">These are explicit Owner decisions. Safe defaults are visible, but production authority, numbering, evidence, and Synology details remain configurable.</p><div className="admin-owner-chip-grid">{(data.items || []).map((item: any) => <div key={item.key}><b>{item.title}</b><small>{item.requested_input}</small><span>{item.status}{item.safe_default !== undefined ? ` · default: ${String(item.safe_default)}` : ""}</span></div>)}</div><div className="admin-owner-safe"><b>{data.items?.length || 0} required Contract inputs are registered</b><span>Real Synology verification remains an external go-live dependency. Contract, Project, Client, Proposal, task, issue, and notification records remain canonical.</span></div></section>; }

function PermitSetup({ data }: { data: any }) { return <div className="admin-owner-two-col"><section className="admin-owner-panel"><span className="eyebrow">PERMIT WORKFLOW SETUP</span><h3>Requirements and attachments</h3><h4>Requirement applicability</h4>{(data.requirements || []).map((item: any) => <div className="admin-owner-row" key={item.name}><div><b>{item.name}</b><small>{item.description} · {item.applicability}</small></div><em>{item.status}</em></div>)}<h4>Attachment categories</h4>{(data.attachments || []).map((item: any) => <div className="admin-owner-row" key={item.label}><div><b>{item.label}</b><small>{item.formats?.join(", ") || "Configured formats"}</small></div><em>{item.required_state}</em></div>)}</section><section className="admin-owner-panel"><span className="eyebrow">MUNICIPALITY CONFIGURATION</span><h3>{data.municipality?.mode || "Needs AMEC Input"}</h3><div className="admin-owner-definition-list"><b>MFA</b><span>{data.municipality?.mfa}</span><b>Supported reads</b><span>{data.municipality?.supported_reads?.join(", ") || "Needs AMEC Input"}</span><b>Supported writes</b><span>{data.municipality?.supported_writes?.join(", ") || "Needs AMEC Input"}</span><b>Safety boundary</b><span>Reads and assisted preparation are simulated; final submission remains human-controlled.</span></div></section></div>; }

function Templates({ data }: { data: any }) { return <section className="admin-owner-panel"><span className="eyebrow">TEMPLATES &amp; DOCUMENTS</span><h3>Controlled template catalog</h3><div className="admin-owner-template-grid">{(data.templates || []).map((item: any) => <article key={item.id}><b>{item.name}</b><small>{item.purpose} · {item.owner_role}</small><span>{item.status}</span>{item.versions?.map((version: any) => <div key={version.version}>Version {version.version} · {version.status}</div>)}</article>)}</div><p className="admin-owner-note">Synthetic stand-ins are clearly marked. Production Proposal, Contract, Permit, and Municipality templates require AMEC confirmation.</p></section>; }

function Notifications({ data, onRefresh: _onRefresh }: { data: any; onRefresh: () => void }) { const [hours, setHours] = useState<number | "">(data.settings?.follow_up_hours ?? ""); const [message, setMessage] = useState(""); const save = async () => { setMessage(""); if (!hours || hours < 1 || hours > 720) { setMessage("Enter a follow-up time between 1 and 720 hours."); return; } try { await api("/api/admin/notifications/follow-up", { method: "PUT", body: JSON.stringify({ follow_up_hours: hours }) }); setMessage("Follow-up timing saved and audited."); } catch (cause) { setMessage(cause instanceof Error ? cause.message : "Configuration could not be saved."); } }; return <section className="admin-owner-panel"><span className="eyebrow">NOTIFICATIONS &amp; FOLLOW-UP</span><h3>Notification audiences and follow-up</h3><div className="admin-owner-chip-grid">{(data.audiences || []).map((item: any) => <div key={item.name}><b>{item.name}</b><small>{item.summary}</small><span>{item.status}</span></div>)}</div><div className="admin-owner-edit"><label>Follow-up reminder timing <input aria-label="Follow-up reminder timing" type="number" min="1" max="720" value={hours} onChange={(event) => setHours(event.target.value ? Number(event.target.value) : "")} /><small>Hours · synthetic test configuration until AMEC confirms policy.</small></label><button className="button-primary" onClick={save}>Save setting</button></div>{message && <div className="admin-owner-message" role="status">{message}</div>}<p className="admin-owner-note">Resulting notifications remain in the operational work surface; no external email is sent from this prototype.</p><div className="admin-owner-definition-list"><b>Delivery boundary</b><span>{data.delivery_boundary}</span><b>Recent events</b><span>{data.recent_event_count ?? 0} recorded operational events</span></div></section>; }

function Security({ data }: { data: any }) { const rows = [["Environment", data.environment?.label, data.environment?.status], ["Production data", data.data_classification?.label, data.data_classification?.status], ["MFA", data.mfa?.label, data.mfa?.status], ["Role-based access", data.role_based_access?.label, data.role_based_access?.status], ["Audit retention", data.audit_retention?.label, data.audit_retention?.status], ["Backup and recovery", data.backup_recovery?.label, data.backup_recovery?.status]]; return <section className="admin-owner-panel"><span className="eyebrow">DATA, SECURITY &amp; RETENTION</span><h3>Safe operating configuration</h3><div className="admin-owner-chip-grid">{rows.map(([label, detail, status]) => <div key={String(label)}><b>{label}</b><small>{detail}</small><span>{status}</span></div>)}</div><div className="admin-owner-safe"><b>Secrets exposed: No</b><span>Passwords, tokens, OTP values, database URLs, and authorization headers are not returned to this screen.</span></div></section>; }

function IntegrationHealth({ data, onNavigate }: { data: any; onNavigate: (route: string) => void }) { return <section className="admin-owner-panel"><div className="admin-owner-panel-heading"><div><span className="eyebrow">INTEGRATION HEALTH</span><h3>Cross-system health</h3></div><span className="admin-owner-status">Checked {data.checked_at ? new Date(data.checked_at).toLocaleString() : "—"}</span></div><p className="admin-owner-copy">{data.purpose}</p><div className="admin-owner-table">{(data.integrations || []).map((item: any) => <div className="admin-owner-row" key={item.name}><div><b>{item.name}</b><small>{item.affected_workflow}</small></div><span>{item.status}</span><em>{item.production_status}</em></div>)}</div><button className="text-button" onClick={() => onNavigate("/admin/data-connections")}>Manage source connections <Icon name="arrow-up-right" size={14} /></button></section>; }

function Audit({ data, onNavigate }: { data: any; onNavigate: (route: string) => void }) { return <section className="admin-owner-panel"><div className="admin-owner-panel-heading"><div><span className="eyebrow">AUDIT HISTORY</span><h3>Owner-readable operational history</h3></div><button className="button-secondary" onClick={() => onNavigate("/admin/advanced-diagnostics")}>Technical detail</button></div><div className="admin-owner-table">{(data.events || []).map((event: any) => <div className="admin-owner-row" key={event.id}><div><b>{event.action}</b><small>{event.record} · {event.when}</small></div><span>{event.actor}</span><em>{event.outcome}</em></div>)}</div></section>; }

function Advanced({ data, onNavigate }: { data: any; onNavigate: (route: string) => void }) { return <section className="admin-owner-panel admin-owner-advanced"><span className="eyebrow">ADVANCED DIAGNOSTICS · SECONDARY</span><h3>Technical evidence and diagnostics</h3><p>Technical IDs, hashes, adapter evidence, and synthetic fixture diagnostics stay separate from normal Owner configuration. No credentials or authorization material is shown.</p>{(data.diagnostics || []).map((item: any) => <button className="admin-owner-card" key={item.name} onClick={() => onNavigate(item.route)}><span><b>{item.name}</b><small>{item.purpose} · {item.status}</small></span><strong><Icon name="arrow-up-right" size={14} /></strong></button>)}</section>; }
