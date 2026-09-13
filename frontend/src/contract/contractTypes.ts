export type ContractListItem = {
  id: string;
  contract_name?: string;
  contract_reference?: string;
  client?: { id?: string; name?: string; reference?: string } | null;
  project?: { id?: string; name?: string; reference?: string; code?: string | null } | null;
  project_opportunity_ref?: string | null;
  stage?: string | null;
  status?: string | null;
  amount?: string | number | null;
  currency?: string | null;
  next_action?: string | null;
  blockers_count?: number;
  billing_readiness?: string | null;
  close_date?: string | null;
};

export type ContractData = {
  id: string;
  contract?: {
    id?: string;
    name?: string;
    reference?: string;
    stage?: string;
    status?: string;
    amount?: string | number | null;
    currency?: string | null;
    duration?: string | null;
    project_description?: string | null;
    last_activity?: string | null;
    expected_close_date?: string | null;
    authority_state?: string | null;
  };
  client?: { id?: string; name?: string; reference?: string } | null;
  project?: { id?: string; name?: string; reference?: string; code?: string | null; status?: string } | null;
  origin?: { proposal_id?: string; proposal_reference?: string; title?: string; revision_number?: number; content_hash?: string; snapshot?: Record<string, any> } | null;
  current_revision?: { id?: string; revision_number?: number; status?: string; accepted?: boolean; authority_reviewed?: boolean; content_hash?: string; maker_checker?: Record<string, unknown> | null } | null;
  revisions?: Array<{ id?: string; revision_number?: number; status?: string; created_at?: string; supersedes_revision_id?: string | null; content_hash?: string | null; authority_reviewed?: boolean; accepted?: boolean; maker_checker?: Record<string, unknown> | null }>;
  readiness?: { ready?: boolean; blockers?: Array<{ code?: string; label?: string; severity?: string }>; warnings?: Array<{ code?: string; label?: string }>; accepted?: boolean; authority_reviewed?: boolean; activation_ready?: boolean; source10_controls?: Record<string, any> };
  operations?: Record<string, any>;
  billing_readiness?: Record<string, any>;
  activation?: { project_code?: string; start_date?: string; activated_by?: string; project_id?: string } | null;
  executed_evidence?: Array<{ id?: string; document_version_id?: string; content_hash?: string; recorded_by?: string; recorded_at?: string; source_reference?: string }>;
  handoff_evidence?: Record<string, Array<{ id?: string; contract_revision_id?: string; source_reference?: string; status?: string; recorded_by?: string; recorded_at?: string; document_version_id?: string | null; content_hash?: string | null }>>;
  evidence?: Array<Record<string, any>>;
  client_document?: Record<string, any>;
  lpo?: Record<string, any>;
  source_panel?: Array<{ key?: string; label?: string; detail?: string; source?: string; open?: string | null }>;
  payment_terms?: Array<Record<string, any>>;
  deliverables?: Array<Record<string, any>>;
  client_inputs?: Array<Record<string, any>>;
  client_contacts?: Array<{ id?: string; name?: string; email?: string; phone?: string; role_title?: string }>;
  history?: Array<{ id?: string; event_type?: string; occurred_at?: string; actor?: string; after?: Record<string, any> }>;
  effective_policies?: Record<string, any>;
  [key: string]: any;
};

export type IntelligenceSkill = {
  skill_id: string;
  version: string;
  name: string;
  purpose: string;
  status: string;
  eligibility_reason: string;
  required_capabilities: string[];
  allowed_reads: string[];
  allowed_effects: string[];
  canonical_write_authority: "ZERO";
  protected_action_authority: "ZERO";
  human_review_required: boolean;
  last_run?: Record<string, any> | null;
};

export type ContractIntelligence = {
  contract_id: string;
  architecture: { registry_version: string; citation_policy: string; result_policy: string };
  runtime: { feature_enabled: boolean; external_inference_enabled: boolean; real_content_allowed: boolean; state: string };
  skills: IntelligenceSkill[];
  findings: Array<Record<string, any>>;
};
