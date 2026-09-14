export type DemoRole =
  | "SYSTEM_ADMIN"
  | "OWNER_SPONSOR"
  | "COMMERCIAL_APPROVER"
  | "RESPONSIBLE_ENGINEER";

export type Persona = "OWNER" | "BUSINESS_DEVELOPMENT" | "ENGINEERING";

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
  id: "home" | "opportunity" | "contract" | "billing" | "content-library";
  page: "home" | "opportunities" | "contract-mobilization" | "billing" | "content-library";
  route: string;
  label: string;
  icon: string;
  feature?: FeatureKey;
};

export const primaryNavigation: readonly PrimaryNavigationItem[] = [
  { id: "home", page: "home", route: "/home", label: "Home", icon: "⌂" },
  {
    id: "opportunity",
    page: "opportunities",
    route: "/opportunities",
    label: "Opportunity / Proposal / Client Tender",
    icon: "↗",
    feature: "moduleOpportunityProposalClientTender",
  },
  {
    id: "contract",
    page: "contract-mobilization",
    route: "/contract-mobilization",
    label: "Contract / Mobilization",
    icon: "▤",
    feature: "moduleContractMobilization",
  },
  {
    id: "billing",
    page: "billing",
    route: "/billing",
    label: "Billing / Invoice / Receivables / Collection",
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
];

const personaCapabilities: Record<Persona, Set<FeatureKey>> = {
  OWNER: new Set([
    "moduleOpportunityProposalClientTender",
    "moduleContractMobilization",
    "moduleBillingInvoiceReceivablesCollection",
    "moduleContentLibrary",
  ]),
  BUSINESS_DEVELOPMENT: new Set([
    "moduleOpportunityProposalClientTender",
    "moduleContractMobilization",
    "moduleBillingInvoiceReceivablesCollection",
    "moduleContentLibrary",
  ]),
  ENGINEERING: new Set([
    "moduleOpportunityProposalClientTender",
    "moduleContractMobilization",
    "moduleBillingInvoiceReceivablesCollection",
    "moduleContentLibrary",
  ]),
};

export function personaForRole(role: string): Persona {
  if (role === "COMMERCIAL_APPROVER") return "BUSINESS_DEVELOPMENT";
  if (role === "RESPONSIBLE_ENGINEER") return "ENGINEERING";
  return "OWNER";
}

export function featureVisible(feature: FeatureKey, role: string): boolean {
  if (!featureAvailability[feature]) return false;
  return personaCapabilities[personaForRole(role)].has(feature);
}

export function getPrimaryNavigation(role: string): PrimaryNavigationItem[] {
  return primaryNavigation.filter(
    (item) => !item.feature || featureVisible(item.feature, role),
  );
}

const disabledTopLevelPatterns: RegExp[] = [
  /^\/phase4\/review(?:\/|$)/,
  /^\/phase5\/review(?:\/|$)/,
  /^\/source18\/committee(?:\/|$)/,
  /^\/engineering(?:\/|$)/,
  /^\/engineering-closeout(?:\/|$)/,
  /^\/authority-cases(?:\/|$)/,
  /^\/construction(?:\/|$)/,
  /^\/completion(?:\/|$)/,
  /^\/handover(?:\/|$)/,
  /^\/notifications(?:\/|$)/,
  /^\/settings(?:\/|$)/,
  /^\/admin(?:\/|$)/,
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
  ACTIVE_TOP_LEVEL_MODULE_COUNT: 4,
  OWNER_PRIMARY_DESTINATION_COUNT: 5,
  HOME_VISIBLE: true,
  CONTENT_LIBRARY_TOP_LEVEL_MODULE_COUNT: 1,
  CONTENT_LIBRARY_INTERNAL_LIBRARY_COUNT: 4,
  FLAG_OFF_OVERRIDES_OWNER: true,
  FLAG_OFF_OVERRIDES_SYSTEM_ADMIN: true,
  FLAG_OFF_OVERRIDES_DEMO_ROLE: true,
} as const;
