export type ProposalRole =
  | "SYSTEM_ADMIN"
  | "OWNER_SPONSOR"
  | "COMMERCIAL_APPROVER"
  | "RESPONSIBLE_ENGINEER";

export type ProposalStage =
  | "IN_REVIEW"
  | "RECEIVED"
  | "PROPOSAL_PREPARATION"
  | "PROPOSAL_HANDOVER"
  | "READY_FOR_QUOTATION"
  | "COMMERCIAL_REVIEW"
  | "QUOTATION_IN_PROGRESS"
  | "CLIENT_RESPONSE_PENDING"
  | "ACCEPTED"
  | "CONTRACT_HANDOVER"
  | "CLOSED"
  | string;

export type JsonRecord = Record<string, unknown>;

export interface ProposalRegisterRow {
  id: string;
  proposal_reference: string;
  proposal: string;
  project_ref: string | null;
  client: string;
  activity: string;
  stage: string;
  stage_code: ProposalStage;
  amount: string | number | null;
  last_activity: string | null;
  location: string | null;
  current_owner: string;
  next_action: { label?: string; reason?: string; blockers?: number; deep_link?: string; eligible?: boolean };
  owner_lane: JsonRecord;
  contract_eligible: boolean;
  validation: JsonRecord;
}

export interface ProposalRegisterResponse {
  items: ProposalRegisterRow[];
  lane_counts: Record<string, number>;
  lane_options?: Array<{ code: string; label: string }>;
  count: number;
  action_capabilities?: Record<string, { available?: boolean; capability?: string; reason?: string | null }>;
}

export interface ProposalDetail {
  id: string;
  proposal_reference: string;
  project_reference: string | null;
  project_id: string | null;
  client_account_id: string | null;
  client_name: string | null;
  title: string;
  stage: ProposalStage;
  stage_label: string;
  lifecycle: Array<{ number: number; label: string; active: boolean }>;
  current_owner: string;
  next_actor: string;
  next_action: { label?: string; eligible?: boolean };
  amount: string | number | null;
  last_activity: string | null;
  updated_at: string | null;
  fields: JsonRecord;
  provenance: JsonRecord;
  sources: JsonRecord[];
  notes: JsonRecord[];
  site_photos: JsonRecord[];
  forms_v2: JsonRecord;
  validation: JsonRecord;
  readiness_v2: JsonRecord;
  intake_readiness: JsonRecord;
  configuration: JsonRecord;
  proposal_breakdown: JsonRecord;
  hardening: JsonRecord;
  authority: JsonRecord;
  owner_lane: JsonRecord;
  outputs: JsonRecord;
  current_revision: JsonRecord | null;
  draft_revision: JsonRecord | null;
  revision_history: JsonRecord[];
  stage_history: JsonRecord[];
  commercial_controls: JsonRecord;
  action_capabilities?: Record<string, { available?: boolean; capability?: string; reason?: string | null }>;
  stage_gate: JsonRecord;
  contract_eligible?: boolean;
  ai_assist?: JsonRecord;
  intelligence?: JsonRecord;
  synthetic_only?: boolean;
}

export interface ProposalSourceOption {
  key: "TENDER_EMAIL" | "TENDER_DOCUMENT" | "TENDER_PHOTO" | "CLIENT_DATA" | "NONE";
  label: string;
  description: string;
  acceptsFile: boolean;
  icon: "mail" | "document" | "image" | "users" | "empty";
}

export const lifecycleStages = [
  { number: 1, label: "Intake & Sources", description: "Assemble the enquiry, client, site, and evidence context." },
  { number: 2, label: "Engineering Preparation", description: "Translate the request into confirmable AMEC scope." },
  { number: 3, label: "Commercial Review", description: "Prepare and accept the exact Proposal revision." },
  { number: 4, label: "Client Response", description: "Record distribution, response, acceptance evidence, and LPO basis." },
  { number: 5, label: "Contract Handoff", description: "Prove the accepted basis is eligible for Contract." },
] as const;
