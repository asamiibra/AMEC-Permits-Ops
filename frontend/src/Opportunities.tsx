import { ProposalRoutes } from "./features/proposals/ProposalRoutes";

type Role = "SYSTEM_ADMIN" | "OWNER_SPONSOR" | "COMMERCIAL_APPROVER" | "RESPONSIBLE_ENGINEER";

/** Compatibility entry point: legacy Opportunity callers now render the canonical Proposal routes. */
export function OpportunitiesPage({ role }: { role: Role }) {
  return <ProposalRoutes role={role} />;
}
