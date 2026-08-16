import { useEffect, useMemo, useState } from "react";
import { api } from "./api";
import {
  DocumentsPage,
  ConflictsPage,
  ConfigurationPage,
  SpikePage,
  SubmissionConfirmationPage,
} from "./Week2";
import {
  Phase0Page,
  AdjudicationPage,
  AnalysisPage,
  ThresholdsPage,
  CorpusPage,
  Tier1Page,
  Tier2Page,
  BusinessBaselinePage,
  DeliveryPage,
  CloseDecisionPage,
  BaselinePage,
  SignoffPage,
} from "./Week3";
import { PackageReadinessPage, MunicipalityPreparationPage } from "./Week45";
import { FindingsConsolePage } from "./Week7";
import { LineageValidityPage } from "./Week8";
import { AttachmentGridPage } from "./Week9";
import { ReconciliationControls } from "./ReconciliationControls";
import {
  AdministrationPage,
  Application,
  MyWorkPage,
  PermitsPage,
  PermitWorkspacePage,
  Project,
  ReviewsPage,
  WorkflowStage,
  projectWorkflowStage,
} from "./WorkflowFirst";
import {
  IssueFocusBanner,
  PersonaIssueDetailPage,
  PersonaIssuesPage,
  PersonaNotificationsPage,
  Persona,
} from "./PersonaIssuesNotifications";
import { ExpansionFoundation } from "./ExpansionFoundation";
import { OpportunitiesPage } from "./Opportunities";
import { ProposalsContractsPage } from "./ProposalsContracts";
import { EngineeringCloseoutPage } from "./EngineeringCloseout";
import { ProjectEngineeringPage } from "./ProjectEngineering";
import { EngineeringDrawingReviewPage } from "./EngineeringDrawingReview";
import { AboutPermitOpsPage } from "./AboutPermitOps";
import { AdministrationOwnerPage } from "./AdministrationOwner";
import { AMECWorkPage } from "./AMECWork";
import {
  ReadinessDrawer,
  ReadinessOverviewPage,
  getScreenDefinition,
} from "./ProductionReadiness";
import { AmecLogo } from "./AmecLogo";
import { readDemoRole } from "./rebrand";
import { CurrentDashboard } from "./Dashboard";
import { DashboardInputsPage } from "./DashboardInputs";
import { BDProposalOwnerSessionPage } from "./BDProposalOwnerSession";
import { AuthorityCaseWorkspacePage } from "./AuthorityCaseWorkspace";
import { NewPermitPage, PermitCasePage, PermitPortfolioPage } from "./PermitAuthorityUX";
import { BillingInvoicePage } from "./BillingInvoice";
import { ConstructionPage } from "./Construction";
import { CompletionPage } from "./Completion";
import { HandoverPage } from "./Handover";
import { HomeCommandCenter } from "./HomeCommandCenter";
import { Icon, type IconName } from "./Icon";
import "./dashboard.css";
import "./billing-invoice.css";
import "./construction.css";
import "./completion.css";
import "./handover.css";
import "./home-command-center.css";
import "./home-command-center-accessibility.css";

type Decision = {
  id: string;
  category: string;
  key: string;
  status: string;
  notes?: string;
};
type Raid = {
  id: string;
  type: string;
  title: string;
  description: string;
  severity: string;
  owner: string;
  status: string;
  mitigation: string;
};

type BusinessNavItem = {
  id: string;
  page: string;
  label: string;
  icon: IconName;
  path?: string;
  group: "HOME" | "BUSINESS FLOW";
};
const businessNav: BusinessNavItem[] = [
  { id: "home", page: "home", label: "Home", icon: "dashboard", path: "/home", group: "HOME" },
  { id: "intake-opportunity", page: "opportunities", label: "Intake & Opportunity", icon: "briefcase", path: "/opportunities", group: "BUSINESS FLOW" },
  { id: "contract-mobilization", page: "permits", label: "Contract & Mobilization", icon: "contract", path: "/proposals-contracts", group: "BUSINESS FLOW" },
  { id: "design-delivery", page: "project-engineering", label: "Design & Technical Delivery", icon: "engineering", path: "/engineering", group: "BUSINESS FLOW" },
  { id: "regulatory-submissions", page: "permit-portfolio", label: "Regulatory & Submissions", icon: "authority", path: "/permits", group: "BUSINESS FLOW" },
  { id: "construction-post-approval", page: "construction", label: "Construction & Post-Approval", icon: "construction", path: "/construction", group: "BUSINESS FLOW" },
  { id: "completion-as-built", page: "completion", label: "Completion & As-Built", icon: "completion", path: "/completion", group: "BUSINESS FLOW" },
  { id: "handover-closeout", page: "handover", label: "Handover & Closeout", icon: "handover", path: "/handover", group: "BUSINESS FLOW" },
];
const legacyNav = [
  { id: "expansion-foundation", label: "Expansion foundation" },
  { id: "projects", label: "Project register" },
  { id: "documents", label: "Documents / source evidence" },
  { id: "conflicts", label: "Conflicts" },
  { id: "config", label: "Configuration" },
  { id: "package", label: "Package readiness" },
  { id: "municipality", label: "Municipality preparation" },
  { id: "findings", label: "Findings & work" },
  { id: "lineage", label: "Lineage & validity" },
  { id: "attachments-grids", label: "Attachments & grids" },
  { id: "spike", label: "Test extraction" },
  { id: "adjudication", label: "Expected results" },
  { id: "analysis", label: "Test analysis" },
  { id: "thresholds", label: "Test targets" },
  { id: "corpus", label: "Test documents" },
  { id: "tier1", label: "Tier 1 decisions" },
  { id: "tier2", label: "Tier 2 backlog" },
  { id: "delivery", label: "Delivery / data" },
  { id: "close", label: "Go-live setup decision" },
  { id: "baseline", label: "Setup baseline" },
  { id: "signoff", label: "Commercial draft" },
  { id: "confirmation", label: "Submission confirmation" },
  { id: "discovery", label: "Project setup" },
  { id: "business", label: "Business case" },
  { id: "business-baseline", label: "Business baseline" },
  { id: "privacy", label: "Privacy & data" },
  { id: "volume", label: "Volume baseline" },
  { id: "inquiries", label: "Ministry inquiry" },
  { id: "raid", label: "RAID log" },
  { id: "control-loop", label: "Control diagnostics" },
];
const adminRoles = new Set(["SYSTEM_ADMIN", "OWNER_SPONSOR"]);
const personaForRole = (value: string): Persona =>
  value === "COMMERCIAL_APPROVER"
    ? "BUSINESS_DEVELOPMENT"
    : value === "RESPONSIBLE_ENGINEER"
      ? "ENGINEERING"
      : "OWNER";
const statusClass = (status: string) =>
  `status status-${status.toLowerCase().replaceAll("_", "-")}`;
const pageFromPath = () => {
  const path = window.location.pathname;
  if (path === "/" || path === "/home") return "home";
  if (path === "/dashboard") return "dashboard";
  if (path === "/dashboard-v2") return "dashboard";
  if (path === "/bd") return "opportunities";
  if (path === "/bd/proposals") return "bd-proposals";
  if (path === "/billing" || path.startsWith("/billing/")) return "billing";
  if (path === "/engineering") return "project-engineering";
  if (path === "/project-engineering") return "project-engineering";
  if (path === "/construction" || path.startsWith("/construction/")) return "construction";
  if (path === "/completion" || path.startsWith("/completion/")) return "completion";
  if (path === "/handover" || path.startsWith("/handover/")) return "handover";
  if (path === "/engineering/drawing-review") return "engineering-drawing-review";
  if (path === "/permit") return "permit-portfolio";
  if (path === "/authority-cases" || path.startsWith("/authority-cases/")) return "authority-cases";
  if (path === "/work") return "my-work";
  if (path === "/permits" || path === "/projects") return "permit-portfolio";
  if (path === "/proposals-contracts") return "permits";
  if (path === "/permits/new") return "permit-new";
  if (path.startsWith("/permits/")) return "permit-case";
  if (
    path === "/proposals/new" ||
    path.startsWith("/proposals/") ||
    path.startsWith("/contracts/")
  )
    return "permits";
  if (path === "/opportunities" || path.startsWith("/opportunities/")) return "opportunities";
  if (path === "/engineering-closeout") return "engineering-closeout";
  if (path === "/reviews") return "reviews";
  if (path === "/issues") return "issues";
  if (path.startsWith("/issues/")) return "issue-detail";
  if (path === "/notifications") return "notifications";
  if (
    path === "/about" ||
    path === "/how-permitops-works" ||
    path === "/operating-guide"
  )
    return "about";
  if (path === "/admin") return "administration";
  if (path === "/dashboard/inputs-go-live") return "dashboard-inputs";
  if (path === "/dashboard-v2/inputs-go-live") return "dashboard-inputs";
  if (path === "/admin/go-live-readiness") return "go-live-readiness";
  if (path === "/admin/control-diagnostics") return "control-loop";
  if (path.startsWith("/admin/")) return "administration";
  if (path.startsWith("/proposals-contracts/"))
    return "permit-workspace";
  return "my-work";
};
const stageFromPath = (): WorkflowStage => {
  const part = window.location.pathname
    .split("/")
    .pop()
    ?.replaceAll("-", "_")
    .toUpperCase();
  return part &&
    [
      "PROJECT_AND_SOURCES",
      "VERIFY_DATA",
      "PREPARE_PACKAGE",
      "MUNICIPALITY_PREPARATION",
      "FINAL_REVIEW",
      "AUTHORITY_REVIEW",
      "COMMENTS_AND_CORRECTIONS",
      "HISTORY",
    ].includes(part)
    ? (part as WorkflowStage)
    : "PROJECT_AND_SOURCES";
};

function App() {
  const [page, setPage] = useState(pageFromPath);
  const [selected, setSelected] = useState<Project | null>(null);
  const [selectedStage, setSelectedStage] =
    useState<WorkflowStage>(stageFromPath);
  const [projects, setProjects] = useState<Project[]>([]);
  const [apps, setApps] = useState<Application[]>([]);
  const [governance] = useState({ environment_badge: "SYNTHETIC PROTOTYPE" });
  const [error, setError] = useState("");
  const [role, setRole] = useState<string>(() => readDemoRole());
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
    const pathname = window.location.pathname;
    const target = pathname === "/dashboard-v2"
      ? "/dashboard"
      : pathname === "/dashboard-v2/inputs-go-live"
        ? "/dashboard/inputs-go-live"
        : null;
    if (!target) return;
    window.history.replaceState({}, "", `${target}${window.location.search}${window.location.hash}`);
    window.dispatchEvent(new PopStateEvent("popstate"));
  }, []);
  useEffect(() => {
    const originalPushState = window.history.pushState.bind(window.history);
    window.history.pushState = ((
      state: unknown,
      title: string,
      url?: string | URL | null,
    ) => {
      const next = url == null ? url : String(url);
      return originalPushState(state, title, next);
    }) as History["pushState"];
    return () => {
      window.history.pushState = originalPushState;
    };
  }, []);
  useEffect(() => {
    if (page === "my-work") return;
    Promise.allSettled([
      api<Project[]>("/api/projects"),
      api<Application[]>("/api/applications"),
    ]).then(([projectResult, applicationResult]) => {
      const p = projectResult.status === "fulfilled" ? projectResult.value : [];
      const a =
        applicationResult.status === "fulfilled" ? applicationResult.value : [];
      setProjects(p);
      setApps(a);
      const parts = window.location.pathname.split("/");
      if (page === "permit-workspace" && parts[2]) {
        const project = p.find((item) => item.id === parts[2]);
        if (project) setSelected(project);
      }
    });
  }, [page]);
  useEffect(() => {
    sessionStorage.setItem("proposalops-role", role);
  }, [role]);
  useEffect(() => {
    const syncLocation = () => {
      const nextPage = pageFromPath();
      const projectId =
        window.location.pathname.startsWith("/proposals-contracts/")
          ? window.location.pathname.split("/")[2]
          : undefined;
      setPage(nextPage);
      setSelectedStage(stageFromPath());
      setSelected(
        projectId
          ? projects.find((project) => project.id === projectId) || null
          : null,
      );
    };
    window.addEventListener("popstate", syncLocation);
    return () => window.removeEventListener("popstate", syncLocation);
  }, [projects]);
  useEffect(() => {
    if (
      window.location.pathname.startsWith("/admin") &&
      !adminRoles.has(role)
    ) {
      setPage("home");
      window.history.replaceState({}, "", "/home");
    }
  }, [role]);
  const navigate = (next: string) => {
    const navItem = businessNav.find((item) => item.id === next);
    const nextPage = navItem?.page || next;
    setPage(nextPage);
    setSelected(null);
    const path = navItem?.path ||
      (nextPage === "my-work"
        ? "/work"
        : nextPage === "permit-portfolio"
          ? "/permits"
          : nextPage === "permits"
            ? "/proposals-contracts"
          : nextPage === "about"
            ? "/operating-guide"
            : nextPage === "administration"
              ? "/admin"
              : nextPage === "go-live-readiness"
                ? "/admin/go-live-readiness"
                : nextPage === "dashboard-inputs"
                  ? "/dashboard/inputs-go-live"
                  : `/${nextPage}`);
    window.history.pushState({}, "", path);
    window.dispatchEvent(new PopStateEvent("popstate"));
  };
  const openPermit = (
    projectId: string,
    stage: WorkflowStage = "PROJECT_AND_SOURCES",
  ) => {
    const project =
      projects.find((item) => item.id === projectId) || projects[0];
    if (!project) return;
    setSelected(project);
    setSelectedStage(stage);
    setPage("permit-workspace");
    window.history.pushState(
      {},
      "",
      `/permits/${project.id}/${stage.toLowerCase().replaceAll("_", "-")}`,
    );
  };
  const openLegacy = (next: string, projectId?: string) => {
    if (!adminRoles.has(role) && !projectId) {
      navigate("my-work");
      return;
    }
    if (next === "control-loop") {
      setPage("control-loop");
      setSelected(null);
      window.history.pushState({}, "", "/admin/control-diagnostics");
      return;
    }
    setPage(next);
    setSelected(
      projectId ? projects.find((item) => item.id === projectId) || null : null,
    );
    window.history.pushState(
      {},
      "",
      projectId
        ? `/proposals-contracts/${projectId}/${next === "package" ? "package" : next === "municipality" ? "municipality" : next}`
        : `/admin/${next}`,
    );
  };
  const openProject = (p: Project) => openPermit(p.id);
  const visibleBusinessNav = businessNav.filter((item) => {
    if (role === "SYSTEM_ADMIN" || role === "OWNER_SPONSOR") return true;
    if (role === "COMMERCIAL_APPROVER")
      return [
        "home",
        "intake-opportunity",
        "contract-mobilization",
        "regulatory-submissions",
        "completion-as-built",
      ].includes(item.id);
    if (role === "RESPONSIBLE_ENGINEER")
      return [
        "home",
        "design-delivery",
        "regulatory-submissions",
        "construction-post-approval",
        "completion-as-built",
        "handover-closeout",
      ].includes(item.id);
    return ["home", "regulatory-submissions", "completion-as-built", "handover-closeout"].includes(item.id);
  });
  const title =
    page === "permit-workspace" && selected
      ? `${selected.project_number} · ${selected.project_name}`
      : ["permit-portfolio", "permit-new", "permit-case"].includes(page)
        ? "Permit"
      : page === "administration"
        ? "Administration"
        : page === "handover"
          ? "Handover / Admin Closeout"
        : page === "go-live-readiness"
          ? "Go-Live Setup"
          : page === "dashboard-inputs"
            ? "Master Content Setup & Go-Live"
              : page === "home"
                ? "Home"
                : visibleBusinessNav.find((item) => item.page === page)?.label ||
              legacyNav.find((item) => item.id === page)?.label ||
              (page === "project-detail" ? "Project detail" : "PermitOps");
  const permitSafetySurface = page === "permit-workspace";
  const issueDetailId = window.location.pathname.startsWith("/issues/")
    ? window.location.pathname.split("/")[2]
    : undefined;
  return (
    <div className="app-shell">
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
          <div className="nav-section-label">HOME</div>
          {visibleBusinessNav.filter((item) => item.group === "HOME").map((item) => <button key={item.id} aria-label={item.label} data-nav-id={item.id} className={page === item.page ? "nav-item active" : "nav-item"} onClick={() => navigate(item.id)}><span className="nav-icon"><Icon name={item.icon} size={18} /></span><span>{item.label}</span></button>)}
          <div className="nav-section-label">BUSINESS FLOW</div>
          {visibleBusinessNav.filter((item) => item.group === "BUSINESS FLOW").map((item) => <button key={item.id} aria-label={item.label} data-nav-id={item.id} className={page === item.page ? "nav-item active" : "nav-item"} onClick={() => navigate(item.id)}><span className="nav-icon"><Icon name={item.icon} size={18} /></span><span>{item.label}</span></button>)}
          {adminRoles.has(role) && (
            <>
              <div className="nav-section-label nav-system-label">SYSTEM</div>
              <button
                aria-label="Administration"
                data-nav-id="administration"
                className={
                  page === "administration" ? "nav-item active" : "nav-item"
                }
                onClick={() => navigate("administration")}
              >
                <span className="nav-icon"><Icon name="settings" size={18} /></span>
                <span>Admin</span>
                <span className="sr-only">Administration</span>
              </button>
              <button aria-label="Operating Guide" data-nav-id="operating-guide" className={page === "about" ? "nav-item active" : "nav-item"} onClick={() => navigate("about")}><span className="nav-icon"><Icon name="guide" size={18} /></span><span>Operating Guide</span></button>
            </>
          )}
          {!adminRoles.has(role) && <button aria-label="Operating Guide" data-nav-id="operating-guide" className={page === "about" ? "nav-item active" : "nav-item"} onClick={() => navigate("about")}><span className="nav-icon"><Icon name="guide" size={18} /></span><span>Operating Guide</span></button>}
        </nav>
        <div className="sidebar-foot">
          <span className="lock"><Icon name="shield" size={16} /></span>
          <span>
            <b>Safe boundary</b>
            <small>
              Synthetic data only
              <br />
              No portal writes
              <br />
              No closure automation
            </small>
          </span>
        </div>
      </aside>
      <main className="main">
        {page === "handover" && <HandoverPage />}
        {page === "engineering-drawing-review" && <EngineeringDrawingReviewPage />}
        <header className="topbar">
          <div className="topbar-heading">
            <AmecLogo size="sm" className="mobile-topbar-amec-logo" />
            <div>
              <span className="eyebrow">AMEC WORKSPACE</span>
              <h1>ProposalOps</h1>
            </div>
          </div>
          <div className="top-actions">
            <NotificationBell role={role} onNavigate={() => navigate("notifications")} />
            <ReadinessDrawer
              screenId={
                window.location.pathname === "/proposals/new"
                  ? getScreenDefinition("new-proposal").screenId
                  : page === "permit-workspace"
                    ? getScreenDefinition(selectedStage).screenId
                    : ["permit-portfolio", "permit-new", "permit-case"].includes(page)
                      ? getScreenDefinition("permits").screenId
                    : getScreenDefinition(page).screenId
              }
              role={role}
              onNavigate={navigate}
            />
            <span className="env-chip">
              <span className="dot green" />{" "}
              {governance?.environment_badge || "SYNTHETIC PROTOTYPE"}
            </span>
            <label aria-label="Demo as" className="role-switcher">
              Demo as
              <select
                aria-label="Persona"
                value={role}
                onChange={(event) => setRole(event.target.value)}
              >
                <option value="SYSTEM_ADMIN">Owner</option>
                <option value="COMMERCIAL_APPROVER">
                  Business Development
                </option>
                <option value="RESPONSIBLE_ENGINEER">Engineering</option>
              </select>
            </label>
            <button className="avatar" aria-label="Current user">
              SA
            </button>
          </div>
        </header>
        <div className="content">
          {error && (
            <div className="error-banner">
              API unavailable: {error}. Start the backend to view seeded data.
            </div>
          )}
          {page === "administration" ||
          page === "control-loop" ||
          page.startsWith("admin-") ||
          page === "go-live-readiness" ||
          page === "dashboard-inputs" ||
          page === "about" ||
          window.location.pathname === "/proposals/new" ? null : (
            <div className="synthetic-note compact-environment-badge">
              SYNTHETIC PROTOTYPE · NO PORTAL WRITES · HUMAN SUBMISSION REQUIRED
            </div>
          )}
          {page === "dashboard" && <CurrentDashboard role={role} />}{" "}
          {page === "home" && <HomeCommandCenter role={role} />}{" "}
          {page === "my-work" && (
            <MyWorkPage
              projects={projects}
              applications={apps}
              openPermit={openPermit}
              openAbout={() => navigate("about")}
            />
          )}{" "}
          {page === "about" && <AboutPermitOpsPage onNavigate={navigate} />}{" "}
          {page === "opportunities" && <OpportunitiesPage role={role as "SYSTEM_ADMIN" | "OWNER_SPONSOR" | "COMMERCIAL_APPROVER" | "RESPONSIBLE_ENGINEER"} />}{" "}
          {page === "billing" && <BillingInvoicePage />}{" "}
          {page === "bd-proposals" && <BDProposalOwnerSessionPage role={role as "SYSTEM_ADMIN" | "OWNER_SPONSOR" | "COMMERCIAL_APPROVER" | "RESPONSIBLE_ENGINEER"} />} {" "}
          {page === "project-engineering" && <ProjectEngineeringPage />}{" "}
          {page === "construction" && <ConstructionPage />}{" "}
          {page === "completion" && <CompletionPage />}{" "}
          {page === "authority-cases" && <AuthorityCaseWorkspacePage />}{" "}
          {page === "engineering-closeout" && <EngineeringCloseoutPage />}{" "}
          {page === "permit-portfolio" && <PermitPortfolioPage />} {" "}
          {page === "permit-new" && <NewPermitPage />} {" "}
          {page === "permit-case" && <PermitCasePage />} {" "}
          {page === "permits" && (
            <ProposalsContractsPage
              projects={projects}
              persona={
                role as
                  | "SYSTEM_ADMIN"
                  | "COMMERCIAL_APPROVER"
                  | "RESPONSIBLE_ENGINEER"
              }
              openRecord={openPermit}
            />
          )}{" "}
          {page === "reviews" && (
            <ReviewsPage
              projects={projects}
              applications={apps}
              openPermit={openPermit}
            />
          )}{" "}
          {page === "issues" && (
            <PersonaIssuesPage persona={personaForRole(role)} />
          )}{" "}
          {page === "issue-detail" && issueDetailId && (
            <PersonaIssueDetailPage
              persona={personaForRole(role)}
              issueId={issueDetailId}
            />
          )}{" "}
          {page === "notifications" && (
            <PersonaNotificationsPage persona={personaForRole(role)} />
          )}{" "}
          {page === "permit-workspace" && selected && (
            <PermitWorkspacePage
              project={selected}
              application={apps.find((item) => item.project_id === selected.id)}
              activeStage={selectedStage}
              openStage={(stage) => {
                setSelectedStage(stage);
                window.history.pushState(
                  {},
                  "",
                  `/permits/${selected.id}/${stage.toLowerCase().replaceAll("_", "-")}`,
                );
              }}
              openLegacy={openLegacy}
              backToPermits={() => navigate("permits")}
            />
          )}{" "}
          {page === "administration" && (
            <AdministrationPage openLegacy={openLegacy} />
          )}{" "}
          {page === "go-live-readiness" && (
            <ReadinessOverviewPage onNavigate={navigate} role={role} />
          )}{" "}
          {page === "dashboard-inputs" && (
            <DashboardInputsPage onNavigate={navigate} role={role} />
          )}{" "}
          {page === "expansion-foundation" && <ExpansionFoundation />}{" "}
          {page === "projects" && (
            <Projects projects={projects} apps={apps} open={openProject} />
          )}{" "}
          {page === "project-detail" && selected && (
            <ProjectDetail
              project={selected}
              apps={apps.filter((a) => a.project_id === selected.id)}
              back={() => navigate("permits")}
            />
          )}{" "}
          {page === "package" && (
            <PackageReadinessPage initialProjectId={selected?.id} />
          )}{" "}
          {page === "municipality" && (
            <MunicipalityPreparationPage initialProjectId={selected?.id} />
          )}{" "}
          {page === "findings" && <FindingsConsolePage />}
          {page === "lineage" && <LineageValidityPage />}
          {page === "attachments-grids" && <AttachmentGridPage />}
          {page === "documents" && <DocumentsPage />}
          {page === "conflicts" && <ConflictsPage />}
          {page === "config" && <ConfigurationPage />}
          {page === "spike" && <SpikePage />}
          {page === "adjudication" && <AdjudicationPage />}
          {page === "analysis" && <AnalysisPage />}
          {page === "thresholds" && <ThresholdsPage />}
          {page === "corpus" && <CorpusPage />}
          {page === "tier1" && <Tier1Page />}
          {page === "delivery" && <DeliveryPage />}
          {page === "close" && <CloseDecisionPage />}
          {page === "baseline" && <BaselinePage />}
          {page === "signoff" && <SignoffPage />}
          {page === "confirmation" && <SubmissionConfirmationPage />}
          {page === "discovery" && <Discovery />}
          {page === "business" && <BusinessCase />}
          {page === "business-baseline" && <BusinessBaselinePage />}
          {page === "privacy" && <Privacy />}
          {page === "volume" && <Volume />}
          {page === "inquiries" && <Inquiries />}
          {page === "raid" && <Raid />}
          {page === "control-loop" && (
            <ReconciliationControls
              state={{
                packageStatus: "BLOCKED",
                blockedReasons: ["Current evidence requires human approval"],
                packageStale: true,
                revisionStale: true,
                portalMismatch: true,
                municipalityValue: "Doha",
                dropdownCode: "MUN_A",
                dropdownLabel: "Doha Municipality",
                findingOwner: "Responsible Engineer",
                taskLabel: "Finding remediation",
                notificationStatus: "FAILED",
                precheckRun: "SYN-PRECHECK-0142",
                precheckRevision: "R2",
                handoffStatus: "HUMAN SUBMISSION REQUIRED",
              }}
            />
          )}
        </div>
      </main>
    </div>
  );
}

function PageIntro({
  kicker,
  title,
  description,
}: {
  kicker: string;
  title: string;
  description: string;
}) {
  return (
    <div className="page-intro">
      <div>
        <span className="eyebrow">{kicker}</span>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
    </div>
  );
}

function NotificationBell({ role, onNavigate }: { role: string; onNavigate: () => void }) {
  const [unread, setUnread] = useState(0);
  useEffect(() => {
    let live = true;
    api<{ summary?: { unread?: number } }>(`/api/notifications/summary?persona=${personaForRole(role)}`)
      .then((value) => { if (live) setUnread(Number(value.summary?.unread || 0)); })
      .catch(() => { if (live) setUnread(0); });
    return () => { live = false; };
  }, [role]);
  return <button className="header-notifications" aria-label={`Notifications${unread ? `, ${unread} unread` : ""}`} onClick={onNavigate}><Icon name="notifications" size={17} />{unread > 0 && <span className="header-notifications-badge">{unread > 99 ? "99+" : unread}</span>}</button>;
}
function Dashboard({
  projects,
  apps,
  go,
}: {
  projects: Project[];
  apps: Application[];
  go: (p: string) => void;
}) {
  const returned = apps.filter(
    (a) => a.application_status === "RETURNED",
  ).length;
  return (
    <>
      <PageIntro
        kicker="WEEK 1 CONTROL ROOM"
        title="A safe foundation for permit integrity"
        description="Canonical PermitOps data connected to three synthetic operating surfaces. Every link and decision is auditable."
      />
      <div className="metric-grid">
        <Metric
          label="Active projects"
          value={projects.filter((p) => p.status === "ACTIVE").length}
          tone="blue"
        />
        <Metric label="Applications" value={apps.length} tone="teal" />
        <Metric label="Returned applications" value={returned} tone="orange" />
        <Metric label="Open RAID items" value="10" tone="red" />
      </div>
      <div className="two-col">
        <section className="panel">
          <div className="panel-head">
            <div>
              <span className="eyebrow">PORTFOLIO</span>
              <h3>Projects requiring attention</h3>
            </div>
            <button className="text-button" onClick={() => go("projects")}>
              View all <Icon name="arrow-up-right" size={14} />
            </button>
          </div>
          <div className="mini-list">
            {projects.slice(0, 4).map((p) => (
              <button key={p.id} onClick={() => go("projects")}>
                <span>
                  <b>{p.project_number}</b>
                  <small>{p.project_name}</small>
                </span>
                <span
                  className={statusClass(
                    apps.find((a) => a.project_id === p.id)
                      ?.application_status || "DRAFT",
                  )}
                >
                  {apps.find((a) => a.project_id === p.id)
                    ?.application_status || "NO APP"}
                </span>
              </button>
            ))}
          </div>
        </section>
        <section className="panel discovery-card">
          <span className="eyebrow">DISCOVERY READINESS</span>
          <h3>Privacy & authority access</h3>
          <div className="progress">
            <div style={{ width: "28%" }} />
          </div>
          <b>2 of 7 decisions confirmed</b>
          <p>
            Real sensitive-document processing remains not approved. Review the
            discovery dashboard before any Phase 0 data decision.
          </p>
          <button className="button-secondary" onClick={() => go("discovery")}>
            Open discovery <Icon name="arrow-up-right" size={14} />
          </button>
        </section>
      </div>
      <ReconciliationControls
        state={{
          packageStatus: "BLOCKED",
          blockedReasons: ["Current evidence requires human approval"],
          packageStale: true,
          revisionStale: true,
          portalMismatch: true,
          municipalityValue: "Doha",
          dropdownCode: "MUN_A",
          dropdownLabel: "Doha Municipality",
          findingOwner: "Responsible Engineer",
          taskLabel: "Finding remediation",
          notificationStatus: "FAILED",
          precheckRun: "SYN-PRECHECK-0142",
          precheckRevision: "R2",
          handoffStatus: "HUMAN SUBMISSION REQUIRED",
        }}
      />
      <div className="synthetic-note">
        SYNTHETIC DEMONSTRATION DATA — REPLACE DURING PHASE 0 · No real QIDs,
        title deeds, credentials, or authority connections.
      </div>
    </>
  );
}
function Metric({
  label,
  value,
  tone,
}: {
  label: string;
  value: string | number;
  tone: string;
}) {
  return (
    <div className={`metric ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>Week 1 baseline</small>
    </div>
  );
}
function Projects({
  projects,
  apps,
  open,
}: {
  projects: Project[];
  apps: Application[];
  open: (p: Project) => void;
}) {
  return (
    <>
      <PageIntro
        kicker="CANONICAL REGISTER"
        title="Projects"
        description="PermitOps project identity stays canonical while external representations remain explicit links."
      />
      <section className="panel table-panel">
        <div className="toolbar">
          <span className="search-box">
            ⌕ <input placeholder="Filter projects" />
          </span>
          <span className="muted">{projects.length} records · synthetic</span>
        </div>
        <table>
          <thead>
            <tr>
              <th>Project #</th>
              <th>Project</th>
              <th>Municipality</th>
              <th>Permit type</th>
              <th>Application #</th>
              <th>Status</th>
              <th>Repeats</th>
              <th>Assigned engineer</th>
            </tr>
          </thead>
          <tbody>
            {projects.map((p) => {
              const a = apps.find((x) => x.project_id === p.id);
              return (
                <tr key={p.id} onClick={() => open(p)}>
                  <td>
                    <b className="linkish">{p.project_number}</b>
                  </td>
                  <td>{p.project_name}</td>
                  <td>{p.municipality}</td>
                  <td>{p.permit_type}</td>
                  <td>{a?.external_request_number || "—"}</td>
                  <td>
                    <span
                      className={statusClass(a?.application_status || "DRAFT")}
                    >
                      {a?.application_status || "NO APP"}
                    </span>
                  </td>
                  <td>{a?.repetition_count ?? "—"}</td>
                  <td>{p.assigned_engineer || "—"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>
    </>
  );
}
function ProjectDetail({
  project,
  apps,
  back,
}: {
  project: Project;
  apps: Application[];
  back: () => void;
}) {
  const [detail, setDetail] = useState<any>(null);
  useEffect(() => {
    api<any>(`/api/projects/${project.id}`)
      .then(setDetail)
      .catch(() => {});
  }, [project.id]);
  const a = apps[0];
  return (
    <>
      <button className="back-button" onClick={back}>
        <Icon name="arrow-left" size={14} /> Projects
      </button>
      <PageIntro
        kicker={project.project_number}
        title={project.project_name}
        description={`${project.municipality} · ${project.permit_type} · ${project.workstream || "Permit workstream"}`}
      />
      <div className="detail-grid">
        <section className="panel">
          <div className="panel-head">
            <h3>External system links</h3>
            <span className="tag">3 representations</span>
          </div>
          {(detail?.links || []).map((l: any) => (
            <div className="link-row" key={l.id}>
              <span className={`system-mark ${l.system_type.toLowerCase()}`}>
                {l.system_type[0]}
              </span>
              <span>
                <b>
                  {l.system_type === "MUNICIPALITY"
                    ? "Permit Authority Simulator"
                    : l.system_type}
                </b>
                <small>{l.display_reference}</small>
              </span>
              <span className="linked">LINKED</span>
            </div>
          ))}
          <div className="mismatch">
            ↗ User confirmation is required when identifiers conflict. No fuzzy
            auto-linking.
          </div>
        </section>
        <section className="panel">
          <div className="panel-head">
            <h3>Application status</h3>
            {a && (
              <span className={statusClass(a.application_status)}>
                {a.application_status}
              </span>
            )}
          </div>
          {a ? (
            <>
              <div className="app-number">{a.external_request_number}</div>
              <div className="app-stats">
                <div>
                  <span>Repetition count</span>
                  <b>{a.repetition_count}</b>
                </div>
                <div>
                  <span>Authority</span>
                  <b>Permit Authority Simulator</b>
                </div>
              </div>
              {a.application_status === "RETURNED" && (
                <div className="comments">
                  <b>Synthetic authority comments</b>
                  <p><Icon name="alert" size={14} /> Owner name differs from supporting document.</p>
                  <p><Icon name="alert" size={14} /> Drawing revision does not match package revision.</p>
                  <p><Icon name="alert" size={14} /> Required attachment missing.</p>
                </div>
              )}
            </>
          ) : (
            <p>No application linked.</p>
          )}
        </section>
      </div>
      <ReconciliationFoundation projectId={project.id} />
      <section className="placeholder-grid">
        {[
          "Documents",
          "Verified facts",
          "Requirements",
          "Package",
          "Municipality preparation",
          "Findings",
        ].map((t) => (
          <div className="placeholder" key={t}>
            <span>{t}</span>
            <b>Planned for subsequent build wave</b>
            <small>
              Week 1 intentionally does not implement this capability.
            </small>
          </div>
        ))}
      </section>
      <section className="panel">
        <div className="panel-head">
          <h3>Activity & audit</h3>
          <span className="muted">Correlation IDs retained</span>
        </div>
        {(detail?.audit || []).slice(0, 5).map((e: any) => (
          <div className="audit-row" key={e.id}>
            <span className="audit-dot" />
            <span>
              <b>{e.event_type}</b>
              <small>
                {new Date(e.occurred_at).toLocaleString()} ·{" "}
                {e.correlation_id.slice(0, 12)}...
              </small>
            </span>
          </div>
        ))}
      </section>
    </>
  );
}
function ReconciliationFoundation({ projectId }: { projectId: string }) {
  const [foundation, setFoundation] = useState<any>(null);
  const [property, setProperty] = useState<any>(null);
  const [rendering, setRendering] = useState<any>(null);
  useEffect(() => {
    Promise.all([
      api<any>(`/api/reconciliation/projects/${projectId}`),
      api<any>(`/api/reconciliation/properties/${projectId}`),
      api<any>(
        `/api/reconciliation/rendering-preview?project_id=${projectId}&field_code=PROPERTY.PLOT_NUMBER`,
      ),
    ])
      .then(([f, p, r]) => {
        setFoundation(f);
        setProperty(p);
        setRendering(r);
      })
      .catch(() => {});
  }, [projectId]);
  if (!foundation) return null;
  return (
    <section className="panel reconciliation-foundation">
      <div className="panel-head">
        <div>
          <span className="eyebrow">RECORDING-DERIVED FOUNDATION</span>
          <h3>Identity, ownership & rendering provenance</h3>
        </div>
        <span className="tag">{foundation.fixture?.fixture_version}</span>
      </div>
      <div className="reconciliation-grid">
        <div>
          <b>Initiation</b>
          <small>
            {foundation.initiation?.initiation_type} ·{" "}
            {foundation.initiation?.initiation_reference}
          </small>
          <b>Number reservation</b>
          <small>
            {foundation.reservation?.proposed_number} ·{" "}
            {foundation.reservation?.status}
          </small>
          <b>Synology</b>
          <small>{foundation.synology?.root_path}</small>
          <b>Excel</b>
          <small>
            {foundation.excel?.workbook_identity} ·{" "}
            {foundation.excel?.sheet_name} / row {foundation.excel?.row_number}
          </small>
        </div>
        <div>
          <b>Property</b>
          <small>
            {property?.property?.pin} · plot {property?.property?.plot_number}
          </small>
          <b>Owners</b>
          {(property?.owners || []).map((o: any) => (
            <small key={o.id}>
              {o.party?.name_en} · {Math.round(o.normalized_share * 100)}%
            </small>
          ))}
          <b>Representation</b>
          <small>
            {property?.representations?.[0]?.representative?.name_en || "None"}{" "}
            · {property?.authorizations?.[0]?.status || "—"}
          </small>
          <b>Rendering preview</b>
          <small>
            Raw: {rendering?.raw_observation?.raw_value} · Canonical:{" "}
            {rendering?.canonical_verified_value?.value}
          </small>
          <small>
            Targets:{" "}
            {Object.entries(rendering?.target_renderings || {})
              .map(([k, v]: any) => `${k}=${v.value}`)
              .join(" · ")}
          </small>
        </div>
      </div>
    </section>
  );
}

function Discovery() {
  const [items, setItems] = useState<Decision[]>([]);
  useEffect(() => {
    api<Decision[]>("/api/discovery/decisions")
      .then(setItems)
      .catch(() => {});
  }, []);
  const update = (item: Decision) => {
    const status = item.status === "UNKNOWN" ? "CONFIRMED" : "UNKNOWN";
    api<Decision>(`/api/discovery/decisions/${item.id}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }).then((x) => setItems(items.map((i) => (i.id === x.id ? x : i))));
  };
  return (
    <>
      <PageIntro
        kicker="PHASE 0 EVIDENCE BOARD"
        title="Discovery dashboard"
        description="Track the decisions that must be confirmed before real data or authority integration is considered."
      />
      <div className="decision-grid">
        {items.map((i) => (
          <div className="decision-card" key={i.id}>
            <div className="decision-top">
              <span className="eyebrow">{i.category}</span>
              <button
                className={`decision-status ${i.status.toLowerCase()}`}
                onClick={() => update(i)}
              >
                {i.status}
              </button>
            </div>
            <h3>{i.key.replaceAll("_", " ")}</h3>
            <p>{i.notes}</p>
            <small>
              Click status to simulate a reviewed decision. Audit event is
              created.
            </small>
          </div>
        ))}
      </div>
      <div className="two-col">
        <section className="panel">
          <span className="eyebrow">PROCESS</span>
          <h3>Current-state journey</h3>
          <p className="journey">
            Project → documents → manual entry → internal review → simulator
            preparation → human final submission → authority review
          </p>
          <span className="tag warning">
            WORKING HYPOTHESIS — VALIDATE WITH CLIENT
          </span>
        </section>
        <section className="panel privacy-callout">
          <span className="eyebrow">DATA SAFETY</span>
          <h3>Development policy</h3>
          <strong>SYNTHETIC / REDACTED ONLY</strong>
          <p>
            External AI route: DISABLED UNTIL APPROVED. No raw
            sensitive-document access is authorized.
          </p>
        </section>
      </div>
    </>
  );
}
function BusinessCase() {
  const [v, setV] = useState<any>(null);
  useEffect(() => {
    api<any>("/api/discovery/business-case")
      .then(setV)
      .catch(() => {});
  }, []);
  if (!v) return <Loading />;
  const change = (key: string, value: string) => {
    const next = { ...v, [key]: Number(value) };
    setV({
      ...v,
      ...next,
      applications_per_year: next.applications_per_month * 12,
      annual_manual_hours:
        (next.applications_per_month *
          12 *
          (next.manual_data_entry_minutes +
            next.upload_minutes +
            next.status_check_minutes)) /
        60,
    });
  };
  return (
    <>
      <PageIntro
        kicker="ILLUSTRATIVE BASELINE"
        title="Business-case snapshot"
        description="Current synthetic baseline exposure. Benefit assumptions will be established after Phase 0 evidence."
      />
      <div className="synthetic-note">
        SYNTHETIC DEMONSTRATION DATA — REPLACE DURING PHASE 0
      </div>
      <div className="business-layout">
        <section className="panel inputs">
          <h3>Editable inputs</h3>
          {[
            ["applications_per_month", "Applications / month"],
            ["manual_data_entry_minutes", "Data entry min / application"],
            ["upload_minutes", "Upload min / application"],
            ["status_check_minutes", "Status checks min / application"],
            ["return_rate", "Return rate (decimal)"],
            ["rework_hours_per_return", "Rework hours / return"],
            ["delay_days_per_return", "Delay days / return"],
            ["loaded_hourly_rate_qar", "Loaded labour rate (QAR / hour)"],
          ].map(([k, l]) => (
            <label key={k}>
              {l}
              <input
                type="number"
                value={v[k]}
                step={k === "return_rate" ? 0.05 : 1}
                onChange={(e) => change(k, e.target.value)}
              />
            </label>
          ))}
          <button
            className="button-primary"
            onClick={() =>
              api<any>("/api/discovery/business-case", {
                method: "PUT",
                body: JSON.stringify({ values: v }),
              })
            }
          >
            Save baseline
          </button>
        </section>
        <section className="panel exposure">
          <span className="eyebrow">CURRENT SYNTHETIC BASELINE EXPOSURE</span>
          <h3>Annual view</h3>
          <div className="exposure-row">
            <span>Applications / year</span>
            <b>{Math.round(v.applications_per_year)}</b>
          </div>
          <div className="exposure-row">
            <span>Current manual annual hours</span>
            <b>{Math.round(v.annual_manual_hours)} h</b>
          </div>
          <div className="exposure-row">
            <span>Estimated annual returned cases</span>
            <b>{Math.round(v.estimated_annual_returned_cases)}</b>
          </div>
          <div className="exposure-row">
            <span>Estimated rework hours</span>
            <b>{Math.round(v.estimated_rework_hours)} h</b>
          </div>
          <div className="exposure-row highlighted">
            <span>Indicative labour cost</span>
            <b>
              QAR {Math.round(v.indicative_labour_cost_qar).toLocaleString()}
            </b>
          </div>
          <p>
            These are illustrative calculations, not a savings or ROI claim.
          </p>
        </section>
      </div>
    </>
  );
}
function Privacy() {
  return (
    <>
      <PageIntro
        kicker="CONTROL GATE"
        title="Privacy & data access"
        description="No real sensitive data is authorized in DEV or TEST. This page makes the current boundary explicit."
      />
      <div className="privacy-banner">
        <div className="shield"><Icon name="check" size={16} /></div>
        <div>
          <b>REAL SENSITIVE-DOCUMENT PROCESSING: NOT APPROVED</b>
          <p>
            Development policy is synthetic / redacted only. The external AI
            route is disabled until approved.
          </p>
        </div>
      </div>
      <section className="decision-table panel">
        {[
          ["Third-party processing of owner/QID/title deed data", "UNKNOWN"],
          ["Approved data location", "UNKNOWN"],
          ["Remote/offshore raw-data access", "UNKNOWN"],
          ["External AI route", "DISABLED UNTIL APPROVED"],
          ["Approved TEST real-document location", "UNKNOWN"],
          ["Development policy", "SYNTHETIC / REDACTED ONLY"],
        ].map(([a, b]) => (
          <div key={a}>
            <span>{a}</span>
            <b
              className={
                b.includes("DISABLED") || b.includes("SYNTHETIC")
                  ? "safe"
                  : "unknown"
              }
            >
              {b}
            </b>
          </div>
        ))}
      </section>
    </>
  );
}
function Volume() {
  const [v, setV] = useState<any>(null);
  useEffect(() => {
    api<any>("/api/discovery/volume")
      .then(setV)
      .catch(() => {});
  }, []);
  if (!v) return <Loading />;
  return (
    <>
      <PageIntro
        kicker="EVIDENCE FOR LATER DESIGN"
        title="Volume / concurrency baseline"
        description="Synthetic editable values only. No sophisticated concurrency implementation exists in Week 1."
      />
      <div className="volume-grid">
        {Object.entries(v).map(([k, val]) => (
          <label className="volume-card" key={k}>
            <span>{k.replaceAll("_", " ")}</span>
            <input
              value={String(val)}
              onChange={(e) => setV({ ...v, [k]: e.target.value })}
            />
            <small>
              {k.includes("concurrent")
                ? "Informs whether a simple DB lease is enough later."
                : "Replace during Phase 0 validation."}
            </small>
          </label>
        ))}
      </div>
      <button
        className="button-primary"
        onClick={() =>
          api("/api/discovery/volume", {
            method: "PUT",
            body: JSON.stringify({ values: v }),
          })
        }
      >
        Save volume baseline
      </button>
    </>
  );
}
function Inquiries() {
  const [items, setItems] = useState<any[]>([]);
  useEffect(() => {
    api<any[]>("/api/ministry-inquiries")
      .then(setItems)
      .catch(() => {});
  }, []);
  const ask = (i: any) =>
    api<any>(`/api/ministry-inquiries/${i.id}`, {
      method: "PATCH",
      body: JSON.stringify({
        status: i.status === "NOT_ASKED" ? "ASKED" : "NOT_ASKED",
      }),
    }).then((x) => setItems(items.map((a) => (a.id === x.id ? x : a))));
  return (
    <>
      <PageIntro
        kicker="NARROW QUESTIONS"
        title="Ministry inquiry log"
        description="Process-quality questions for the client to validate. This is not a request to automate an official website."
      />
      <section className="panel inquiry-list">
        {items.map((i) => (
          <div className="inquiry-row" key={i.id}>
            <div>
              <span className="eyebrow">{i.question_code}</span>
              <b>{i.question}</b>
              <small>Owner: {i.client_owner || "TBD"}</small>
            </div>
            <button
              className={`decision-status ${i.status.toLowerCase()}`}
              onClick={() => ask(i)}
            >
              {i.status}
            </button>
          </div>
        ))}
      </section>
    </>
  );
}
function Raid() {
  const [items, setItems] = useState<Raid[]>([]);
  const [title, setTitle] = useState("");
  useEffect(() => {
    api<Raid[]>("/api/raid")
      .then(setItems)
      .catch(() => {});
  }, []);
  const add = () => {
    if (!title) return;
    api<Raid>("/api/raid", {
      method: "POST",
      body: JSON.stringify({
        type: "ISSUE",
        title,
        description: title,
        severity: "MEDIUM",
        owner: "TBD",
        status: "OPEN",
        mitigation: "To be confirmed",
      }),
    }).then((x) => {
      setItems([x, ...items]);
      setTitle("");
    });
  };
  return (
    <>
      <PageIntro
        kicker="DELIVERY CONTROL"
        title="RAID log"
        description="Risks, assumptions, issues, and dependencies for the Week 1 foundation."
      />
      <div className="raid-add">
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Add a synthetic issue or dependency"
        />
        <button className="button-primary" onClick={add}>
          Add item
        </button>
      </div>
      <section className="panel raid-list">
        {items.map((i) => (
          <div className="raid-row" key={i.id}>
            <span className={`raid-type ${i.type.toLowerCase()}`}>
              {i.type}
            </span>
            <div>
              <b>{i.title}</b>
              <p>{i.description}</p>
              <small>
                Owner: {i.owner} · Mitigation: {i.mitigation}
              </small>
            </div>
            <span className="tag">{i.status}</span>
          </div>
        ))}
      </section>
    </>
  );
}
function Loading() {
  return <div className="loading">Loading synthetic baseline…</div>;
}

export default App;
