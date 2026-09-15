export type DemoRole =
  | "SYSTEM_ADMIN"
  | "OWNER_SPONSOR"
  | "COMMERCIAL_APPROVER"
  | "RESPONSIBLE_ENGINEER";

export type Persona =
  | "OWNER"
  | "BUSINESS_DEVELOPMENT"
  | "ENGINEERING"
  | "SYSTEM_ADMIN_TECHNICAL";

import { isAllowedPublicRoute } from "./domainOwnershipRoutes";

/**
 * The single release-visibility registry for the Owner shell.
 *
 * A false value hides the surface from every persona, including the demo
 * SYSTEM_ADMIN alias. It does not remove the underlying domain implementation
 * or server authorization.
 */
export const featureAvailability = {
  moduleOpportunityProposalClientTender: true,
  moduleContractMobilization: true,
  moduleBillingInvoiceReceivablesCollection: true,
  moduleContentLibrary: true,
  moduleMyWork: true,
  moduleDesignEngineering: true,
  moduleRegulatorySubmissions: true,
  moduleEngineersCommittee: true,
  moduleConstruction: true,
  moduleCompletion: true,
  moduleHandover: true,
  moduleAdministration: true,

  evidenceReview: false,
  classifierReview: false,
  designTechnicalDeliveryTopLevel: false,
  regulatorySubmissionsTopLevel: false,
  engineersCommitteeTopLevel: false,
  constructionPostApprovalTopLevel: false,
  completionAsBuiltTopLevel: false,
  handoverCloseoutTopLevel: false,
  inputsGoLive: false,
  notifications: false,
  settings: false,
  admin: false,
  operatingGuide: false,
} as const;

export type FeatureKey = keyof typeof featureAvailability;

export type PrimaryNavigationItem = {
  id: string;
  page: string;
  route: string;
  label: string;
  icon: string;
  feature?: FeatureKey;
};

export const primaryNavigation: readonly PrimaryNavigationItem[] = [
  { id: "home", page: "home", route: "/home", label: "Home", icon: "⌂" },
  {
    id: "work", page: "work", route: "/work", label: "My Work", icon: "✓", feature: "moduleMyWork",
  },
  {
    id: "opportunity",
    page: "opportunities",
    route: "/opportunities",
    label: "Opportunities & Proposals",
    icon: "↗",
    feature: "moduleOpportunityProposalClientTender",
  },
  {
    id: "contract",
    page: "contract-mobilization",
    route: "/contract-mobilization",
    label: "Contracts & Mobilization",
    icon: "▤",
    feature: "moduleContractMobilization",
  },
  {
    id: "billing",
    page: "billing",
    route: "/billing",
    label: "Billing & Receivables",
    icon: "¤",
    feature: "moduleBillingInvoiceReceivablesCollection",
  },
  {
    id: "content-library",
    page: "content-library",
    route: "/content-library",
    label: "Content Library",
    icon: "▦",
    feature: "moduleContentLibrary",
  },
  { id: "engineering", page: "engineering", route: "/engineering", label: "Design & Engineering", icon: "⌁", feature: "moduleDesignEngineering" },
  { id: "regulatory", page: "regulatory", route: "/regulatory", label: "Regulatory & Submissions", icon: "◫", feature: "moduleRegulatorySubmissions" },
  { id: "committee", page: "committee", route: "/committee", label: "Engineers Committee", icon: "◈", feature: "moduleEngineersCommittee" },
  { id: "construction", page: "construction", route: "/construction", label: "Construction", icon: "⌂", feature: "moduleConstruction" },
  { id: "completion", page: "completion", route: "/completion", label: "Completion & As-Built", icon: "□", feature: "moduleCompletion" },
  { id: "handover", page: "handover", route: "/handover", label: "Handover & Closeout", icon: "⇢", feature: "moduleHandover" },
  { id: "administration", page: "administration", route: "/administration", label: "Administration", icon: "⚙", feature: "moduleAdministration" },
];

const personaCapabilities: Record<Persona, Set<FeatureKey>> = {
  OWNER: new Set([
    "moduleOpportunityProposalClientTender",
    "moduleContractMobilization",
    "moduleBillingInvoiceReceivablesCollection",
    "moduleContentLibrary",
    "moduleMyWork", "moduleDesignEngineering", "moduleRegulatorySubmissions", "moduleEngineersCommittee", "moduleConstruction", "moduleCompletion", "moduleHandover", "moduleAdministration",
  ]),
  BUSINESS_DEVELOPMENT: new Set([
    "moduleOpportunityProposalClientTender",
    "moduleContractMobilization",
    "moduleBillingInvoiceReceivablesCollection",
    "moduleContentLibrary",
    "moduleMyWork", "moduleDesignEngineering", "moduleRegulatorySubmissions", "moduleEngineersCommittee", "moduleConstruction", "moduleCompletion", "moduleHandover", "moduleAdministration",
  ]),
  ENGINEERING: new Set([
    "moduleOpportunityProposalClientTender",
    "moduleContractMobilization",
    "moduleBillingInvoiceReceivablesCollection",
    "moduleContentLibrary",
    "moduleMyWork", "moduleDesignEngineering", "moduleRegulatorySubmissions", "moduleEngineersCommittee", "moduleConstruction", "moduleCompletion", "moduleHandover", "moduleAdministration",
  ]),
  SYSTEM_ADMIN_TECHNICAL: new Set([
    "moduleOpportunityProposalClientTender",
    "moduleContractMobilization",
    "moduleBillingInvoiceReceivablesCollection",
    "moduleContentLibrary",
    "moduleMyWork", "moduleDesignEngineering", "moduleRegulatorySubmissions", "moduleEngineersCommittee", "moduleConstruction", "moduleCompletion", "moduleHandover", "moduleAdministration",
  ]),
};

export function personaForRole(role: string): Persona | null {
  if (role === "OWNER_SPONSOR") return "OWNER";
  if (role === "PROCESS_CHAMPION") return "BUSINESS_DEVELOPMENT";
  if (role === "COMMERCIAL_APPROVER") return "BUSINESS_DEVELOPMENT";
  if (role === "RESPONSIBLE_ENGINEER") return "ENGINEERING";
  if (role === "SYSTEM_ADMIN") return "SYSTEM_ADMIN_TECHNICAL";
  return null;
}

export function isSupportedShellRole(role: string): boolean {
  return [
    "OWNER_SPONSOR",
    "PROCESS_CHAMPION",
    "RESPONSIBLE_ENGINEER",
    "SYSTEM_ADMIN",
  ].includes(role);
}

export function featureVisible(feature: FeatureKey, role: string): boolean {
  if (!featureAvailability[feature]) return false;
  const persona = personaForRole(role);
  return persona ? personaCapabilities[persona].has(feature) : false;
}

export function getPrimaryNavigation(role: string): PrimaryNavigationItem[] {
  return primaryNavigation.filter(
    (item) => !item.feature || featureVisible(item.feature, role),
  );
}

const disabledTopLevelPatterns: RegExp[] = [
  /^\/phase4\/review(?:\/|$)/,
  /^\/phase5\/review(?:\/|$)/,
  /^\/authority-cases(?:\/|$)/,
  /^\/notifications(?:\/|$)/,
  /^\/settings(?:\/|$)/,
  /^\/dashboard\/inputs-go-live(?:\/|$)/,
  /^\/dashboard-v2\/inputs-go-live(?:\/|$)/,
  /^\/admin\/go-live-readiness(?:\/|$)/,
  /^\/admin\/contracts\/inputs\/go-live(?:\/|$)/,
  /^\/operating-guide(?:\/|$)/,
  /^\/about(?:\/|$)/,
  /^\/how-permitops-works(?:\/|$)/,
  /^\/reviews(?:\/|$)/,
];

export function isDisabledTopLevelRoute(pathname: string): boolean {
  return !isAllowedPublicRoute(pathname) || disabledTopLevelPatterns.some((pattern) => pattern.test(pathname));
}

export const ownerShellAcceptance = {
  ACTIVE_TOP_LEVEL_MODULE_COUNT: 12,
  OWNER_PRIMARY_DESTINATION_COUNT: 13,
  HOME_VISIBLE: true,
  CONTENT_LIBRARY_TOP_LEVEL_MODULE_COUNT: 1,
  CONTENT_LIBRARY_INTERNAL_LIBRARY_COUNT: 4,
  FLAG_OFF_OVERRIDES_OWNER: true,
  FLAG_OFF_OVERRIDES_SYSTEM_ADMIN: true,
  FLAG_OFF_OVERRIDES_DEMO_ROLE: true,
} as const;
