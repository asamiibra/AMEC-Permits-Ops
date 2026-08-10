# Lifecycle and KPI contract

The backend predicate registry drives both KPI counts and list filtering. PROPOSAL_PREPARATION and PROPOSAL_HANDOVER are active/open Proposal states; a durable Contract overrides stale Proposal display state to Contracted (or Closed). Contract DRAFT remains Open and In Process. The list therefore cannot show a row as Intake Review while also offering View Contract.
