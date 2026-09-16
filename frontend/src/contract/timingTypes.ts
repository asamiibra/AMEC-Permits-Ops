export const timingFacts = {
  CLIENT_ARCHITECTURE_APPROVED: "Client architecture approval",
  CONTRACT_DURATION_START: "Contract duration start",
  MUNICIPALITY_WORK_START: "Municipality work start",
} as const;
export type TimingFactType = keyof typeof timingFacts;
export type TimingTransition = "COMMERCIAL_START" | "PROJECT_ACTIVATION" | "DESIGN_START" | "CONTRACT_DURATION_START" | "MUNICIPALITY_WORK_START";
export type TimingFact = {
  fact: string; applicable: boolean; required_for: string[]; state: string;
  source_clause: string; source_document_version_id?: string | null;
  policy_version?: string; evidence_ids: string[];
  detail?: { effective_date?: string; recorded_by?: string; recorded_at?: string } | null;
};
export type StartPrerequisites = {
  contract_revision_id: string | null; status: string; facts: TimingFact[];
  blockers: string[]; blockers_by_transition: Record<string, string[]>; policy_version: string;
};
export type TimingRequirementInput = {
  fact: TimingFactType; applicable: boolean; required_for: TimingTransition[];
  source_clause: string; source_document_version_id: string; policy_version: string; reason: string;
};
export type TimingFactInput = {
  contract_revision_id: string; effective_date: string; trigger_type: string;
  source_clause: string; source_reference: string; source_document_version_id: string;
  policy_version: string; reason: string;
};
