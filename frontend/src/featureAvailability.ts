export type DemoRole = "SYSTEM_ADMIN" | "OWNER_SPONSOR" | "COMMERCIAL_APPROVER" | "RESPONSIBLE_ENGINEER";
/** Business personas are deliberately limited to the three operating roles. */
export type Persona = "OWNER" | "BUSINESS_DEVELOPMENT" | "ENGINEERING";
export type AccessClass = "SYSTEM_ADMIN";

import { isAllowedPublicRoute } from "./domainOwnershipRoutes";

/** Human-facing product workspaces. Admin remains a capability, not a business persona. */
export const featureAvailability = {
  moduleWork: true,
  moduleOpportunityProposalClientTender: true,
  moduleContractMobilization: true,
  moduleProjectDelivery: true,
  moduleBillingInvoiceReceivablesCollection: true,
  moduleContentLibrary: true,
  moduleIssuesNotifications: true,
  moduleOwnerDecisions: true,
  evidenceReview: false,
  classifierReview: false,
  inputsGoLive: false,
  settings: false,
  notifications: false,
  admin: true,
  operatingGuide: false,
  aiIntegration: false,
} as const;

export type FeatureKey = keyof typeof featureAvailability;
export type PrimaryNavigationItem = {
  id: "home" | "work" | "opportunity" | "contract" | "project-delivery" | "billing" | "content-library";
  page: "home" | "work" | "opportunities" | "contract-mobilization" | "project-delivery" | "billing" | "content-library";
  route: string; label: string; icon: string; feature?: FeatureKey;
};

export const primaryNavigation: readonly PrimaryNavigationItem[] = [
  { id: "home", page: "home", route: "/home", label: "Home", icon: "⌂" },
  { id: "work", page: "work", route: "/work", label: "My Work", icon: "✓", feature: "moduleWork" },
  { id: "opportunity", page: "opportunities", route: "/proposals", label: "Opportunities & Proposals", icon: "↗", feature: "moduleOpportunityProposalClientTender" },
  { id: "contract", page: "contract-mobilization", route: "/contract-mobilization", label: "Contract & Mobilization", icon: "▤", feature: "moduleContractMobilization" },
  { id: "project-delivery", page: "project-delivery", route: "/engineering", label: "Projects & Delivery", icon: "⌁", feature: "moduleProjectDelivery" },
  { id: "billing", page: "billing", route: "/billing", label: "Billing & Finance", icon: "¤", feature: "moduleBillingInvoiceReceivablesCollection" },
  { id: "content-library", page: "content-library", route: "/content-library", label: "Content Library", icon: "▦", feature: "moduleContentLibrary" },
];

const shared = new Set<FeatureKey>([
  "moduleWork", "moduleOpportunityProposalClientTender", "moduleContractMobilization", "moduleProjectDelivery",
  "moduleBillingInvoiceReceivablesCollection", "moduleContentLibrary", "moduleIssuesNotifications", "moduleOwnerDecisions",
]);
const personaCapabilities: Record<Persona, Set<FeatureKey>> = {
  OWNER: new Set(shared), BUSINESS_DEVELOPMENT: new Set(shared), ENGINEERING: new Set(shared),
};

export function personaForRole(role: string): Persona | null {
  if (role === "OWNER_SPONSOR") return "OWNER";
  if (role === "PROCESS_CHAMPION" || role === "COMMERCIAL_APPROVER") return "BUSINESS_DEVELOPMENT";
  if (role === "RESPONSIBLE_ENGINEER") return "ENGINEERING";
  return null;
}
export function isSupportedShellRole(role: string): boolean { return ["OWNER_SPONSOR", "PROCESS_CHAMPION", "COMMERCIAL_APPROVER", "RESPONSIBLE_ENGINEER", "SYSTEM_ADMIN"].includes(role); }
export function featureVisible(feature: FeatureKey, role: string): boolean {
  if (!featureAvailability[feature]) return false;
  if (role === "SYSTEM_ADMIN") return feature === "admin";
  const persona = personaForRole(role);
  return Boolean(persona && personaCapabilities[persona].has(feature));
}
export function getPrimaryNavigation(role: string): PrimaryNavigationItem[] { return primaryNavigation.filter((item) => !item.feature || featureVisible(item.feature, role)); }

const historicalOrDeferredPatterns: RegExp[] = [
  /^\/phase\d+(?:\/|$)/, /^\/week\d+(?:\/|$)/, /^\/source18(?:\/|$)/, /^\/reviews(?:\/|$)/,
  /^\/dashboard(?:-v2)?\/inputs-go-live(?:\/|$)/, /^\/admin\/go-live-readiness(?:\/|$)/,
  /^\/admin\/contracts\/inputs\/go-live(?:\/|$)/, /^\/operating-guide(?:\/|$)/,
  /^\/about(?:\/|$)/, /^\/how-permitops-works(?:\/|$)/,
];
export function isDisabledTopLevelRoute(pathname: string): boolean { return !isAllowedPublicRoute(pathname) || historicalOrDeferredPatterns.some((pattern) => pattern.test(pathname)); }

export const ownerShellAcceptance = {
  ACTIVE_TOP_LEVEL_MODULE_COUNT: 7, OWNER_PRIMARY_DESTINATION_COUNT: 7, HOME_VISIBLE: true,
  CONTENT_LIBRARY_TOP_LEVEL_MODULE_COUNT: 1, CONTENT_LIBRARY_INTERNAL_LIBRARY_COUNT: 4,
  FLAG_OFF_OVERRIDES_OWNER: true, FLAG_OFF_OVERRIDES_SYSTEM_ADMIN: true, FLAG_OFF_OVERRIDES_DEMO_ROLE: true,
} as const;
