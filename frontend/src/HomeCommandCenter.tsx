import { useEffect, useMemo, useState } from "react";
import { api } from "./api";
import { Icon } from "./Icon";

type HomeRole = "SYSTEM_ADMIN" | "OWNER_SPONSOR" | "COMMERCIAL_APPROVER" | "RESPONSIBLE_ENGINEER";
type AttentionView = "ALL" | "ACTIONS" | "REVIEWS" | "EXCEPTIONS" | "OVERDUE";

type WorkItem = {
  id: string;
  source_type?: string;
  issue_id?: string | null;
  domain?: string;
  work_type?: string;
  title: string;
  business_context?: string;
  reference?: string;
  stage?: string;
  assigned_team?: string;
  assigned_user?: string | null;
  priority?: string;
  blocking?: boolean;
  due_at?: string | null;
  overdue?: boolean;
  deep_link?: string;
  cta_label?: string;
  status?: string;
};

type IssueItem = {
  id: string;
  display_domain?: string;
  severity?: string;
  blocking?: boolean;
  status?: string;
  owner_team?: string;
  title: string;
  summary?: string;
  affected_record?: { label?: string };
  due_at?: string | null;
  deep_link?: string;
  issue_detail_link?: string;
  resolution_link?: string;
  cta_label?: string;
  actionability?: string;
};

type AttentionItem = {
  id: string;
  kind: "WORK" | "ISSUE";
  source: string;
  state: string;
  title: string;
  context: string;
  reference: string;
  owner: string;
  stage: string;
  priority: string;
  blocking: boolean;
  dueAt?: string | null;
  overdue: boolean;
  deepLink: string;
  ctaLabel: string;
  review: boolean;
  relatedIssue: boolean;
};

type HomeData = {
  work: WorkItem[];
  issues: IssueItem[];
  recentChanges: Array<{ id: string; title: string; detail?: string; when?: string; deep_link?: string }>;
  financeSummary?: { plans?: number; milestones?: number; invoices?: number; payment_receipts?: number };
  invoices: any[];
  content: { forms: number; reports: number; engineeringWorks: number; definitions: number };
};

const rolePersona = (role: string) => role === "COMMERCIAL_APPROVER" ? "BUSINESS_DEVELOPMENT" : role === "RESPONSIBLE_ENGINEER" ? "ENGINEERING" : "OWNER";

const stages = [
  { id: "intake-opportunity", label: "Intake & Opportunity", purpose: "Capture the opportunity and shape the request.", route: "/opportunities", icon: "briefcase" as const },
  { id: "contract-mobilization", label: "Contract & Mobilization", purpose: "Review commercial handoff and contract context.", route: "/proposals-contracts", icon: "contract" as const },
  { id: "design-delivery", label: "Design & Technical Delivery", purpose: "Resolve engineering inputs, revisions, and closeout work.", route: "/engineering", icon: "engineering" as const },
  { id: "regulatory-submissions", label: "Regulatory & Submissions", purpose: "Prepare, review, and monitor regulated submissions.", route: "/permits", icon: "authority" as const },
  { id: "construction-post-approval", label: "Construction & Post-Approval", purpose: "Control approved execution and post-approval evidence.", route: "/construction", icon: "construction" as const },
  { id: "completion-as-built", label: "Completion & As-Built", purpose: "Record verified completion and as-built outcomes.", route: "/completion", icon: "completion" as const },
  { id: "handover-closeout", label: "Handover & Closeout", purpose: "Coordinate handover evidence and service closeout.", route: "/handover", icon: "handover" as const },
];

const viewLabels: Array<[AttentionView, string]> = [["ALL", "All"], ["ACTIONS", "Actions"], ["REVIEWS", "Reviews"], ["EXCEPTIONS", "Exceptions"], ["OVERDUE", "Overdue"]];
const priorityRank: Record<string, number> = { BLOCKING: 0, CRITICAL: 0, MAJOR: 1, HIGH: 1, NORMAL: 2, MEDIUM: 2, LOW: 3 };

function readable(value: unknown) {
  return String(value || "Recorded").replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function isReview(item: AttentionItem) {
  return item.review || /REVIEW|REVIEW|COMMENT|VERIFY/i.test(`${item.state} ${item.stage} ${item.title}`);
}

function isOverdue(item: AttentionItem) {
  return item.overdue || Boolean(item.dueAt && new Date(item.dueAt).getTime() < Date.now());
}

function matchesView(item: AttentionItem, view: AttentionView) {
  if (view === "ALL") return true;
  if (view === "ACTIONS") return item.kind === "WORK" && !item.blocking && !isReview(item);
  if (view === "REVIEWS") return isReview(item);
  if (view === "EXCEPTIONS") return item.kind === "ISSUE" || item.blocking;
  return isOverdue(item);
}

function formatDue(value?: string | null, overdue = false) {
  if (overdue) return "Overdue";
  if (!value) return "No due date";
  const days = Math.ceil((new Date(value).getTime() - Date.now()) / 86400000);
  return days <= 0 ? "Due today" : days === 1 ? "Due tomorrow" : `Due in ${days} days`;
}

function normalizeWork(item: WorkItem): AttentionItem {
  const review = /REVIEW|COMMENT|VERIFY/i.test(`${item.work_type || ""} ${item.stage || ""} ${item.title}`);
  return {
    id: `work-${item.id}`,
    kind: "WORK",
    source: readable(item.domain || item.source_type),
    state: item.issue_id ? `ISSUE · ${item.blocking ? "BLOCKED" : review ? "REVIEW" : readable(item.status || "OPEN")}` : item.blocking ? "BLOCKED" : review ? "REVIEW" : readable(item.status || "OPEN"),
    title: item.title,
    context: item.business_context || "Canonical work item requiring a next action.",
    reference: item.reference || item.source_type || "Shared work",
    owner: item.assigned_team || item.assigned_user || "Assigned team",
    stage: item.stage || "Canonical workspace",
    priority: readable(item.priority || "NORMAL"),
    blocking: Boolean(item.blocking),
    dueAt: item.due_at,
    overdue: Boolean(item.overdue),
    deepLink: item.deep_link || "/work",
    ctaLabel: item.cta_label || "Open work",
    review,
    relatedIssue: Boolean(item.issue_id),
  };
}

function normalizeIssue(item: IssueItem): AttentionItem {
  const review = String(item.actionability || item.severity || "").toUpperCase().includes("REVIEW");
  return {
    id: `issue-${item.id}`,
    kind: "ISSUE",
    source: readable(item.display_domain || "Issue"),
    state: item.blocking ? "BLOCKING" : readable(item.severity || item.status || "OPEN"),
    title: item.title,
    context: item.summary || "Issue context requires review in its owning workspace.",
    reference: item.affected_record?.label || "Issue record",
    owner: item.owner_team || "Assigned team",
    stage: "Issue context",
    priority: readable(item.severity || "NORMAL"),
    blocking: Boolean(item.blocking),
    dueAt: item.due_at,
    overdue: Boolean(item.due_at && new Date(item.due_at).getTime() < Date.now()),
    deepLink: item.deep_link || item.issue_detail_link || item.resolution_link || "/issues",
    ctaLabel: item.cta_label || "Open issue",
    review,
    relatedIssue: true,
  };
}

function currencySummary(items: any[]) {
  const grouped = new Map<string, number>();
  items.forEach((item) => {
    const amount = Number(item?.receivable?.outstanding_amount);
    const currency = String(item?.revision?.currency || "").trim().toUpperCase();
    if (Number.isFinite(amount) && currency) grouped.set(currency, (grouped.get(currency) || 0) + amount);
  });
  return Array.from(grouped.entries()).map(([currency, amount]) => `${amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${currency}`).join(" · ");
}

export function HomeCommandCenter({ role }: { role: string }) {
  const [data, setData] = useState<HomeData | null>(null);
  const [loading, setLoading] = useState(true);
  const [errors, setErrors] = useState<string[]>([]);
  const [view, setView] = useState<AttentionView>("ALL");

  useEffect(() => {
    let live = true;
    setLoading(true);
    const persona = rolePersona(role);
    Promise.allSettled([
      api<any>("/api/work"),
      api<any>(`/api/issues?persona=${persona}`),
      api<any>("/api/billing/summary"),
      api<any>("/api/billing/invoices"),
      api<any>("/api/master-content?content_type=FORM"),
      api<any>("/api/master-content?content_type=REPORT"),
      api<any>("/api/master-content?content_type=ENGINEERING_WORK"),
      api<any>("/api/definitions"),
    ]).then((results) => {
      if (!live) return;
      const [work, issues, financeSummary, invoices, forms, reports, engineeringWorks, definitions] = results;
      const failures = results.map((result, index) => result.status === "rejected" ? `${["work", "issues", "finance", "invoices", "forms", "reports", "engineering works", "definitions"][index]} unavailable` : "").filter(Boolean);
      setErrors(failures);
      const workValue = work.status === "fulfilled" ? work.value : {};
      const issueValue = issues.status === "fulfilled" ? issues.value : {};
      setData({
        work: Array.isArray(workValue.items) ? workValue.items : [],
        issues: Array.isArray(issueValue.issues) ? issueValue.issues : [],
        recentChanges: Array.isArray(workValue.recent_changes) ? workValue.recent_changes : [],
        financeSummary: financeSummary.status === "fulfilled" ? financeSummary.value : undefined,
        invoices: invoices.status === "fulfilled" && Array.isArray(invoices.value.items) ? invoices.value.items : [],
        content: {
          forms: forms.status === "fulfilled" && Array.isArray(forms.value) ? forms.value.length : 0,
          reports: reports.status === "fulfilled" && Array.isArray(reports.value) ? reports.value.length : 0,
          engineeringWorks: engineeringWorks.status === "fulfilled" && Array.isArray(engineeringWorks.value) ? engineeringWorks.value.length : 0,
          definitions: definitions.status === "fulfilled" && Array.isArray(definitions.value) ? definitions.value.length : 0,
        },
      });
      setLoading(false);
    });
    return () => { live = false; };
  }, [role]);

  const attention = useMemo(() => {
    if (!data) return [];
    const work = data.work.map(normalizeWork);
    const coveredIssues = new Set(data.work.map((item) => item.issue_id).filter(Boolean));
    const issues = data.issues.filter((item) => !coveredIssues.has(item.id)).map(normalizeIssue);
    return [...work, ...issues].sort((left, right) => {
      const urgency = Number(right.blocking) - Number(left.blocking) || Number(isOverdue(right)) - Number(isOverdue(left));
      if (urgency) return urgency;
      return (priorityRank[left.priority.toUpperCase()] ?? 3) - (priorityRank[right.priority.toUpperCase()] ?? 3);
    });
  }, [data]);

  const visibleAttention = useMemo(() => attention.filter((item) => matchesView(item, view)).slice(0, 25), [attention, view]);
  const count = (target: AttentionView) => attention.filter((item) => matchesView(item, target)).length;
  const outstanding = data ? currencySummary(data.invoices) : "";
  const invoicesDue = data?.invoices.filter((item) => item.stage === "NEED_ACTION" || item.receivable?.due_date).length || 0;
  const paymentsToReview = data?.invoices.filter((item) => item.stage === "AUTHORITY_REVIEW" || ["REVIEW", "PARTIALLY_PAID"].includes(String(item.receivable?.state || "").toUpperCase())).length || 0;

  return <div className="home-command-center" data-testid="home-command-center">
    <header className="home-header">
      <div><span className="eyebrow">HOME</span><h2>Home</h2><p>Start with what needs attention, then open the canonical workspace that owns the record.</p></div>
    </header>

    <section className="home-section home-flow-section" aria-labelledby="home-flow-heading">
      <div className="home-section-heading"><div><span className="eyebrow">BUSINESS FLOW</span><h3 id="home-flow-heading">Seven places where canonical work happens</h3></div><span className="home-section-note">Navigation only · no state changes</span></div>
      <div className="home-stage-grid">{stages.map((stage, index) => <a className="home-stage-card" href={stage.route} key={stage.id}><span className="home-stage-icon"><Icon name={stage.icon} size={18} /></span><span className="home-stage-number">0{index + 1}</span><h4>{stage.label}</h4><p>{stage.purpose}</p><span className="home-stage-link">Open workspace <Icon name="arrow-up-right" size={14} /></span></a>)}</div>
    </section>

    <section className="home-section home-attention-section" aria-labelledby="home-attention-heading">
      <div className="home-section-heading"><div><span className="eyebrow">WHAT NEEDS ATTENTION</span><h3 id="home-attention-heading">Prioritized work and lifecycle exceptions</h3><p className="home-section-description">Work and Issues stay distinguishable while sharing one role-scoped action surface.</p></div><a className="text-button" href="/work">Open full AMEC Work <Icon name="arrow-up-right" size={14} /></a></div>
      <div className="home-attention-counts" aria-label="Attention summary counts">{([["ALL", "Open"], ["ACTIONS", "Actions"], ["REVIEWS", "Reviews"], ["EXCEPTIONS", "Blocked / Exceptions"], ["OVERDUE", "Overdue"]] as Array<[AttentionView, string]>).map(([key, label]) => <div key={key}><span>{label}</span><strong>{loading ? "—" : count(key)}</strong></div>)}</div>
      <div className="home-attention-toolbar" role="group" aria-label="Attention views">{viewLabels.map(([key, label]) => <button key={key} className={view === key ? "filter active" : "filter"} aria-pressed={view === key} onClick={() => setView(key)}>{label}</button>)}</div>
      {errors.length > 0 && <div className="home-bounded-warning" role="status">Some Home projections are unavailable: {errors.join(", ")}. The underlying workspaces remain available.</div>}
      {loading ? <div className="home-empty-state" role="status">Loading authorized attention…</div> : visibleAttention.length ? <div className="home-attention-list">{visibleAttention.map((item) => <article className="home-attention-row" key={item.id}><div className="home-attention-mark"><Icon name={item.kind === "ISSUE" ? "issues" : item.blocking ? "alert" : "work"} size={17} /></div><div className="home-attention-main"><div className="home-attention-meta"><span className="home-source-badge">{item.kind}</span><span>{item.source}</span><span>{item.state}</span>{isOverdue(item) && <span className="home-overdue">{formatDue(item.dueAt, true)}</span>}</div><h4>{item.title}</h4><p>{item.context}</p><small>{item.reference} · {item.owner} · {item.stage}</small></div><a className="button-secondary home-attention-action" href={item.deepLink}>{item.ctaLabel} <Icon name="arrow-up-right" size={14} /></a></article>)}</div> : <div className="home-empty-state"><b>You&apos;re all caught up</b><p>No current actions, reviews, exceptions, or overdue work in your authorized scope.</p></div>}
    </section>

    <div className="home-support-grid">
      <section className="home-section home-finance-section" aria-labelledby="home-finance-heading"><div className="home-section-heading"><div><span className="eyebrow">FINANCE</span><h3 id="home-finance-heading">Financial follow-up</h3></div><a className="text-button" href="/billing">Open Finance <Icon name="arrow-up-right" size={14} /></a></div>{data?.financeSummary ? <div className="home-metric-list"><div><span>Outstanding receivables</span><strong>{outstanding || "No issued balance"}</strong></div><div><span>Invoices due</span><strong>{invoicesDue}</strong></div><div><span>Payments to review</span><strong>{paymentsToReview}</strong></div><div><span>Settlement</span><strong>Canonical workspace</strong></div></div> : <div className="home-empty-state"><b>No current financial follow-up</b><p>Finance data is unavailable for this authorized scope.</p></div>}<small className="home-contract-note">Amounts are shown only when the canonical invoice projection provides a currency; settlement remains separate from invoice status.</small></section>
      <section className="home-section home-content-section" aria-labelledby="home-content-heading"><div className="home-section-heading"><div><span className="eyebrow">CONTENT LIBRARY</span><h3 id="home-content-heading">Shared governed content</h3></div><a className="text-button" href="/dashboard">Open Content Library <Icon name="arrow-up-right" size={14} /></a></div>{data ? <div className="home-content-grid"><div><Icon name="library" size={17} /><span>Forms</span><strong>{data.content.forms}</strong></div><div><Icon name="library" size={17} /><span>Reports</span><strong>{data.content.reports}</strong></div><div><Icon name="engineering" size={17} /><span>Engineering Works</span><strong>{data.content.engineeringWorks}</strong></div><div><Icon name="help" size={17} /><span>Definitions</span><strong>{data.content.definitions}</strong></div></div> : <div className="home-empty-state"><b>Content Library unavailable</b><p>Open the governed library to inspect the current bounded state.</p></div>}<small className="home-contract-note">Checklist remains governed as a Form; Home exposes discoverability only.</small></section>
    </div>

    <section className="home-section home-activity-section" aria-labelledby="home-activity-heading"><div className="home-section-heading"><div><span className="eyebrow">RECENT BUSINESS ACTIVITY</span><h3 id="home-activity-heading">What recently happened</h3></div><span className="home-section-note">Role-scoped canonical work changes</span></div>{data?.recentChanges.length ? <div className="home-activity-list">{data.recentChanges.slice(0, 5).map((item) => <a className="home-activity-row" href={item.deep_link || "/work"} key={item.id}><span className="home-activity-dot" /><span><b>{item.title}</b><small>{item.detail || "Recorded in the canonical work projection"}</small></span><time>{item.when ? new Date(item.when).toLocaleDateString() : "Recent"}</time><Icon name="arrow-up-right" size={14} /></a>)}</div> : <div className="home-empty-state"><b>No recent activity is available</b><p>The canonical work projection returned no bounded business changes for this scope.</p></div>}</section>
  </div>;
}
