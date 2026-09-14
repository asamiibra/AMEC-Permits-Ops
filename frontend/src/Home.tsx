import { primaryNavigation } from "./featureAvailability";

export function HomePage(_props?: { role?: string }) {
  const modules = primaryNavigation.filter((item) => item.id !== "home");

  return (
    <div className="home-page" data-testid="home-page">
      <header className="home-hero">
        <div>
          <span className="eyebrow">PROPOSALOPS COMMAND CENTER</span>
          <h2>Work across the active ProposalOps modules.</h2>
          <p>
            Start with the business context you need. Home keeps the current
            active business work visible without exposing technical or
            diagnostic routes.
          </p>
        </div>
        <span className="tag">OWNER SHELL</span>
      </header>
      <section className="home-module-grid" aria-label="Active modules">
        {modules.map((module) => (
          <a
            className="home-module-card"
            data-testid="home-module-card"
            href={module.route}
            key={module.id}
          >
            <span className="home-module-icon" aria-hidden="true">
              {module.icon}
            </span>
            <span className="eyebrow">ACTIVE MODULE</span>
            <h3>{module.label}</h3>
            <p>
              {module.id === "opportunity"
                ? "Manage opportunities, proposals, and client tenders."
                : module.id === "contract"
                  ? "Move accepted work into contract and mobilization control."
                  : module.id === "billing"
                    ? "Control invoices, receivables, and collection follow-up."
                    : "Use governed Forms, Reports, Engineering Works, and Definitions."}
            </p>
            <span className="home-module-link">Open module →</span>
          </a>
        ))}
      </section>
    </div>
  );
}
