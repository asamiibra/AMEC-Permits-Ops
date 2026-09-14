export type BillingStatus = string;

export type BillingCapabilityDTO = {
  role: string;
  capabilities: Record<string, boolean>;
  authority_source: "SERVER_MUTATION_POLICY";
  frontend_only_authority_grants: 0;
  unresolved_owner_decisions: Array<{ key: string; label: string }>;
};

export type BillingContext = {
  client?: { id: string; name: string; reference: string } | null;
  project?: { id: string; name: string; reference: string } | null;
  contract?: { id: string; name: string; reference: string } | null;
};

export type BillingInvoice = {
  id: string;
  invoice_reference: string;
  project_invoice_ordinal?: number | null;
  status: BillingStatus;
  contract_id?: string | null;
  project_id?: string | null;
  client_account_id?: string | null;
  current_revision_id?: string | null;
  source_clone_id?: string | null;
  clone_idempotency_key?: string | null;
};

export type InvoiceProjection = {
  invoice_id: string;
  invoice_reference: string;
  project_invoice_ordinal?: number | null;
  contract_id?: string | null;
  project_id?: string | null;
  client_account_id?: string | null;
  status: BillingStatus;
  revision_id?: string | null;
  revision_number?: number | null;
  billing_period?: string | null;
  invoice_date?: string | null;
  due_date?: string | null;
  payable_amount?: string | null;
  currency?: string | null;
  cash_allocated_amount: string;
  non_cash_resolved_amount: string;
  outstanding_amount?: string | null;
  receivable_state: BillingStatus;
  collection_status: string;
  follow_up_count: number;
  latest_follow_up?: Record<string, unknown> | null;
  days_relative_to_due?: number | null;
  collection_action?: string;
  context?: BillingContext;
};

export type InvoiceRegisterItem = {
  invoice: BillingInvoice;
  contract?: Record<string, unknown> | null;
  client?: Record<string, unknown> | null;
  project?: Record<string, unknown> | null;
  revision?: Record<string, unknown> | null;
  stage: string;
  receivable: Record<string, unknown>;
};

export type BillingPlanItem = {
  plan: Record<string, unknown> & { id: string; status: string; billing_mode?: string };
  revision?: Record<string, unknown> & { id: string; revision_number: number; currency: string; billing_mode?: string } | null;
  milestones: BillingMilestone[];
  context: BillingContext;
};

export type BillingMilestone = {
  id: string;
  sequence: number;
  name: string;
  description?: string | null;
  currency: string;
  basis_type: string;
  calculated_amount?: string | null;
  trigger_type: string;
  trigger_description?: string | null;
  eligibility_state: string;
  status: string;
  billing_mode?: string | null;
  plan_id?: string | null;
  plan_revision_id?: string | null;
  contract_id?: string | null;
  project_id?: string | null;
  client_account_id?: string | null;
  context: BillingContext;
  invoiced_amount: string;
  actual_collected: string;
  remaining_invoiceable: string;
  invoiceable_now: boolean;
  invoices: Array<{ invoice_id: string; invoice_reference: string; status: string; amount: string; currency: string }>;
  latest_eligibility?: Record<string, unknown> | null;
};

export type PaymentReceipt = {
  id: string;
  client_account_id: string;
  contract_id: string;
  project_id?: string | null;
  received_date: string;
  amount: string;
  currency: string;
  reference: string;
  payment_method?: string | null;
  verification_status: string;
  recorded_at: string;
  verified_at?: string | null;
};

export type PaymentItem = {
  payment: PaymentReceipt;
  credit: { state: string; received_amount: string; allocated_amount: string; unallocated_balance: string; verification_status: string; currency: string };
  context: BillingContext;
  evidence: { primary: boolean; receipt_voucher: boolean };
  allocations: Array<Record<string, unknown>>;
  reversals: Array<Record<string, unknown>>;
  eligible_invoices?: Array<{ invoice_id: string; invoice_reference: string; project_id?: string | null; outstanding_amount: string; currency: string; milestone_ids: string[] }>;
};

export type BillingEvidenceItem = { document_id: string; document_version_id: string; label: string; filename: string; approval_state: string; source_reference: string; mime_type: string; open_path: string };

export type WorkItemTarget = { entity_type: string; entity_id: string; route: string };

export type WorkItem = {
  category: string;
  why: string;
  next_action: string;
  authority_needed: string;
  entity: Record<string, unknown>;
  target?: WorkItemTarget;
};

export type CommandCenterDTO = {
  metrics: { ready_to_invoice: number; draft_review_required: number; issued_outstanding: number; overdue: number; payments_to_verify: number; unallocated_client_credit: number };
  work_items: WorkItem[];
  open_receivables: InvoiceProjection[];
  payments: PaymentItem[];
  source_of_truth: string;
  system_insights_only: boolean;
  ai_assisted: boolean;
  unresolved_owner_decisions: string[];
};

export type BillingReportsDTO = {
  invoice_report: InvoiceProjection[];
  open_receivables: InvoiceProjection[];
  payment_history: PaymentItem[];
  ytd: Record<string, unknown> | null;
  ytd_status: string;
  timezone?: string | null;
  source_of_truth: string;
};

export type BillingControlsDTO = {
  financial_account_masters: Array<Record<string, unknown>>;
  financial_account_versions: Array<Record<string, unknown>>;
  invoice_numbering: { status: string; policy: unknown; production_fail_closed: boolean };
  unresolved_owner_decisions: string[];
  ai_canonical_write_authority: 0;
  ai_protected_action_authority: 0;
  resolved_owner_policies?: Array<{ key: string; policy_status: string; effective_value: string }>;
  fx_policy?: { status: string; policy: string; records: Array<Record<string, unknown>> };
  expected_exp_policy?: { status: string; policy: string };
  ytd_policy?: { status: string; boundary: string; runtime_configuration_status: string };
};

export type BillingPlanDetailDTO = {
  plan: Record<string, unknown> & { id: string; status: string; billing_mode?: string };
  revision?: Record<string, unknown> & { id: string; revision_number: number; status: string; billing_mode?: string } | null;
  revisions?: Array<Record<string, unknown>>;
  milestones: BillingMilestone[];
  readiness_requests?: Array<Record<string, unknown>>;
  context?: BillingContext;
};

export type ProjectFinanceDTO = {
  project?: Record<string, unknown> | null;
  contract?: Record<string, unknown> | null;
  currency?: string | null;
  project_value?: string | null;
  qar_amount?: string | null;
  fx_projection?: Record<string, unknown>;
  expected_exp?: Record<string, unknown>;
  total_invoiced?: string;
  amount_received?: string;
  outstanding_amount?: string;
  billing_completion_state?: string;
  financial_completion_state?: string;
  invoices?: InvoiceProjection[];
  milestones?: BillingMilestone[];
  payment_history?: PaymentItem[];
  ytd?: Record<string, unknown>;
};

export type InvoiceDetailDTO = {
  invoice: BillingInvoice;
  client?: Record<string, unknown> | null;
  contract?: Record<string, unknown> | null;
  project?: Record<string, unknown> | null;
  revision: Record<string, unknown> & { id: string; status: string; currency?: string; payable_total?: string; service_period?: string | null; service_period_label?: string | null; service_period_start?: string | null; service_period_end?: string | null; invoice_date?: string | null; due_date?: string | null; created_at?: string | null };
  lines: Array<Record<string, unknown> & { id: string; description: string; calculated_line_amount: string; currency: string }>;
  issue?: Record<string, unknown> | null;
  artifact?: Record<string, unknown> | null;
  communications: { state: string; deliveries: Array<Record<string, unknown>>; acknowledgments: Array<Record<string, unknown>> };
  receivable: { state: string; communication_state: string; outstanding_amount?: string | null; verified_paid_amount: string; resolved_non_cash_amount: string };
  allocations: Array<Record<string, unknown>>;
  resolutions: Array<Record<string, unknown>>;
  follow_ups: Array<Record<string, unknown>>;
  precheck: { result: string; checks: Array<{ code: string; status: string; reason: string }> };
};
