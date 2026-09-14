import { ProposalRoutes } from "./features/proposals/ProposalRoutes";
import type { ProposalRole } from "./features/proposals/types";

type Role = ProposalRole | "PROCESS_CHAMPION";

/** Compatibility entry point: legacy Opportunity callers now render the canonical Proposal routes. */
export function OpportunitiesPage({ role }: { role: Role }) {
  return <ProposalRoutes role={role === "PROCESS_CHAMPION" ? "COMMERCIAL_APPROVER" : role} />;
}
