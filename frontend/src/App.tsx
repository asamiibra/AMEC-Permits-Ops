import { useEffect, useState } from "react";
import { ApiError, api } from "./api";
import { ContractMobilizationPage } from "./AdministrationOwner";
import { CurrentDashboard } from "./Dashboard";
import { BillingInvoicePage } from "./BillingInvoice";
import { BillingShell } from "./billing/BillingShell";
import { HomePage } from "./Home";
import { ProposalRoutes } from "./features/proposals/ProposalRoutes";
import type { ProposalRole } from "./features/proposals/types";
import { AmecLogo } from "./AmecLogo";
import { browserAuthMode, getSignedInAccountIdentity, signOut } from "./auth";
import { readDemoRole } from "./rebrand";
import { classifyPublicRoute, type PublicPage } from "./domainOwnershipRoutes";
import { getPrimaryNavigation, isSupportedShellRole } from "./featureAvailability";
import { AuthzSurface, type AuthzSurfaceState } from "./AuthFailureSurface";
import "./dashboard.css";
import "./billing-invoice.css";
import "./admin-owner.css";

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
  const [page, setPage] = useState<PublicPage>(pageFromPath);
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
          <small>QEC-DOHA · SYNTHETIC COMMISSIONING</small>
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
                  <option value="SYSTEM_ADMIN">System Admin</option>
                  <option value="PROCESS_CHAMPION">Business Development</option>
                  <option value="RESPONSIBLE_ENGINEER">Engineering</option>
                </select>
              </label>
            )}
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
            SYNTHETIC PROTOTYPE · NO PORTAL WRITES · HUMAN SUBMISSION REQUIRED
          </div>
          {page === "home" && <HomePage />}
          {page === "opportunities" && <ProposalRoutes role={moduleRole as ProposalRole} />}
          {page === "contract-mobilization" && <ContractMobilizationPage />}
          {page === "billing" && <BillingShell />}
          {page === "content-library" && <CurrentDashboard role={role} />}
        </div>
      </main>
    </div>
  );
}
