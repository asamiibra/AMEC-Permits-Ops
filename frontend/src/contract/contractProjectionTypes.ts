import type { StartPrerequisites } from "./timingTypes";

export type DocumentVersion = {
  id: string; filename?: string; version_number?: number; sha256?: string;
  source_path_or_reference?: string; approval_state?: string; currentness_state?: string;
  commercial_terms?: Record<string, unknown>;
};
export type DocumentSource = { label?: string; document?: DocumentVersion | null; status?: string; requiredness?: { label?: string } };
export type ContractEvidence = {
  id?: string; evidence_type?: string; source_role?: string; source_reference?: string;
  document_version_id?: string; document?: DocumentVersion | null; content_hash?: string;
  status?: string; recorded_by?: string; recorded_at?: string;
};
export type ContractCommitment = {
  id: string; sequence?: number; label?: string; title?: string; name?: string;
  term_text?: string; description?: string; required?: boolean; input_code?: string;
  commitment_ref?: string; due_trigger_description?: string; status?: string;
  source_document?: DocumentVersion | null; source_type?: string; human_verified_by?: string;
  basis_type?: string; percentage?: number | string; fixed_amount?: number | string;
  currency?: string; trigger_type?: string; trigger_description?: string; due_days?: number;
};
export type ServiceHandoff = { id: string; service_ref?: string; reference?: string; description?: string; title?: string; status?: string; project_id?: string; contract_revision_id?: string; service_offering_code?: string; service_type?: string; readiness?: string; blockers?: string[] };
export type ContactOption = { contact_point_id: string; organization_party_id?: string; practical_role?: string; operational_contact?: { name?: string }; organization?: { name?: string }; channel?: string };
export type ExtensionRecord = ContractEvidence & { metadata?: { event?: string; decision?: string; requested_end_date?: string; approved_end_date?: string; reason?: string } };
export type ContractOperations = {
  primary_next_action?: { label?: string; code?: string; target_section?: string; enabled?: boolean; action_type?: string };
  next_action?: string; status?: string; risk_state?: string; contract?: { status?: string };
  lifecycle_milestones?: Array<{ code: string; label?: string; complete: boolean; evidence?: string; blocked_reason?: string }>;
  readiness_states?: { states?: Record<string, { result?: string; missing_evidence?: string[] }> };
  start_prerequisites?: StartPrerequisites;
  contract_clock?: { days_remaining?: number | null; original_expected_end?: string; current_expected_end?: string; extension_state?: string; extension_history?: ExtensionRecord[] };
  controls?: { invoice_due_state?: string; collection_state?: string; contact_state?: string };
  schedule_semantics?: { date_semantics?: string; items?: Array<{ id: string; reference?: string; title?: string; start_at?: string; end_at?: string; due_at?: string; payment_condition?: string; amount?: string; status?: string }> };
  operational_contact_routing?: { purposes?: Record<string, { status?: string; generic_fallback_used?: boolean; eligible_options?: ContactOption[] }> };
  mobilization?: { service_engagements?: ServiceHandoff[] };
};
export type WorkflowTask = { id: string; title: string; status: string; next_action_code?: string; deep_link?: string };
export type Notification = { id: string; event_type: string; status: string; subject: string; created_at: string };
export type FormPackageItem = { form_id: string; ref?: string; title?: string; applicability?: string; prefill_state?: string; review_state?: string; signature_state?: string; current_document_version_id?: string; current_version?: number; current_sha256?: string; status?: string };
