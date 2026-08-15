import { BDProposalOwnerSessionPage } from "./BDProposalOwnerSession";

type Role = "SYSTEM_ADMIN" | "OWNER_SPONSOR" | "COMMERCIAL_APPROVER" | "RESPONSIBLE_ENGINEER";

/** Compatibility route: /bd and /opportunities now open the canonical Proposal Intake surface. */
export function OpportunitiesPage({ role }: { role: Role }) {
  return <BDProposalOwnerSessionPage role={role} />;
}
