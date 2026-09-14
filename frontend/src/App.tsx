import { useEffect, useState } from "react";
import { api } from "./api";
import { OpportunitiesPage } from "./Opportunities";
import { ContractMobilizationPage } from "./AdministrationOwner";
import { CurrentDashboard } from "./Dashboard";
import { BillingInvoicePage } from "./BillingInvoice";
import { HomePage } from "./Home";
import { AmecLogo } from "./AmecLogo";
import { browserAuthMode } from "./auth";
import { readDemoRole } from "./rebrand";
import { classifyPublicRoute, type PublicPage } from "./domainOwnershipRoutes";
import { getPrimaryNavigation } from "./featureAvailability";
import "./dashboard.css";
import "./billing-invoice.css";
import "./admin-owner.css";

type AuthSession = {
  authenticated: boolean;
  identity: {
    user_id: string | null;
    tenant_id: string | null;
    object_id: string | null;
    role: string;
  };
};

type DemoRole = "SYSTEM_ADMIN" | "OWNER_SPONSOR" | "COMMERCIAL_APPROVER" | "RESPONSIBLE_ENGINEER";

function pageFromPath(): PublicPage {
  return classifyPublicRoute(window.location.pathname).page;
}

export default function App() {
  const [page, setPage] = useState<PublicPage>(pageFromPath);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [role, setRole] = useState<string>(() => (
    browserAuthMode() === "DEV_HEADER" ? readDemoRole() : "OWNER_SPONSOR"
  ));
  const [authSession, setAuthSession] = useState<AuthSession | null>(null);

  useEffect(() => {
    document.documentElement.lang = "en";
    document.documentElement.dir = "ltr";
    document.body.dir = "ltr";
  }, []);

  useEffect(() => {
    if (browserAuthMode() === "DEV_HEADER") {
      sessionStorage.setItem("proposalops-role", role);
      return;
    }
    sessionStorage.removeItem("proposalops-role");
  }, [role]);

  useEffect(() => {
    if (browserAuthMode() !== "ENTRA") return;
    api<AuthSession>("/api/auth/session")
      .then((session) => {
        setAuthSession(session);
        setRole(session.identity.role);
      })
      .catch(() => setAuthSession(null));
  }, []);

  useEffect(() => {
    const syncLocation = () => {
      const route = classifyPublicRoute(window.location.pathname);
      if (!route.allowed) {
        window.history.replaceState({}, "", "/home");
      }
      setPage(route.page);
    };
    syncLocation();
    window.addEventListener("popstate", syncLocation);
    return () => window.removeEventListener("popstate", syncLocation);
  }, []);

  const navigate = (id: string) => {
    const item = getPrimaryNavigation(role).find((candidate) => candidate.id === id);
    if (!item) {
      window.history.replaceState({}, "", "/home");
      setPage("home");
      return;
    }
    setMobileNavOpen(false);
    window.history.pushState({}, "", item.route);
    setPage(item.page);
    window.dispatchEvent(new PopStateEvent("popstate"));
  };

  const visibleNavigation = getPrimaryNavigation(role);
  const title = visibleNavigation.find((item) => item.page === page)?.label || "Home";
  const moduleRole = role as DemoRole;

  return (
    <div
      className="app-shell"
      data-g9-authenticated={authSession?.authenticated ? "true" : "false"}
      data-g9-auth-tenant={authSession?.identity.tenant_id || ""}
      data-g9-auth-object-id={authSession?.identity.object_id || ""}
      data-g9-auth-role={authSession?.identity.role || ""}
    >
      <aside className="sidebar">
        <div className="brand">
          <AmecLogo size="sm" className="sidebar-amec-logo" />
          <div className="brand-product">
            <b>AMEC Works</b>
            <small>PROPOSALOPS WORKSPACE</small>
          </div>
        </div>
        <div className="office-pill">
          <span className="dot" />
          <span>AMEC Engineering</span>
          <br />
          <small>QEC-DOHA · SYNTHETIC DEV</small>
        </div>
        <nav aria-label="Primary navigation">
          {visibleNavigation.map((item) => (
            <button
              key={item.id}
              type="button"
              aria-label={item.label}
              className={page === item.page ? "nav-item active" : "nav-item"}
              onClick={() => navigate(item.id)}
            >
              <span className="nav-icon">{item.icon}</span>
              <span>{item.label}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-foot">
          <span className="lock">▣</span>
          <span>
            <b>Safe boundary</b>
            <small>Synthetic data only<br />No portal writes<br />No closure automation</small>
          </span>
        </div>
      </aside>
      <main className="main">
        {mobileNavOpen && (
          <div className="mobile-nav-backdrop" role="presentation" onClick={() => setMobileNavOpen(false)}>
            <aside className="mobile-nav-drawer" role="dialog" aria-modal="true" aria-label="Mobile primary navigation" onClick={(event) => event.stopPropagation()}>
              <div className="mobile-nav-drawer-head">
                <div><b>AMEC Works</b><small>PROPOSALOPS WORKSPACE</small></div>
                <button className="mobile-nav-close" type="button" aria-label="Close navigation" onClick={() => setMobileNavOpen(false)}>×</button>
              </div>
              <nav aria-label="Mobile primary navigation">
                {visibleNavigation.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    aria-label={item.label}
                    className={page === item.page ? "nav-item active" : "nav-item"}
                    onClick={() => navigate(item.id)}
                  >
                    <span className="nav-icon">{item.icon}</span>
                    <span>{item.label}</span>
                  </button>
                ))}
              </nav>
            </aside>
          </div>
        )}
        <header className="topbar">
          <div className="topbar-heading">
            <button className="mobile-nav-trigger" type="button" aria-label="Open navigation" aria-expanded={mobileNavOpen} onClick={() => setMobileNavOpen(true)} />
            <AmecLogo size="sm" className="mobile-topbar-amec-logo" />
            <div>
              <span className="eyebrow">AMEC WORKSPACE</span>
              <h1>{title}</h1>
            </div>
          </div>
          <div className="top-actions">
            <span className="env-chip">
              <span className="dot green" /> SYNTHETIC PROTOTYPE
            </span>
            {browserAuthMode() === "DEV_HEADER" && (
              <label aria-label="Demo as" className="role-switcher">
                Demo as
                <select
                  aria-label="Persona"
                  value={role}
                  onChange={(event) => setRole(event.target.value)}
                >
                  <option value="SYSTEM_ADMIN">Owner</option>
                  <option value="COMMERCIAL_APPROVER">Business Development</option>
                  <option value="RESPONSIBLE_ENGINEER">Engineering</option>
                </select>
              </label>
            )}
            <button className="avatar" type="button" aria-label="Current user">SA</button>
          </div>
        </header>
        <div className="content">
          <div className="synthetic-note compact-environment-badge">
            SYNTHETIC PROTOTYPE · NO PORTAL WRITES · HUMAN SUBMISSION REQUIRED
          </div>
          {page === "home" && <HomePage />}
          {page === "opportunities" && <OpportunitiesPage role={moduleRole} />}
          {page === "contract-mobilization" && <ContractMobilizationPage />}
          {page === "billing" && <BillingInvoicePage />}
          {page === "content-library" && <CurrentDashboard role={role} />}
        </div>
      </main>
    </div>
  );
}
