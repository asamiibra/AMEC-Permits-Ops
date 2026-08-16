import { useEffect, useState } from "react";
import { api } from "./api";

type HomeProps = { role: string };

const stages = [
  { id: "intake", title: "Intake & Opportunity", description: "Turn a client need into a governed Proposal.", href: "/opportunities", icon: "↗" },
  { id: "contract", title: "Contract & Mobilization", description: "Move an accepted Proposal into controlled activation.", href: "/proposals-contracts", icon: "▤" },
  { id: "design", title: "Design & Technical Delivery", description: "Coordinate engineering deliverables, reviews, and baselines.", href: "/engineering", icon: "⌁" },
  { id: "regulatory", title: "Regulatory & Submissions", description: "Prepare authority evidence, cases, submissions, and findings.", href: "/authority-cases", icon: "◈" },
  { id: "construction", title: "Construction & Post-Approval", description: "Track execution evidence after approval.", href: "/construction", icon: "▥" },
  { id: "completion", title: "Completion & As-Built", description: "Control completion evidence and as-built comparison.", href: "/completion", icon: "✓" },
  { id: "handover", title: "Handover & Closeout", description: "Prepare the final handover package and closeout record.", href: "/handover", icon: "→" },
] as const;

function derivedValue(value: unknown, fallback = "—") {
  return typeof value === "number" ? String(value) : fallback;
}

export function HomePage({ role }: HomeProps) {
  const [work, setWork] = useState<any>(null);
  const [issues, setIssues] = useState<any>(null);
  const [workError, setWorkError] = useState(false);
  const [issuesError, setIssuesError] = useState(false);

  useEffect(() => {
    let live = true;
    Promise.allSettled([
      api<any>("/api/work/summary"),
      api<any>("/api/issues/summary"),
    ]).then(([workResult, issuesResult]) => {
      if (!live) return;
      if (workResult.status === "fulfilled") setWork(workResult.value);
      else setWorkError(true);
      if (issuesResult.status === "fulfilled") setIssues(issuesResult.value);
      else setIssuesError(true);
    });
    return () => { live = false; };
  }, [role]);

  const workSummary = work?.summary || {};
  const issueSummary = issues?.summary || {};
  const workItems = Array.isArray(work?.projection) ? work.projection.slice(0, 3) : Array.isArray(work?.items) ? work.items.slice(0, 3) : [];

  return (
    <div className="home-page" data-testid="home-page">
      <section className="home-hero">
        <div>
          <span className="eyebrow">PROPOSALOPS · AMEC WORKSPACE</span>
          <h2>Home</h2>
          <p>Start with the business flow, then open the canonical workspace that owns the record.</p>
        </div>
        <div className="home-hero-note"><span className="dot green" /> Synthetic prototype · human-controlled workflow</div>
      </section>

      <section className="home-section" aria-labelledby="business-flow-heading">
        <div className="home-section-heading"><div><span className="eyebrow">BUSINESS FLOW</span><h3 id="business-flow-heading">Seven connected stages</h3></div><span className="muted">Open a stage workspace</span></div>
        <div className="home-stage-grid">
          {stages.map((stage) => (
            <a className="home-stage-card" data-testid="home-stage-card" href={stage.href} key={stage.id}>
              <span className="home-stage-icon" aria-hidden="true">{stage.icon}</span>
              <span className="home-stage-title">{stage.title}</span>
              <span className="home-stage-description">{stage.description}</span>
              <span className="home-stage-link">Open workspace →</span>
            </a>
          ))}
        </div>
      </section>

      <section className="home-section" aria-labelledby="finance-heading">
        <div className="home-section-heading"><div><span className="eyebrow">CROSS-FUNCTIONAL</span><h3 id="finance-heading">Financial Flow</h3></div><span className="muted">Parallel to delivery</span></div>
        <div className="home-finance-lane">
          <span className="home-flow-node">Budget &amp; commercial control</span><span className="home-flow-arrow">→</span>
          <a className="home-flow-node home-flow-link" href="/billing">Finance workspace →</a><span className="home-flow-arrow">→</span>
          <span className="home-flow-node">Invoice evidence &amp; approvals</span>
        </div>
      </section>

      <section className="home-widgets" aria-label="Cross-functional summaries">
        <article className="home-widget" data-testid="amec-work-widget">
          <div className="home-widget-heading"><div><span className="eyebrow">AMEC WORK</span><h3>What needs attention</h3></div><a href="/work">Open AMEC Work →</a></div>
          {workError ? <p className="truthful-empty">AMEC Work summary is unavailable. Open the canonical worklist to retry.</p> : work ? <><div className="home-metric-row"><div><strong>{derivedValue(workSummary.needs_action)}</strong><span>Needs action</span></div><div><strong>{derivedValue(workSummary.waiting_review)}</strong><span>Waiting review</span></div><div><strong>{derivedValue(workSummary.blocked)}</strong><span>Blocked</span></div></div>{workItems.length > 0 && <div className="home-mini-list">{workItems.map((item: any) => <a href={item.deep_link || "/work"} key={item.id || item.title}>{item.title || item.action_label || "Open work item"}</a>)}</div>}</> : <p className="loading">Loading AMEC Work summary…</p>}
        </article>
        <article className="home-widget" data-testid="issues-widget">
          <div className="home-widget-heading"><div><span className="eyebrow">ISSUES</span><h3>Exceptions across lifecycle</h3></div><a href="/issues">Open Issues →</a></div>
          {issuesError ? <p className="truthful-empty">Issue summary is unavailable. Open the canonical Issues register to retry.</p> : issues ? <div className="home-metric-row"><div><strong>{derivedValue(issueSummary.open_issues)}</strong><span>Open issues</span></div><div><strong>{derivedValue(issueSummary.blocking_issues)}</strong><span>Blocking</span></div><div><strong>{derivedValue(issueSummary.overdue_unassigned)}</strong><span>Overdue / unassigned</span></div></div> : <p className="loading">Loading Issues summary…</p>}
        </article>
      </section>

      <section className="home-activity-note" aria-label="Recent business activity"><span className="eyebrow">RECENT BUSINESS ACTIVITY</span><p>Activity remains in the canonical stage workspaces and AMEC Work, so Home does not invent a second event history.</p></section>
    </div>
  );
}
