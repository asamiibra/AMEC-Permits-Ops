import { Icon } from "./Icon";
import { primaryNavigation, type PrimaryNavigationItem } from "./featureAvailability";

export function HomePage(_props?: { role?: string }) {
  const foundation = primaryNavigation.find((item) => item.id === "content-library");
  const workflow = primaryNavigation.filter((item) => ["opportunity", "contract", "billing"].includes(item.id));
  if (!foundation) return null;

  return (
    <div className="home-page" data-testid="home-page">
      <header className="home-hero">
        <div>
          <span className="eyebrow">HOME · PROPOSALOPS WORKSPACE</span>
          <h2>Keep work moving from source to cash.</h2>
          <p>
            Start with governed content, move through the commercial workflow,
            and keep every protected decision with the responsible human.
          </p>
        </div>
        <span className="home-safety-note"><Icon name="shield" size={15} /> Human review remains required</span>
      </header>

      <section className="home-foundation" aria-labelledby="home-foundation-title">
        <div className="home-section-heading">
          <div><span className="eyebrow">FOUNDATION</span><h3 id="home-foundation-title">Content Library</h3></div>
          <span className="home-section-note">Trusted source material for every module</span>
        </div>
        <div className="home-foundation-row">
          <span className="home-module-icon"><Icon name={foundation.icon} size={21} /></span>
          <div><strong>Governed content, ready for reuse</strong><p>Browse Forms, Reports, Engineering Works, and Definitions with currentness and authority visible.</p></div>
          <a className="home-module-link" href={foundation.route}>Open Content Library <Icon name="arrow-right" size={15} /></a>
        </div>
      </section>

      <section className="home-workflow" aria-labelledby="home-workflow-title">
        <div className="home-section-heading">
          <div><span className="eyebrow">WORKFLOW</span><h3 id="home-workflow-title">From Proposal to Billing</h3></div>
          <span className="home-section-note">Separate stages, explicit handoffs</span>
        </div>
        <div className="home-workflow-grid">
          {workflow.map((module, index) => <WorkflowCard key={module.id} module={module} index={index} />)}
        </div>
      </section>
    </div>
  );
}

function WorkflowCard({ module, index }: { module: PrimaryNavigationItem; index: number }) {
  const description = module.id === "opportunity"
    ? "Shape opportunities, proposals, and client tenders."
    : module.id === "contract"
      ? "Turn accepted work into controlled contract mobilization."
      : "Review invoices, receivables, and collection follow-up."
  return <>
    <a className="home-module-card" data-testid="home-module-card" href={module.route}>
      <span className="home-module-icon"><Icon name={module.icon} size={21} /></span>
      <span className="eyebrow">{String(index + 1).padStart(2, "0")} · ACTIVE MODULE</span>
      <h3>{module.label}</h3>
      <p>{description}</p>
      <span className="home-module-link">Open module <Icon name="arrow-up-right" size={14} /></span>
    </a>
    {index < 2 && <span className="home-workflow-arrow" aria-hidden="true"><Icon name="arrow-right" size={17} /></span>}
  </>;
}
