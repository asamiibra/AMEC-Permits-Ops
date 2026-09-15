import { useEffect, useState } from "react";
import { ApiError, api } from "./api";
import { OpportunitiesPage } from "./Opportunities";
import { ContractMobilizationPage } from "./AdministrationOwner";
import { AdministrationOwnerPage } from "./AdministrationOwner";
import { CurrentDashboard } from "./Dashboard";
import { BillingInvoicePage } from "./BillingInvoice";
import { HomeCommandCenter } from "./HomeCommandCenter";
import { AMECWorkPage } from "./AMECWork";
import { ProductDeliveryPage } from "./ProductDelivery";
import { OwnerDecisionCenterPage } from "./OwnerDecisionCenter";
import { PersonaIssueDetailPage, PersonaIssuesPage, PersonaNotificationsPage, type Persona as IssuePersona } from "./PersonaIssuesNotifications";
import { NotificationBell } from "./NotificationBell";
import { AmecLogo } from "./AmecLogo";
import { browserAuthMode, getSignedInAccountIdentity, signOut } from "./auth";
import { readDemoRole } from "./rebrand";
import { classifyPublicRoute, type PublicPage } from "./domainOwnershipRoutes";
import { getPrimaryNavigation, isSupportedShellRole, personaForRole } from "./featureAvailability";
import { EnvironmentBlockedSurface, environmentIndicator, isSyntheticEnvironment, runtimeEnvironment } from "./environment";
import { AuthzSurface, type AuthzSurfaceState } from "./AuthFailureSurface";
import "./dashboard.css";
import "./billing-invoice.css";
import "./admin-owner.css";
import "./product-surface.css";

type AuthSession = {
  authenticated: boolean;
  identity: {
    user_id: string | null;
    tenant_id: string | null;
    object_id: string | null;
    display_name: string | null;
    preferred_username: string | null;
    role: string;
  };
};

type DemoRole = "SYSTEM_ADMIN" | "OWNER_SPONSOR" | "PROCESS_CHAMPION" | "COMMERCIAL_APPROVER" | "RESPONSIBLE_ENGINEER";
type AuthzState = AuthzSurfaceState | "AUTHZ_AUTHORIZED";

export function userInitials(displayName: string | null | undefined, preferredUsername: string | null | undefined): string {
  const name = displayName?.trim();
  if (name) {
    const parts = name.split(/\s+/).filter(Boolean);
    if (parts.length > 1) return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
    return parts[0].slice(0, 2).toUpperCase();
  }
  const username = preferredUsername?.trim().split("@")[0] || "";
  if (username) return username.slice(0, 2).toUpperCase();
  return "•";
}

function roleLabel(role: string | null | undefined): string {
  return (role || "Role pending")
    .toLowerCase()
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function pageFromPath(): PublicPage {
  return classifyPublicRoute(window.location.pathname).page;
}

export default function App() {
  const environment = runtimeEnvironment();
  const [page, setPage] = useState<PublicPage>(pageFromPath);
  const [currentPath, setCurrentPath] = useState(() => window.location.pathname);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [accountMenuOpen, setAccountMenuOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const [signOutError, setSignOutError] = useState<string | null>(null);
  const [role, setRole] = useState<string>(() => (
    browserAuthMode() === "DEV_HEADER" ? readDemoRole() : ""
  ));
  const [authSession, setAuthSession] = useState<AuthSession | null>(null);
  const [accountIdentity, setAccountIdentity] = useState<{ displayName: string | null; preferredUsername: string | null } | null>(null);
  const [authzState, setAuthzState] = useState<AuthzState>(() => (
    browserAuthMode() === "DEV_HEADER" ? "AUTHZ_AUTHORIZED" : "AUTHZ_LOADING"
  ));

  useEffect(() => {
    document.documentElement.lang = "en";
    document.documentElement.dir = "ltr";
    document.body.dir = "ltr";
    try {
      [
        "permitops.locale",
        "permitops-locale",
        "permitops-language",
        "language",
        "locale",
      ].forEach((key) => window.localStorage.removeItem(key));
    } catch {
      // The application remains English/LTR when browser storage is unavailable.
    }
  }, []);

  useEffect(() => {
    if (!accountMenuOpen && !mobileNavOpen) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      setAccountMenuOpen(false);
      setMobileNavOpen(false);
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [accountMenuOpen, mobileNavOpen]);

  useEffect(() => {
    if (browserAuthMode() === "DEV_HEADER") {
      sessionStorage.setItem("proposalops-role", role);
      return;
    }
    sessionStorage.removeItem("proposalops-role");
  }, [role]);

  const loadSession = () => {
    if (browserAuthMode() !== "ENTRA") return;
    setAuthzState("AUTHZ_LOADING");
    void getSignedInAccountIdentity()
      .then((account) => setAccountIdentity(account))
      .catch(() => setAccountIdentity(null));
    void api<AuthSession>("/api/auth/session")
      .then((session) => {
        if (!session.authenticated || !session.identity.role?.trim()) {
          throw new ApiError("The AMEC System session did not contain an application role.", 403, "/api/auth/session");
        }
        setAuthSession(session);
        setRole(session.identity.role);
        setAuthzState(isSupportedShellRole(session.identity.role) ? "AUTHZ_AUTHORIZED" : "AUTHZ_UNSUPPORTED_ROLE");
      })
      .catch((error: unknown) => {
        setAuthSession(null);
        setAccountIdentity(null);
        setRole("");
        const status = error instanceof ApiError ? error.status : 0;
        setAuthzState(status === 403 ? "AUTHZ_UNMAPPED" : status === 401 ? "AUTHZ_UNAUTHENTICATED" : "AUTHZ_ERROR");
      });
  };

  useEffect(() => {
    loadSession();
  }, []);

  useEffect(() => {
    const syncLocation = () => {
      const route = classifyPublicRoute(window.location.pathname);
      const administrationDenied = route.page === "administration" && role !== "SYSTEM_ADMIN";
      if (!route.allowed || administrationDenied) {
        window.history.replaceState({}, "", "/home");
      }
      setPage(administrationDenied ? "home" : route.page);
      setCurrentPath(window.location.pathname);
    };
    syncLocation();
    window.addEventListener("popstate", syncLocation);
    return () => window.removeEventListener("popstate", syncLocation);
  }, [role]);

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
  const title = page === "work" ? "My Work"
    : page === "project-delivery" ? "Projects & Delivery"
      : page === "issues" ? "Issues"
        : page === "notifications" ? "Notifications"
          : page === "owner-decisions" ? "Owner Decisions"
            : page === "administration" ? "Administration"
              : visibleNavigation.find((item) => item.page === page)?.label || "Home";
  const moduleRole = role as DemoRole;
  const displayName = authSession?.identity.display_name?.trim() || accountIdentity?.displayName?.trim() || "";
  const preferredUsername = authSession?.identity.preferred_username?.trim() || accountIdentity?.preferredUsername?.trim() || "";
  const identityLabel = displayName || preferredUsername || (browserAuthMode() === "DEV_HEADER" ? "Local development user" : "Signed-in user");
  const initials = userInitials(displayName, preferredUsername);

  const handleSignOut = async () => {
    setSignOutError(null);
    setSigningOut(true);
    try {
      await signOut();
      setAccountMenuOpen(false);
    } catch (error) {
      setSigningOut(false);
      setSignOutError(error instanceof Error ? error.message : "Sign out could not be completed.");
    }
  };

  if (environment === "UNKNOWN") return <EnvironmentBlockedSurface />;

  if (authzState !== "AUTHZ_AUTHORIZED") {
    return (
      <AuthzSurface
        state={authzState}
        identity={displayName || preferredUsername || undefined}
        role={authSession?.identity.role ? roleLabel(authSession.identity.role) : undefined}
        onRetry={authzState === "AUTHZ_UNMAPPED" || authzState === "AUTHZ_UNSUPPORTED_ROLE" ? undefined : loadSession}
        onSignOut={authzState === "AUTHZ_UNMAPPED" || authzState === "AUTHZ_UNSUPPORTED_ROLE" ? handleSignOut : undefined}
        busy={signingOut}
      />
    );
  }

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
            <b>AMEC System</b>
            <small>PROPOSALOPS WORKSPACE</small>
          </div>
        </div>
        <div className="office-pill">
          <span className="dot" />
          <span>AMEC Engineering</span>
          <br />
          {environment !== "PRODUCTION" && <small>QEC-DOHA · SYNTHETIC COMMISSIONING</small>}
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
            {environment === "PRODUCTION"
              ? <small>No portal writes<br />Human-controlled closure</small>
              : <small>Synthetic data only<br />No portal writes<br />No closure automation</small>}
          </span>
        </div>
      </aside>
      <main className="main">
        {mobileNavOpen && (
          <div className="mobile-nav-backdrop" role="presentation" onClick={() => setMobileNavOpen(false)}>
            <aside className="mobile-nav-drawer" role="dialog" aria-modal="true" aria-label="Mobile primary navigation" onClick={(event) => event.stopPropagation()}>
              <div className="mobile-nav-drawer-head">
                <div><b>AMEC System</b><small>PROPOSALOPS WORKSPACE</small></div>
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
              <span className="eyebrow">AMEC SYSTEM WORKSPACE</span>
              <h1>{title}</h1>
            </div>
          </div>
          <div className="top-actions">
              <span className="env-chip" data-runtime-environment={environment}>
              <span className="dot green" /> {environmentIndicator(environment)}
            </span>
            {browserAuthMode() === "DEV_HEADER" && (
              <label aria-label="Demo as" className="role-switcher">
                Demo as
                <select
                  aria-label="Persona"
                  value={role}
                  onChange={(event) => setRole(event.target.value)}
                >
                  <option value="OWNER_SPONSOR">Owner</option>
                  <option value="SYSTEM_ADMIN">System Admin</option>
                  <option value="PROCESS_CHAMPION">Business Development</option>
                  <option value="COMMERCIAL_APPROVER">Business Development · Commercial Approver</option>
                  <option value="RESPONSIBLE_ENGINEER">Engineering</option>
                </select>
              </label>
            )}
            <a className="header-link" href="/issues">Issues</a>
            <a className="header-link" href="/notifications">Notifications</a>
            <NotificationBell persona={issuePersonaForRole(role)} />
            <div className="account-control">
              <button
                className="avatar"
                type="button"
                aria-label={`Account: ${identityLabel}`}
                aria-expanded={accountMenuOpen}
                aria-haspopup="menu"
                aria-controls="account-menu"
                onClick={() => setAccountMenuOpen((open) => !open)}
              >
                {initials}
              </button>
              {accountMenuOpen && (
                <section className="account-menu" id="account-menu" role="menu" aria-label="Signed-in account">
                  <div className="account-menu-heading">
                    <span className="eyebrow">SIGNED-IN IDENTITY</span>
                    <strong>{identityLabel}</strong>
                    {preferredUsername && preferredUsername !== displayName && <small>{preferredUsername}</small>}
                  </div>
                  <div className="account-menu-row">
                    <span>Authentication</span>
                    <b>{browserAuthMode() === "ENTRA" ? "Microsoft Entra ID" : "Local development"}</b>
                  </div>
                  <div className="account-menu-row">
                    <span>AMEC System role</span>
                    <b>{roleLabel(authSession?.identity.role || (browserAuthMode() === "DEV_HEADER" ? role : ""))}</b>
                  </div>
                  {role === "SYSTEM_ADMIN" && (
                    <a className="account-menu-signout" role="menuitem" href="/admin" onClick={() => setAccountMenuOpen(false)}>
                      Administration
                    </a>
                  )}
                  {signOutError && <p className="account-menu-error" role="alert">{signOutError}</p>}
                  <button className="account-menu-signout" type="button" role="menuitem" onClick={() => void handleSignOut()} disabled={signingOut}>
                    {signingOut ? "Signing out…" : "Sign out"}
                  </button>
                </section>
              )}
            </div>
          </div>
        </header>
        <div className="content">
          <div className="synthetic-note compact-environment-badge">
            {isSyntheticEnvironment(environment)
              ? "SYNTHETIC OWNER-UAT · NO PRODUCTION WRITES · HUMAN SUBMISSION REQUIRED"
              : "PRODUCTION · NO AUTOMATED EXTERNAL SUBMISSION · HUMAN CONTROL REQUIRED"}
          </div>
          <ContextualNavigation page={page} currentPath={currentPath} />
          {page === "home" && <HomeCommandCenter role={role} />}
          {page === "work" && <AMECWorkPage />}
          {page === "opportunities" && <OpportunitiesPage role={moduleRole} />}
          {page === "contract-mobilization" && <ContractMobilizationPage />}
          {page === "project-delivery" && <ProductDeliveryPage />}
          {page === "billing" && <BillingInvoicePage />}
          {page === "content-library" && <CurrentDashboard role={role} />}
          {page === "issues" && <IssueRoute role={role} currentPath={currentPath} />}
          {page === "notifications" && <PersonaNotificationsPage persona={issuePersonaForRole(role)} />}
          {page === "owner-decisions" && <OwnerDecisionCenterPage />}
          {page === "administration" && <AdministrationOwnerPage />}
        </div>
      </main>
    </div>
  );
}

function issuePersonaForRole(role: string): IssuePersona {
  const persona = personaForRole(role);
  return persona === "BUSINESS_DEVELOPMENT" ? "BUSINESS_DEVELOPMENT" : persona === "ENGINEERING" ? "ENGINEERING" : "OWNER";
}

function IssueRoute({ role, currentPath }: { role: string; currentPath: string }) {
  const persona = issuePersonaForRole(role);
  const match = currentPath.match(/^\/issues\/([^/]+)$/);
  return match ? <PersonaIssueDetailPage persona={persona} issueId={match[1]} /> : <PersonaIssuesPage persona={persona} />;
}

function ContextualNavigation({ page, currentPath }: { page: PublicPage; currentPath: string }) {
  const links = page === "project-delivery" ? [
    ["Engineering Works", "/engineering"], ["Drawing Review", "/engineering/drawing-review"],
    ["Preparation & Submission", "/permits"], ["Construction", "/construction"],
    ["Completion / As-Built", "/completion"], ["Handover & Closeout", "/handover"],
  ] : page === "billing" ? [["Finance register", "/billing"], ["Project Finance", "/billing?view=project-finance"]]
    : page === "opportunities" ? [["Proposal register", "/proposals"], ["New Proposal", "/proposals/new"]]
      : page === "contract-mobilization" ? [["Contracts", "/contract-mobilization"], ["Owner decisions", "/owner-decisions"]]
        : page === "content-library" ? [["Forms", "/master-content/forms"], ["Reports", "/master-content/reports"], ["Engineering Works", "/master-content/engineering-works"], ["Definitions", "/master-content/definitions"]]
          : [];
  if (!links.length) return null;
  return <nav className="contextual-nav" aria-label="Current workspace navigation">{links.map(([label, route]) => <a className={currentPath === route ? "active" : ""} href={route} key={route}>{label}</a>)}</nav>;
}
