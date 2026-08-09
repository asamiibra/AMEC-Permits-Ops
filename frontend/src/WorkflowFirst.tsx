import { useEffect, useMemo, useState } from "react";
import { api } from "./api";
import "./workflow.css";
import "./workflow-overrides.css";
import { UnifiedMyWorkPanel } from "./UnifiedWork";

export type Project = {
  id: string;
  project_number: string;
  project_name: string;
  municipality: string;
  permit_type: string;
  workstream?: string;
  status: string;
  assigned_engineer?: string | null;
};

export type Application = {
  id: string;
  project_id: string;
  external_request_number: string;
  application_status: string;
  repetition_count: number;
  municipality: string;
  permit_type: string;
  last_status_at?: string;
};

export type WorkflowStage =
  | "PROJECT_AND_SOURCES"
  | "VERIFY_DATA"
  | "PREPARE_PACKAGE"
  | "MUNICIPALITY_PREPARATION"
  | "FINAL_REVIEW"
  | "AUTHORITY_REVIEW"
  | "COMMENTS_AND_CORRECTIONS"
  | "HISTORY";

export const WORKFLOW_STAGES: Array<{ code: WorkflowStage; number: string; label: string; short: string }> = [
  { code: "PROJECT_AND_SOURCES", number: "1", label: "Project & Sources", short: "Sources" },
  { code: "VERIFY_DATA", number: "2", label: "Verify Data", short: "Verify" },
  { code: "PREPARE_PACKAGE", number: "3", label: "Prepare Package", short: "Package" },
  { code: "MUNICIPALITY_PREPARATION", number: "4", label: "Municipality Preparation", short: "Municipality" },
  { code: "FINAL_REVIEW", number: "5", label: "Final Review & Human Submit", short: "Final review" },
  { code: "AUTHORITY_REVIEW", number: "6", label: "Authority Review", short: "Authority" },
  { code: "COMMENTS_AND_CORRECTIONS", number: "7", label: "Comments & Corrections", short: "Corrections" },
  { code: "HISTORY", number: "8", label: "History / Close", short: "History" },
];

export type NextAction = {
  action_code: string;
  action_label: string;
  reason: string;
  owner_role: string;
  stage: WorkflowStage;
  blocking: boolean;
};

const activeFinding = (finding: any) => !["CLOSED", "RESOLVED", "DISMISSED"].includes(String(finding?.status || "").toUpperCase());

export function projectWorkflowStage(application?: Application | null, findings: any[] = []): WorkflowStage {
  const status = String(application?.application_status || "DRAFT").toUpperCase();
  if (status === "RETURNED") return "COMMENTS_AND_CORRECTIONS";
  if (["UNDER_REVIEW", "SUBMITTED", "SUBMITTED_CONFIRMED"].includes(status)) return "AUTHORITY_REVIEW";
  if (["APPROVED", "CLOSED", "SUBMITTED_APPROVED"].includes(status)) return "HISTORY";
  if (["PREPARING", "MUNICIPALITY_PREPARATION", "VERIFIED_DRAFT"].includes(status)) return "MUNICIPALITY_PREPARATION";
  return "PROJECT_AND_SOURCES";
}

export function projectNextAction(project: Project, application?: Application | null, findings: any[] = []): NextAction {
  const status = String(application?.application_status || "DRAFT").toUpperCase();
  const blocking = findings.filter((finding) => Boolean(finding?.blocking) && activeFinding(finding));
  if (blocking.length) {
    return {
      action_code: "RESOLVE_BLOCKING_FINDING",
      action_label: `Resolve ${blocking.length} blocking ${blocking.length === 1 ? "issue" : "issues"}`,
      reason: blocking[0]?.title || "A blocking integrity or authority issue needs evidence.",
      owner_role: blocking[0]?.assignee_role || blocking[0]?.owner?.display_name || "Assigned reviewer",
      stage: status === "RETURNED" ? "COMMENTS_AND_CORRECTIONS" : "VERIFY_DATA",
      blocking: true,
    };
  }
  if (status === "RETURNED") return { action_code: "REVIEW_NEW_AUTHORITY_COMMENTS", action_label: "Review authority comments", reason: "The authority returned this application and the correction loop is open.", owner_role: "Responsible Engineer", stage: "COMMENTS_AND_CORRECTIONS", blocking: true };
  if (["UNDER_REVIEW", "SUBMITTED", "SUBMITTED_CONFIRMED"].includes(status)) return { action_code: "REVIEW_AUTHORITY_STATUS", action_label: "Review authority status", reason: "The application is in authority review; monitoring is read-only.", owner_role: "Permit team", stage: "AUTHORITY_REVIEW", blocking: false };
  if (["APPROVED", "CLOSED", "SUBMITTED_APPROVED"].includes(status)) return { action_code: "OPEN_HISTORY", action_label: "Review permit history", reason: "The latest authority state is approved; inspect the evidence timeline.", owner_role: "Permit team", stage: "HISTORY", blocking: false };
  return { action_code: "ESTABLISH_PROJECT_SOURCES", action_label: "Confirm project & sources", reason: `${project.project_number} needs its source-system links confirmed before verification.`, owner_role: "Permit Preparer", stage: "PROJECT_AND_SOURCES", blocking: true };
}

const stageIndex = (stage: WorkflowStage) => WORKFLOW_STAGES.findIndex((item) => item.code === stage);
const statusClass = (status: string) => `status status-${String(status || "working").toLowerCase().replaceAll("_", "-")}`;
const arrayFrom = (value: any): any[] => Array.isArray(value) ? value : value?.items || value?.documents || value?.conflicts || value?.findings || value?.rows || [];
const fmtDate = (value?: string) => value ? new Date(value).toLocaleDateString() : "—";

function PermitIdentity({ project, application }: { project: Project; application?: Application | null }) {
  return <div className="permit-identity"><div><span className="eyebrow">PERMIT WORKSPACE</span><h2>{project.project_number} · {project.project_name}</h2><p>{application?.external_request_number || "No municipality application linked"} · {project.municipality} · {project.permit_type}</p></div><div className="permit-identity-meta"><span className={statusClass(application?.application_status || project.status)}>{application?.application_status || project.status}</span><small>Owner / next actor</small><b>{project.assigned_engineer || "Permit team"}</b></div></div>;
}

export function PermitStageStepper({ currentStage, activeStage, onSelect }: { currentStage: WorkflowStage; activeStage: WorkflowStage; onSelect: (stage: WorkflowStage) => void }) {
  const current = stageIndex(currentStage);
  return <div className="workflow-stepper" aria-label="Permit lifecycle">
    {WORKFLOW_STAGES.map((item, index) => <button key={item.code} className={`workflow-step ${item.code === activeStage ? "active" : ""} ${item.code === currentStage ? "current" : ""} ${index < current ? "complete" : ""}`} onClick={() => onSelect(item.code)} aria-current={item.code === currentStage ? "step" : undefined}>
      <span className="workflow-step-dot">{index < current ? "✓" : item.number}</span><span>{item.short}</span>{item.code === currentStage && <small>YOU ARE HERE</small>}
    </button>)}
  </div>;
}

function NextActionCard({ action, onOpen }: { action: NextAction; onOpen: () => void }) {
  return <section className={`next-action-card ${action.blocking ? "blocking" : ""}`} aria-label="Next action"><div><span className="eyebrow">NEXT ACTION</span><h3>{action.action_label}</h3><p>{action.reason}</p><small>Owner: <b>{action.owner_role}</b> · Stage: {WORKFLOW_STAGES.find((stage) => stage.code === action.stage)?.label}</small></div><button className="button-primary" onClick={onOpen}>{action.action_label}</button></section>;
}

export function MyWorkPage({ projects, applications, openPermit, openAbout }: { projects: Project[]; applications: Application[]; openPermit: (projectId: string, stage?: WorkflowStage) => void; openAbout?: () => void }) {
  const [findings, setFindings] = useState<any[]>([]); const [tasks, setTasks] = useState<any[]>([]); const [notifications, setNotifications] = useState<any[]>([]); const [message, setMessage] = useState("");
  useEffect(() => { Promise.all([api<any>("/api/findings"), api<any>("/api/tasks"), api<any>("/api/notifications")]).then(([f, t, n]) => { setFindings(f.findings || []); setTasks(t.tasks || []); setNotifications(n.notifications || []); }).catch((error) => setMessage(error.message)); }, []);
  const findingsByProject = useMemo(() => findings.reduce((map, finding) => { (map[finding.project_id] ||= []).push(finding); return map; }, {} as Record<string, any[]>), [findings]);
  const work = projects.map((project) => ({ project, application: applications.find((item) => item.project_id === project.id), findings: findingsByProject[project.id] || [] })).map((item) => ({ ...item, action: projectNextAction(item.project, item.application, item.findings) }));
  const blocked = work.filter((item) => item.action.blocking || item.application?.application_status === "RETURNED");
  const authorityChanges = work.filter((item) => item.application?.application_status === "RETURNED");
  const failedNotifications = notifications.filter((notification) => notification.status === "FAILED" || notification.result === "FAILED");
  return <div className="workflow-page"><PageIntro kicker="MY WORK" title="Resume permit work" description="One prioritized worklist for assigned actions, reviews, blockers, authority changes, and delivery failures. Every card opens the exact permit stage." />{openAbout && <section className="about-entry-card"><div className="about-entry-mark">?</div><div><span className="eyebrow">NEW TO PERMITOPS?</span><h3>See how PermitOps works</h3><p>See the workflow, what is included in the current MVP, and how permit information stays controlled and traceable.</p></div><button className="button-primary" onClick={openAbout}>Explore PermitOps →</button></section>}<UnifiedMyWorkPanel />
    {message && <div className="error-banner">Work signals unavailable: {message}</div>}
    <div className="workflow-summary-grid"><div><span>Action required</span><strong>{blocked.length}</strong><small>Domain-derived next actions</small></div><div><span>Reviews waiting</span><strong>{tasks.length}</strong><small>Durable review tasks</small></div><div><span>Authority changes</span><strong>{authorityChanges.length}</strong><small>Returned or newly changed</small></div><div><span>Delivery failures</span><strong>{failedNotifications.length}</strong><small>Notification evidence</small></div></div>
    <section className="panel workflow-section"><div className="panel-head"><div><span className="eyebrow">ACTION REQUIRED</span><h3>Start with the highest-impact permit action</h3></div><button className="text-button" onClick={() => openPermit(projects[0]?.id || "")}>View permits →</button></div>{blocked.length ? blocked.map((item) => <WorkItem key={item.project.id} project={item.project} application={item.application} action={item.action} onOpen={() => openPermit(item.project.id, item.action.stage)} />) : <EmptyState title="No blocking permit actions" body="When a package, finding, or authority change needs work, the deterministic next action appears here." />}</section>
    <div className="two-col workflow-columns"><section className="panel"><div className="panel-head"><div><span className="eyebrow">REVIEWS WAITING FOR ME</span><h3>Assigned review tasks</h3></div><button className="text-button" onClick={() => openPermit(tasks[0]?.finding?.project_id || projects[0]?.id || "", "COMMENTS_AND_CORRECTIONS")}>All reviews →</button></div>{tasks.length ? tasks.slice(0, 6).map((task) => <div className="work-row" key={task.id}><div><b>{task.title}</b><small>{task.owner_role || "Assigned reviewer"} · {task.status || "OPEN"}</small></div><button className="button-secondary" onClick={() => openPermit(task.finding?.project_id || projects[0]?.id || "", "COMMENTS_AND_CORRECTIONS")}>Open</button></div>) : <EmptyState title="No assigned reviews" body="Field verification, technical review, package approval, and closure tasks will appear when assigned." />}</section><section className="panel"><div className="panel-head"><div><span className="eyebrow">BLOCKED PERMITS</span><h3>Why work cannot continue</h3></div></div>{blocked.slice(0, 5).map((item) => <div className="work-row" key={item.project.id}><div><b>{item.project.project_number}</b><small>{item.action.reason}</small><small>Owner: {item.action.owner_role}</small></div><span className="status status-returned">BLOCKED</span></div>)}{!blocked.length && <EmptyState title="No blocked permits" body="All visible permits can continue to their projected next action." />}</section></div>
    <div className="two-col workflow-columns"><section className="panel"><div className="panel-head"><div><span className="eyebrow">RECENT AUTHORITY CHANGES</span><h3>Status and comment changes</h3></div></div>{authorityChanges.length ? authorityChanges.map((item) => <WorkItem key={item.project.id} project={item.project} application={item.application} action={item.action} onOpen={() => openPermit(item.project.id, "COMMENTS_AND_CORRECTIONS")} compact />) : <EmptyState title="No new authority changes" body="Read-only monitoring changes will be shown here with repetition and evidence." />}</section><section className="panel"><div className="panel-head"><div><span className="eyebrow">NOTIFICATIONS / FAILURES</span><h3>Delivery evidence</h3></div></div>{notifications.length ? notifications.slice(0, 6).map((notification) => <div className="work-row" key={notification.id}><div><b>{notification.subject || notification.event_type || "Permit notification"}</b><small>{notification.channel || "System"} · {notification.status || notification.result || "PENDING"}</small></div><span className={statusClass(notification.status || notification.result || "PENDING")}>{notification.status || notification.result || "PENDING"}</span></div>) : <EmptyState title="No notification failures" body="Failed delivery, retry evidence, and system alerts will be visible without duplicating the task queue." />}</section></div>
  </div>;
}

function WorkItem({ project, application, action, onOpen, compact = false }: { project: Project; application?: Application | null; action: NextAction; onOpen: () => void; compact?: boolean }) {
  return <div className={`work-item ${compact ? "compact" : ""}`}><div className="work-item-main"><span className="eyebrow">{project.project_number} · {application?.external_request_number || "NO APPLICATION"}</span><h3>{project.project_name}</h3><b className="work-action-label">{action.action_label}</b><p>{action.reason}</p><small>Stage: {WORKFLOW_STAGES.find((stage) => stage.code === action.stage)?.label} · Owner: {action.owner_role}</small></div><button className="button-secondary" onClick={onOpen}>{compact ? "Review" : "Open next action"}</button></div>;
}

export function PermitsPage({ projects, applications, openPermit }: { projects: Project[]; applications: Application[]; openPermit: (projectId: string, stage?: WorkflowStage) => void }) {
  const [filter, setFilter] = useState("ALL");
  const rows = projects.map((project) => ({ project, application: applications.find((item) => item.project_id === project.id) }));
  const visible = rows.filter(({ application }) => filter === "ALL" || (filter === "RETURNED" && application?.application_status === "RETURNED") || (filter === "REVIEW" && ["UNDER_REVIEW", "SUBMITTED"].includes(application?.application_status || "")) || (filter === "CLOSED" && ["APPROVED", "CLOSED"].includes(application?.application_status || "")));
  return <div className="workflow-page"><PageIntro kicker="PERMITS" title="Permit portfolio" description="Open a permit workspace to see its lifecycle, current stage, blockers, owner, evidence, and exact next action." /><section className="panel table-panel"><div className="toolbar"><div className="filter-row"><button className={filter === "ALL" ? "filter active" : "filter"} onClick={() => setFilter("ALL")}>All permits</button><button className={filter === "RETURNED" ? "filter active" : "filter"} onClick={() => setFilter("RETURNED")}>Needs action</button><button className={filter === "REVIEW" ? "filter active" : "filter"} onClick={() => setFilter("REVIEW")}>Authority review</button><button className={filter === "CLOSED" ? "filter active" : "filter"} onClick={() => setFilter("CLOSED")}>Ready / closed</button></div><span className="muted">{visible.length} permit workspaces</span></div><table><thead><tr><th>Project / permit</th><th>Municipality application</th><th>Current stage / status</th><th>Owner / next actor</th><th>Last activity</th><th>Open</th></tr></thead><tbody>{visible.map(({ project, application }) => { const action = projectNextAction(project, application); const stage = projectWorkflowStage(application); return <tr key={project.id} onClick={() => openPermit(project.id, stage)}><td><b className="linkish">{project.project_number}</b><br /><span>{project.project_name}</span></td><td>{application?.external_request_number || "Not linked"}</td><td><b>{WORKFLOW_STAGES.find((item) => item.code === stage)?.label}</b><br /><span className={statusClass(application?.application_status || project.status)}>{application?.application_status || project.status}</span></td><td>{action.owner_role}<br /><small>{action.action_label}</small></td><td>{fmtDate(application?.last_status_at)}</td><td><button className="button-secondary" onClick={(event) => { event.stopPropagation(); openPermit(project.id, stage); }}>Open workspace</button></td></tr>; })}</tbody></table></section></div>;
}

export function ReviewsPage({ projects, applications, openPermit }: { projects: Project[]; applications: Application[]; openPermit: (projectId: string, stage?: WorkflowStage) => void }) {
  const [tasks, setTasks] = useState<any[]>([]); useEffect(() => { api<any>("/api/tasks").then((response) => setTasks(response.tasks || [])).catch(() => setTasks([])); }, []);
  return <div className="workflow-page"><PageIntro kicker="REVIEWS" title="Reviews waiting for me" description="Review work is sourced from durable verification, technical, package, handoff, and finding-closure tasks." /><section className="panel"><div className="panel-head"><h3>Assigned reviews</h3><span className="tag">{tasks.length} open</span></div>{tasks.length ? tasks.map((task) => { const project = projects.find((item) => item.id === task.finding?.project_id) || projects[0]; return <div className="review-card" key={task.id}><div><span className="eyebrow">{task.owner_role || "ASSIGNED REVIEW"}</span><h3>{task.title}</h3><p>{task.finding?.title || "Review the linked permit evidence and record the governed decision."}</p><small>Status: {task.status || "OPEN"} · Due: {fmtDate(task.due_at)}</small></div><button className="button-primary" onClick={() => openPermit(project.id, "COMMENTS_AND_CORRECTIONS")}>Open review</button></div>; }) : <EmptyState title="No reviews waiting" body="There are no durable review tasks assigned to this operator. New reviews will link directly to their permit stage." />}</section><section className="panel review-guide"><span className="eyebrow">REVIEW BOUNDARY</span><h3>Professional decisions stay human-owned</h3><p>System administration does not grant professional approval. Final submission remains a human action in the municipality portal; PermitOps exposes no machine Submit capability.</p></section></div>;
}

export function IssuesPage({ projects, applications, openPermit }: { projects: Project[]; applications: Application[]; openPermit: (projectId: string, stage?: WorkflowStage) => void }) {
  const [findings, setFindings] = useState<any[]>([]); const [readiness, setReadiness] = useState<Record<string, any>>({});
  useEffect(() => { api<any>("/api/findings").then((response) => setFindings(response.findings || [])).catch(() => setFindings([])); Promise.all(projects.map((project) => api<any>(`/api/projects/${project.id}/readiness`).then((value) => [project.id, value] as const).catch(() => [project.id, null] as const))).then((items) => setReadiness(Object.fromEntries(items))); }, [projects]);
  const blockedPackages = Object.entries(readiness).filter(([, value]) => value?.evaluation?.overall_status === "BLOCKED");
  return <div className="workflow-page"><PageIntro kicker="ISSUES" title="Issues across permits" description="Blocking findings, package blockers, portal mismatches, stale state, and delivery failures stay visible with owner and evidence context." /><div className="workflow-summary-grid"><div><span>Open findings</span><strong>{findings.filter(activeFinding).length}</strong><small>Finding workflow</small></div><div><span>Blocking findings</span><strong>{findings.filter((finding) => activeFinding(finding) && finding.blocking).length}</strong><small>Stops the relevant gate</small></div><div><span>Blocked packages</span><strong>{blockedPackages.length}</strong><small>Readiness projection</small></div><div><span>Permits in scope</span><strong>{projects.length}</strong><small>Canonical projects</small></div></div><section className="panel"><div className="panel-head"><h3>Open findings</h3><span className="tag">{findings.length}</span></div>{findings.length ? findings.map((finding) => { const project = projects.find((item) => item.id === finding.project_id) || projects[0]; return <div className="issue-card" key={finding.id}><div className="finding-severity">{finding.blocking ? "!" : "•"}</div><div><span className="eyebrow">{project?.project_number || "PERMIT"} · {finding.source_type || "SYSTEM"}</span><h3>{finding.title}</h3><p>{finding.raw_text || finding.normalized_summary || "Evidence-backed issue requiring review."}</p><small>Owner: {finding.assignee_role || finding.owner?.display_name || "Unassigned"} · Status: {finding.status || "OPEN"}</small></div><button className="button-secondary" onClick={() => openPermit(project.id, "COMMENTS_AND_CORRECTIONS")}>Open issue</button></div>; }) : <EmptyState title="No open findings" body="When a finding, portal mismatch, stale item, or authority comment is captured, it will deep-link to the affected permit." />}</section></div>;
}

export function NotificationsPage({ projects, applications, openPermit }: { projects: Project[]; applications: Application[]; openPermit: (projectId: string, stage?: WorkflowStage) => void }) {
  const [notifications, setNotifications] = useState<any[]>([]); const [observability, setObservability] = useState<any>(null);
  useEffect(() => { Promise.all([api<any>("/api/notifications"), api<any>("/api/notifications/observability")]).then(([items, detail]) => { setNotifications(items.notifications || []); setObservability(detail); }).catch(() => {}); }, []);
  return <div className="workflow-page"><PageIntro kicker="NOTIFICATIONS" title="Notifications & delivery" description="Unread alerts, failed deliveries, acknowledgements, and system notices are visible without becoming a duplicate task queue." /><div className="workflow-summary-grid"><div><span>Unread / visible</span><strong>{notifications.length}</strong><small>Notification events</small></div><div><span>Failed delivery</span><strong>{notifications.filter((item) => (item.status || item.result) === "FAILED").length}</strong><small>Retry evidence retained</small></div><div><span>Delivery failure rate</span><strong>{observability ? `${Math.round((observability.delivery_failure_rate || 0) * 100)}%` : "—"}</strong><small>Read-only observability</small></div><div><span>Fallback recipient</span><strong>{observability?.fallback_recipient_visible ? "VISIBLE" : "—"}</strong><small>Process Champion routing</small></div></div><section className="panel"><div className="panel-head"><h3>Notification history</h3><span className="tag">Delivery evidence</span></div>{notifications.length ? notifications.map((notification) => <div className="notification-card" key={notification.id}><div><span className="eyebrow">{notification.channel || "SYSTEM"}</span><h3>{notification.subject || notification.event_type || "Permit notification"}</h3><p>{notification.body || "System notification retained with delivery state."}</p><small>{notification.finding_id ? `Finding ${notification.finding_id}` : "Permit-level event"} · {notification.created_at ? fmtDate(notification.created_at) : "—"}</small></div><span className={statusClass(notification.status || notification.result || "PENDING")}>{notification.status || notification.result || "PENDING"}</span></div>) : <EmptyState title="No notification events" body="Failed delivery, acknowledgement, and system alerts will appear here when emitted by the domain workflows." />}</section></div>;
}

export function PermitWorkspacePage({ project, application, activeStage, openStage, openLegacy, backToPermits }: { project: Project; application?: Application | null; activeStage: WorkflowStage; openStage: (stage: WorkflowStage) => void; openLegacy: (page: string, projectId?: string) => void; backToPermits: () => void }) {
  const [findings, setFindings] = useState<any[]>([]); const [detail, setDetail] = useState<any>(null);
  useEffect(() => { api<any>(`/api/projects/${project.id}`).then(setDetail).catch(() => {}); api<any>(`/api/findings?project_id=${project.id}`).then((value) => setFindings(value.findings || [])).catch(() => setFindings([])); }, [project.id]);
  const currentStage = projectWorkflowStage(application, findings); const action = projectNextAction(project, application, findings);
  return <div className="workflow-page permit-workspace"><button className="back-button" onClick={backToPermits}>← Permit portfolio</button><PermitIdentity project={project} application={application} /><PermitStageStepper currentStage={currentStage} activeStage={activeStage} onSelect={openStage} /><div className="breadcrumb"><span>My Work</span><b>›</b><span>{project.project_number}</span><b>›</b><strong>{WORKFLOW_STAGES.find((item) => item.code === activeStage)?.label}</strong></div><NextActionCard action={action} onOpen={() => openStage(action.stage)} />
    {activeStage === "PROJECT_AND_SOURCES" && <SourcesStage project={project} detail={detail} />}
    {activeStage === "VERIFY_DATA" && <VerifyStage project={project} findings={findings} openLegacy={(page) => openLegacy(page, project.id)} />}
    {activeStage === "PREPARE_PACKAGE" && <WorkspaceStage title="Prepare Package" description="Requirements, forms, Excel projections, drawing metadata, attachments, and internal reviews are package-contextual. The readiness gate remains deterministic." actionLabel="Open package preparation" onOpen={() => openLegacy("package", project.id)} />}
    {activeStage === "MUNICIPALITY_PREPARATION" && <WorkspaceStage title="Municipality Preparation" description="Prepare in configured portal order with assisted field entry, stable grid identity, exact attachments, save/reopen reconciliation, and precheck evidence." actionLabel="Open assisted preparation" onOpen={() => openLegacy("municipality", project.id)} />}
    {activeStage === "FINAL_REVIEW" && <FinalReviewStage project={project} application={application} openLegacy={(page) => openLegacy(page, project.id)} />}
    {activeStage === "AUTHORITY_REVIEW" && <AuthorityReviewStage project={project} application={application} openLegacy={(page) => openLegacy(page, project.id)} />}
    {activeStage === "COMMENTS_AND_CORRECTIONS" && <WorkspaceStage title="Comments & Corrections" description="Findings, tasks, notifications, evidence, closure verification, recurrence, staleness, and the resubmission gate stay together in this permit context." actionLabel="Open permit issues" onOpen={() => openLegacy("findings", project.id)} />}
    {activeStage === "HISTORY" && <HistoryStage project={project} detail={detail} openLegacy={(page) => openLegacy(page, project.id)} />}
  </div>;
}

function SourcesStage({ project, detail }: { project: Project; detail: any }) {
  const links = detail?.links || []; return <section className="panel stage-panel"><div className="stage-heading"><div><span className="eyebrow">STAGE 1 · PROJECT & SOURCES</span><h3>Establish the permit workspace</h3><p>Confirm project identity and the source-system links that drive later verification.</p></div><span className="tag">{links.length >= 3 ? "READY FOR VERIFICATION" : "BLOCKED"}</span></div><div className="source-grid"><div><span className="eyebrow">PROJECT</span><dl><dt>Project number</dt><dd>{project.project_number}</dd><dt>Consultancy office</dt><dd>AMEC Engineering</dd><dt>Project type</dt><dd>{project.workstream || project.permit_type}</dd></dl></div><div><span className="eyebrow">SOURCE SYSTEMS</span>{links.length ? links.map((link: any) => <div className="source-link" key={link.id}><span className="source-check">✓</span><div><b>{link.system_type}</b><small>{link.display_reference}</small></div><span className="tag">LINKED</span></div>) : <Blocker text="Missing required source-system link" owner="Permit Preparer" evidence="Project identity and source reference" />}</div></div></section>;
}

function VerifyStage({ project, findings, openLegacy }: { project: Project; findings: any[]; openLegacy: (page: string) => void }) {
  const [documents, setDocuments] = useState<any[]>([]); const [conflicts, setConflicts] = useState<any[]>([]); useEffect(() => { Promise.all([api<any>(`/api/projects/${project.id}/documents`), api<any>(`/api/projects/${project.id}/conflicts`)]).then(([docs, items]) => { setDocuments(arrayFrom(docs)); setConflicts(arrayFrom(items)); }).catch(() => {}); }, [project.id]);
  const groups = [{ label: "PROPERTY", types: ["TITLE_DEED", "SURVEY_PLAN"] }, { label: "OWNERS / REPRESENTATION", types: ["OWNER_QID", "AUTHORIZATION"] }, { label: "PROJECT", types: ["PROJECT_REGISTER"] }, { label: "DRAWINGS", types: ["DRAWING_SET"] }, { label: "DEPENDENCIES / APPROVALS", types: ["NOC", "OTHER"] }];
  return <section className="panel stage-panel"><div className="stage-heading"><div><span className="eyebrow">STAGE 2 · VERIFY DATA</span><h3>Verify the facts that drive the permit</h3><p>Evidence, current value, verification state, and conflict context stay in one operator job.</p></div><button className="button-secondary" onClick={() => openLegacy("documents")}>Open evidence detail</button></div><div className="fact-groups">{groups.map((group) => <div className="fact-group" key={group.label}><span className="eyebrow">{group.label}</span>{documents.filter((document) => group.types.includes(document.document_type)).slice(0, 4).map((document) => <div className="fact-row" key={document.id}><div><b>{String(document.document_type).replaceAll("_", " ")}</b><small>{document.current_version_id ? "Current version linked" : "No current version"} · Evidence retained</small></div><span className={document.current_version_id ? "status status-approved" : "status status-returned"}>{document.current_version_id ? "VERIFY" : "MISSING"}</span></div>)}{!documents.some((document) => group.types.includes(document.document_type)) && <p className="muted">No source in this business domain yet.</p>}</div>)}</div>{conflicts.length ? <div className="blocker-list"><h3>Conflicts requiring contextual review</h3>{conflicts.slice(0, 5).map((conflict) => <div className="blocker-row" key={conflict.id}><span className="finding-severity">!</span><div><b>{conflict.field_code || conflict.field_name || "Verified field conflict"}</b><small>{conflict.observed_values || conflict.description || "Conflicting observations require a governed decision."}</small></div><button className="button-secondary" onClick={() => openLegacy("conflicts")}>Review</button></div>)}</div> : <div className="empty-inline">No open conflicts are currently returned for this project. Why this value? and lineage remain available from the History/Admin surfaces.</div>}</section>;
}

function WorkspaceStage({ title, description, actionLabel, onOpen }: { title: string; description: string; actionLabel: string; onOpen: () => void }) { return <section className="panel stage-panel"><div className="stage-heading"><div><span className="eyebrow">PERMIT STAGE</span><h3>{title}</h3><p>{description}</p></div><button className="button-primary" onClick={onOpen}>{actionLabel}</button></div><div className="stage-checklist"><div><b>Current state</b><span>Derived from package, preparation, portal, and finding controls</span></div><div><b>Blockers</b><span>Exact reason, owner, evidence, and next route appear when the gate is blocked</span></div><div><b>Safety boundary</b><span>Assisted and read-only controls only; no machine final submission</span></div></div></section>; }

function FinalReviewStage({ project, application, openLegacy }: { project: Project; application?: Application | null; openLegacy: (page: string) => void }) { const checks = ["Current package approved", "PreparationRevision current", "Municipality draft verified", "Attachments persisted", "Grids reconciled", "Precheck clear", "No blocking findings", "Required human reviews complete"]; return <section className="panel stage-panel"><div className="stage-heading"><div><span className="eyebrow">STAGE 5 · FINAL REVIEW & HUMAN SUBMIT</span><h3>Ready for a named human decision</h3><p>PermitOps cannot submit this application. The Final Submitter completes submission in the Municipality portal and records evidence here.</p></div><span className="tag warning">NO MACHINE SUBMIT</span></div><div className="final-review-grid">{checks.map((check) => <div className="check-row" key={check}><span>✓</span><b>{check}</b><small>Gate evidence required</small></div>)}</div><div className="handoff-card"><div><span className="eyebrow">FINAL SUBMISSION HANDOFF</span><h3>{application?.external_request_number || project.project_number}</h3><p>Bind the application identity, current package/hash, PreparationRevision, precheck, and blocking findings to the handoff.</p></div><div className="week45-actions"><button className="button-secondary" onClick={() => openLegacy("package")}>Open readiness</button><button className="button-secondary" onClick={() => openLegacy("confirmation")}>Record human confirmation</button></div></div></section>; }

function AuthorityReviewStage({ project, application, openLegacy }: { project: Project; application?: Application | null; openLegacy: (page: string) => void }) { const [history, setHistory] = useState<any>(null); useEffect(() => { if (application?.id) api<any>(`/api/applications/${application.id}/monitoring-history`).then(setHistory).catch(() => {}); }, [application?.id]); const returned = application?.application_status === "RETURNED"; return <section className="panel stage-panel"><div className="stage-heading"><div><span className="eyebrow">STAGE 6 · AUTHORITY REVIEW</span><h3>{returned ? "Application returned" : "Read-only authority monitoring"}</h3><p>Monitoring stays inside this permit workspace: status, repetition, last checked, next planned check, comments, and read-contract health.</p></div>{returned ? <span className="status status-returned">APPLICATION RETURNED</span> : <span className="tag">READ-ONLY</span>}</div><div className="authority-summary"><div><span>Authority status</span><b>{application?.application_status || "—"}</b></div><div><span>Repetition</span><b>{application?.repetition_count ?? "—"}</b></div><div><span>Last checked</span><b>{fmtDate(application?.last_status_at)}</b></div><div><span>New comments</span><b>{history?.comments?.length ?? history?.comment_observations?.length ?? (returned ? 2 : 0)}</b></div></div>{returned && <div className="authority-alert"><b>Review comments and route corrections.</b><span>This returned state projects the permit into Comments & Corrections; it cannot be manually advanced.</span><button className="button-primary" onClick={() => openLegacy("findings")}>Review comments</button></div>}<p className="muted">External portal reads are bounded and evidence-backed. Manual fallback is visible when the read contract is unavailable.</p></section>; }

function HistoryStage({ project, detail, openLegacy }: { project: Project; detail: any; openLegacy: (page: string) => void }) { const events = detail?.audit || []; return <section className="panel stage-panel"><div className="stage-heading"><div><span className="eyebrow">STAGE 8 · HISTORY / CLOSE</span><h3>Permit evidence timeline</h3><p>Current and historical revisions, packages, prechecks, submission cycles, findings, recurrence, and audit events are separated clearly.</p></div><button className="button-secondary" onClick={() => openLegacy("lineage")}>View technical lineage</button></div><div className="timeline">{events.length ? events.slice(0, 12).map((event: any) => <div className="timeline-row" key={event.id}><span className="timeline-dot"/><div><b>{event.event_type}</b><small>{fmtDate(event.occurred_at)} · <span className="ltr-id">{event.correlation_id || event.id}</span></small></div><span className="tag">{event.entity_type || "AUDIT"}</span></div>) : <EmptyState title="No timeline events" body="Preparation revisions, packages, confirmations, and authority changes will be recorded here." />}</div></section>; }

function Blocker({ text, owner, evidence }: { text: string; owner: string; evidence: string }) { return <div className="blocker-box"><b>BLOCKED · {text}</b><span>Owner: {owner}</span><span>Evidence required: {evidence}</span></div>; }
function EmptyState({ title, body }: { title: string; body: string }) { return <div className="empty-state"><b>{title}</b><p>{body}</p></div>; }
function PageIntro({ kicker, title, description }: { kicker: string; title: string; description: string }) { return <div className="page-intro"><div><span className="eyebrow">{kicker}</span><h2>{title}</h2><p>{description}</p></div></div>; }

export function AdministrationPage({ openLegacy }: { openLegacy: (page: string) => void }) {
  const groups = [
    { title: "Project setup & go-live", description: "Project details, practical AMEC inputs, privacy, volume, questions, support, and safe fallbacks.", links: [["discovery", "Project setup"], ["go-live-readiness", "Go-Live Setup"], ["expansion-foundation", "Expansion foundation"], ["business", "Business case"], ["privacy", "Privacy & data"], ["volume", "Volume baseline"], ["inquiries", "Ministry inquiry"], ["raid", "RAID log"]] },
    { title: "Configuration & rules", description: "Rules, mappings, Municipality setup, package preparation, attachments, and handoff decisions.", links: [["config", "Configuration"], ["thresholds", "Test targets"], ["tier1", "Tier 1 decisions"], ["tier2", "Tier 2 backlog"], ["delivery", "Delivery / data"], ["close", "Go-live setup decision"], ["baseline", "Setup baseline"], ["signoff", "Commercial draft"], ["confirmation", "Confirmation demo"]] },
    { title: "Testing, evidence & audit", description: "Test documents, expected results, analysis, lineage, and control evidence for setup administrators.", links: [["spike", "Test extraction"], ["adjudication", "Expected results"], ["analysis", "Test analysis"], ["corpus", "Test documents"], ["lineage", "Audit & lineage"], ["attachments-grids", "Attachment / grid diagnostics"], ["control-loop", "Control diagnostics"]] },
  ];
  return <div className="workflow-page admin-page"><PageIntro kicker="ADMINISTRATION" title="Setup and system controls" description="Privileged configuration, testing, evidence, and audit surfaces stay available for setup administrators." /><div className="synthetic-note admin-banner">SYNTHETIC DEVELOPMENT / PROTOTYPE TRACK · SAFE FALLBACKS ACTIVE · NO PORTAL WRITES</div><div className="admin-grid">{groups.map((group) => <section className="panel admin-group" key={group.title}><span className="eyebrow">ADMINISTRATION</span><h3>{group.title}</h3><p>{group.description}</p><div className="admin-links">{group.links.map(([id, label]) => <button key={id} onClick={() => openLegacy(id)}>{label}<span>→</span></button>)}</div></section>)}</div></div>;
}

export function WorkflowStageLabel({ stage }: { stage: WorkflowStage }) { return <>{WORKFLOW_STAGES.find((item) => item.code === stage)?.label || stage}</>; }
