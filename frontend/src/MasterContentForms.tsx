import { useEffect, useState } from "react";
import { api, userFacingError } from "./api";
import { readCanonicalForm, readCanonicalForms } from "./contentLibraryApi";
import {
  ContentType,
  Drawer,
  MODULE_LABELS,
  UsedInPicker,
  friendlyStatus,
  versionLabel,
} from "./masterContentUi";

type Category = { id: string; label: string; allowed_content_types: string[] };
type Version = {
  id: string;
  version: number;
  status: string;
  file_name: string;
  updated_by: string;
  updated_at: string;
  change_reason?: string;
  rendition?: { status: string; available: boolean };
};
export type CanonicalForm = {
  id: string;
  serial_number?: number;
  ref: string;
  content_type: "FORM";
  title: string;
  category?: { id: string; label: string } | null;
  description?: string;
  used_in?: string[];
  purpose_bindings?: { module: string; usage_type: string; active: boolean }[];
  source_type_code?: string | null;
  version?: number;
  version_status: string;
  owner_status?: "Current" | "Needs Review" | "Inactive";
  needs_review?: boolean;
  review_note?: string | null;
  current_source_filename?: string;
  updated?: string;
  versions?: Version[];
  governance?: {
    profile?: Record<string, any>;
    provenance?: any[];
    quality_flags?: any[];
    source_sections?: any[];
    readiness?: { state: string; blocking_reasons: string[]; warnings: string[]; last_evaluated_at?: string | null };
    badges?: string[];
  };
  applicability?: V2Applicability[];
  requirement_policy_lineage?: V2Lineage[];
  technical_rule_lineage?: V2Lineage[];
  automation_profiles?: V2AutomationProfile[];
  current_document_version_id?: string | null;
  current_version_id?: string | null;
};

type V2Applicability = {
  id: string;
  external_body_id: string;
  jurisdiction_id?: string | null;
  service_type_id: string;
  lifecycle_phase_id?: string | null;
  source_document_version_id: string;
  status: string;
  confirmed_by?: string | null;
  effective_from?: string | null;
  effective_to?: string | null;
};
type V2Lineage = {
  id: string;
  source_role: string;
  governance_status: string;
  document_version_id: string;
  source_section_id?: string | null;
  relation_type: string;
};
type V2AutomationProfile = Record<string, any> & {
  id: string;
  source_document_version_id: string;
  source_version_state: string;
  automation_status: string;
  readiness?: { state: string; blocking_reasons: string[]; evidence?: Record<string, any> };
  releases?: Array<Record<string, any>>;
};
type V2Catalogs = {
  external_bodies: Array<Record<string, any>>;
  jurisdictions: Array<Record<string, any>>;
  service_types: Array<Record<string, any>>;
  lifecycle_phases: Array<Record<string, any>>;
};

const ownerRoles = new Set(["SYSTEM_ADMIN", "OWNER_SPONSOR"]);
type Filters = {
  q?: string;
  category?: string;
  status?: string;
  module?: string;
};
type SaveRequest = { form?: FormData; metadata?: Record<string, unknown> };

export function CanonicalFormsLibrary({
  role,
  surface = "DASHBOARD",
  compact = false,
  filters,
}: {
  role: string;
  surface?: "DASHBOARD" | "ADMINISTRATION";
  compact?: boolean;
  filters?: Filters;
}) {
  const [forms, setForms] = useState<CanonicalForm[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editor, setEditor] = useState<CanonicalForm | null | undefined>(
    undefined,
  );
  const [history, setHistory] = useState<{
    itemId: string;
    title: string;
    versions: Version[];
  } | null>(null);
  const [details, setDetails] = useState<CanonicalForm | null>(null);
  const [busy, setBusy] = useState(false);
  const [governanceFilters, setGovernanceFilters] = useState({ ownership: "", artifact_kind: "", currentness: "", readiness: "", quality_state: "", restricted_sample: "", language: "" });
  const [v2Filters, setV2Filters] = useState({ external_body_id: "", jurisdiction_id: "", service_type_id: "", lifecycle_phase_id: "", applicability_status: "", readiness: "" });
  const [catalogs, setCatalogs] = useState<V2Catalogs | null>(null);
  const canWrite = ownerRoles.has(role);
  const technicalGovernance = surface === "ADMINISTRATION";
  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const [content, categoryRows, catalogRows] = await Promise.all([
        readCanonicalForms<CanonicalForm>({
          q: filters?.q,
          category_label: filters?.category,
          owner_status: filters?.status,
          module: filters?.module,
          ownership: governanceFilters.ownership,
          artifact_kind: governanceFilters.artifact_kind,
          currentness: governanceFilters.currentness,
          wave_a_readiness: governanceFilters.readiness,
          automation_readiness: v2Filters.readiness,
          quality_state: governanceFilters.quality_state,
          restricted_sample: governanceFilters.restricted_sample,
          language: governanceFilters.language,
          external_body_id: v2Filters.external_body_id,
          jurisdiction_id: v2Filters.jurisdiction_id,
          service_type_id: v2Filters.service_type_id,
          lifecycle_phase_id: v2Filters.lifecycle_phase_id,
          applicability_status: v2Filters.applicability_status,
        }),
        api<Category[]>("/api/master-content/categories"),
        api<V2Catalogs>("/api/dashboard-v2/catalogs"),
      ]);
      setForms(content);
      setCategories(categoryRows);
      setCatalogs(catalogRows);
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Forms could not be loaded.",
      );
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    void load();
  }, [filters?.q, filters?.category, filters?.status, filters?.module, governanceFilters.ownership, governanceFilters.artifact_kind, governanceFilters.currentness, governanceFilters.readiness, governanceFilters.quality_state, governanceFilters.restricted_sample, governanceFilters.language, v2Filters.external_body_id, v2Filters.jurisdiction_id, v2Filters.service_type_id, v2Filters.lifecycle_phase_id, v2Filters.applicability_status, v2Filters.readiness]);
  const save = async (request: SaveRequest) => {
    setBusy(true);
    setError("");
    try {
      if (request.metadata && editor)
        await api(`/api/master-content/${editor.id}/metadata`, {
          method: "PATCH",
          body: JSON.stringify(request.metadata),
          headers: {
            "Content-Type": "application/json",
            "Idempotency-Key": crypto.randomUUID(),
            "X-Source-Surface": surface,
          },
        });
      else if (request.form)
        await api(
          editor
            ? `/api/master-content/${editor.id}/versions`
            : "/api/master-content",
          {
            method: "POST",
            body: request.form,
            headers: {
              "Idempotency-Key": crypto.randomUUID(),
              "X-Source-Surface": surface,
            },
          },
        );
      setEditor(undefined);
      await load();
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "The Form change could not be saved.",
      );
    } finally {
      setBusy(false);
    }
  };
  const filtered = Boolean(filters?.q || filters?.category || filters?.status || filters?.module || Object.values(v2Filters).some(Boolean) || Object.values(governanceFilters).some(Boolean));
  return (
    <section
      id="forms"
      className={`panel dashboard-section canonical-forms-library ${compact ? "canonical-forms-library-compact" : ""}`}
      data-testid={`${surface.toLowerCase()}-forms`}
    >
      <div className="dashboard-section-head">
        <div>
          <span className="eyebrow">
            {surface === "ADMINISTRATION"
              ? "ADMINISTRATION · CANONICAL FORMS"
              : "MASTER LIBRARY"}
          </span>
          <h3>Forms</h3>
          <p className="section-description">
            Reusable AMEC forms and templates.
          </p>
        </div>
        <div className="section-head-actions">
          <span className="record-count">
            {forms.length} {forms.length === 1 ? "record" : "records"}
          </span>
          {canWrite && (
            <button className="button-primary" onClick={() => setEditor(null)}>
              + New Form
            </button>
          )}
        </div>
      </div>
      {surface === "ADMINISTRATION" && (
        <p className="admin-owner-copy canonical-forms-description">
          The same canonical Forms library used by Dashboard, AMEC Work,
          Business Development, and Permit workflows.
        </p>
      )}
      {technicalGovernance && <details className="forms-advanced-filters">
        <summary>Advanced governance filters</summary>
        <div className="dashboard-filter-bar forms-governance-filters">
          <>
            {([['external_body_id', 'External body', catalogs?.external_bodies || []], ['jurisdiction_id', 'Jurisdiction', catalogs?.jurisdictions || []], ['service_type_id', 'Service type', catalogs?.service_types || []], ['lifecycle_phase_id', 'Lifecycle phase', catalogs?.lifecycle_phases || []]] as const).map(([key, label, options]) => <label key={key}>{label}<select aria-label={label} value={v2Filters[key]} onChange={(event) => setV2Filters((current) => ({ ...current, [key]: event.target.value }))}><option value="">All</option>{options.map((option) => <option key={String(option.id)} value={String(option.id)}>{option.name_en || option.code || option.label || option.id}</option>)}</select></label>)}
            <label>Applicability status<select aria-label="Applicability status" value={v2Filters.applicability_status} onChange={(event) => setV2Filters((current) => ({ ...current, applicability_status: event.target.value }))}><option value="">All</option>{['DRAFT', 'ACTIVE', 'NEEDS_REVALIDATION', 'SUPERSEDED', 'RETIRED'].map((option) => <option key={option} value={option}>{option.replaceAll('_', ' ')}</option>)}</select></label>
            <label>Automation readiness<select aria-label="Automation readiness" value={v2Filters.readiness} onChange={(event) => setV2Filters((current) => ({ ...current, readiness: event.target.value }))}><option value="">All</option><option value="AUTOMATED_USE_READY">Automated use ready</option><option value="NEEDS_REVALIDATION">Needs revalidation</option><option value="BLOCKED">Blocked</option></select></label>
            {([['ownership', 'Content ownership', ['AMEC_OWNED', 'EXTERNAL_OFFICIAL', 'EXTERNAL_REFERENCE', 'REFERENCE_SAMPLE', 'NEEDS_REVIEW']], ['artifact_kind', 'Artifact kind', ['AUTHORITY_FORM', 'AMEC_FORM', 'CHECKLIST', 'AUTHORIZATION', 'SERVICE_REQUEST', 'OTHER', 'UNKNOWN']], ['currentness', 'Currentness', ['UNVERIFIED', 'VERIFIED_CURRENT', 'VERIFIED_NOT_CURRENT', 'NEEDS_REVIEW']], ['readiness', 'Wave A readiness', ['REFERENCE_ONLY', 'BLOCKED', 'MANUAL_USE_READY', 'SUPERSEDED']], ['quality_state', 'Quality state', ['OPEN', 'ACCEPTED_RISK', 'RESOLVED']], ['language', 'Language', ['AR', 'EN', 'AR_EN_BILINGUAL', 'OTHER']]] as const).map(([key, label, options]) => <label key={`wave-a-${key}`}>{label}<select aria-label={label} value={governanceFilters[key]} onChange={(event) => setGovernanceFilters((current) => ({ ...current, [key]: event.target.value }))}><option value="">All</option>{options.map((option) => <option key={option} value={option}>{option.replaceAll('_', ' ')}</option>)}</select></label>)}
            <label>Restricted sample<select aria-label="Restricted sample" value={governanceFilters.restricted_sample} onChange={(event) => setGovernanceFilters((current) => ({ ...current, restricted_sample: event.target.value }))}><option value="">All</option><option value="true">Restricted</option><option value="false">Not restricted</option></select></label>
          </>
        </div>
      </details>}
      {error && (
        <div className="dashboard-error" role="alert">
          <b>Forms unavailable</b>
          <span>{error}</span>
          <button className="button-secondary" onClick={() => void load()}>
            Retry
          </button>
        </div>
      )}
      {loading ? (
        <div className="dashboard-state" role="status">
          Loading Forms…
        </div>
      ) : forms.length === 0 ? (
        <EmptyState noun="forms" filtered={filtered} />
      ) : (
        <FormTable
          forms={forms}
          canWrite={canWrite}
          onEdit={setEditor}
          onOpen={async (form) => setDetails(await readCanonicalForm<CanonicalForm>(form.id))}
          onHistory={async (form) => {
            const detail = await readCanonicalForm<CanonicalForm>(form.id);
            setHistory({
              itemId: form.id,
              title: `${form.ref} · ${form.title}`,
              versions: detail.versions || [],
            });
          }}
        />
      )}
      {editor !== undefined && (
        <FormEditor
          item={editor || undefined}
          categories={categories}
          sourceOptions={forms}
          busy={busy}
          onClose={() => setEditor(undefined)}
          onSave={save}
        />
      )}
      {history && (
        <FormHistory history={history} onClose={() => setHistory(null)} />
      )}
      {details && <FormDetails item={details} role={role} surface={surface} categories={categories} onRefresh={async () => setDetails(await readCanonicalForm<CanonicalForm>(details.id))} onModify={() => { setDetails(null); setEditor(details); }} onClose={() => setDetails(null)} />}
    </section>
  );
}

function FormTable({
  forms,
  canWrite,
  onEdit,
  onOpen,
  onHistory,
}: {
  forms: CanonicalForm[];
  canWrite: boolean;
  onEdit: (item: CanonicalForm) => void;
  onOpen: (item: CanonicalForm) => void;
  onHistory: (item: CanonicalForm) => void;
}) {
  return (
    <div className="dashboard-table-wrap">
      <table className="dashboard-table">
        <thead>
          <tr>
            <th>S/N</th>
            <th>Reference</th>
            <th>Form</th>
            <th>Category</th>
            <th>Description</th>
            <th>Used In</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {forms.map((form, index) => (
            <tr key={form.id}>
              <td>{form.serial_number || index + 1}</td>
              <td>
                <code className="content-reference">{form.ref}</code>
              </td>
              <td>
                <b>{form.title}</b>
                <small className="table-subline">Version {form.version || "—"}</small>
              </td>
              <td>{form.category?.label || "Uncategorized"}</td>
              <td
                className="description-cell"
                title={form.description || "No description"}
              >
                {form.description || "No description"}
              </td>
              <td><UsedInChips values={form.used_in} /></td>
              <td><StatusBadge value={form.owner_status || form.version_status} hasVersion={Boolean(form.version)} /></td>
              <td className="dashboard-actions">
                <button className="table-action action-view" onClick={() => onOpen(form)}>Open</button>
                {canWrite && (
                  <button
                    className="table-action action-edit"
                    onClick={() => onEdit(form)}
                  >
                    Modify
                  </button>
                )}
                <button
                  className="table-action action-history"
                  onClick={() => onHistory(form)}
                >
                  History
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function FormDetails({ item, role, surface, categories, onRefresh, onModify, onClose }: { item: CanonicalForm; role: string; surface: "DASHBOARD" | "ADMINISTRATION"; categories: Category[]; onRefresh: () => Promise<void>; onModify: () => void; onClose: () => void }) {
  const governance = item.governance || {};
  const profile = governance.profile || {};
  const readiness = governance.readiness || { state: "BLOCKED", blocking_reasons: ["Governance profile is not available."], warnings: [] };
  const technicalGovernance = surface === "ADMINISTRATION";
  return <Drawer title={`${item.ref} · ${item.title}`} eyebrow="FORM DETAILS" onClose={onClose} footer={<button type="button" className="button-secondary" onClick={onClose}>Close</button>}>
    <section className="form-governance-section"><h3>Overview</h3><div className="content-detail-grid">
      <div><span>Reference</span><b>{item.ref}</b></div>
      <div><span>Category</span><b>{item.category?.label || "Uncategorized"}</b></div>
      <div><span>Current Version</span><b>{versionLabel(item.version)}</b></div>
      <div><span>Status</span><StatusBadge value={item.owner_status || item.version_status} hasVersion={Boolean(item.version)} /></div>
      <div><span>Used In</span><b>{(item.used_in || []).map(module => MODULE_LABELS[module] || module).join(", ") || "Not assigned"}</b></div>
      <div><span>Current source file</span><b>{item.current_source_filename || "Not recorded"}</b></div>
    </div><p className="detail-description">{item.description || "No description"}</p>{item.owner_status === "Needs Review" && item.review_note && <p className="review-note"><b>Review note:</b> {item.review_note}</p>}</section>
    <section className="form-governance-section"><h3>Version History</h3>{(item.versions || []).length ? <div className="content-history-list">{(item.versions || []).map((version) => <div className="content-history-row" key={version.id}><b>Version {version.version}</b><span>{version.file_name} · {version.status}</span><small>{version.updated_at ? new Date(version.updated_at).toLocaleDateString() : "Date not recorded"}</small></div>)}</div> : <p>No previous versions recorded.</p>}</section>
    {technicalGovernance && <>
    <section className="form-governance-section"><h3>Source &amp; Authority</h3><div className="content-detail-grid"><div><span>Ownership</span><b>{String(profile.content_ownership_class || "NEEDS_REVIEW").replaceAll("_", " ")}</b></div><div><span>Publisher / Origin</span><b>{profile.publisher_name || "Not recorded"}</b></div><div><span>Official Form No.</span><b>{profile.official_form_no || "Not recorded"}</b></div><div><span>Issue / Date</span><b>{[profile.official_issue_no, profile.official_issue_date].filter(Boolean).join(" · ") || "Not recorded"}</b></div><div><span>Language</span><b>{String(profile.language_profile || "OTHER").replaceAll("_", " ")}</b></div><div><span>Currentness</span><b>{String(profile.currentness_status || "UNVERIFIED").replaceAll("_", " ")}</b></div></div></section>
    <section className="form-governance-section"><h3>Quality &amp; Sensitivity</h3><p>{profile.sensitivity_flags?.length ? `Sensitive flags: ${profile.sensitivity_flags.join(", ")}` : "No sensitivity flags recorded."}</p>{(governance.quality_flags || []).map((flag: any) => <div className={`quality-flag quality-${String(flag.severity).toLowerCase()}`} key={flag.id}><b>{String(flag.code).replaceAll("_", " ")}</b><span>{flag.status} · {flag.description}</span></div>)}</section>
    <section className="form-governance-section"><h3>Source Sections</h3>{(governance.source_sections || []).length ? (governance.source_sections || []).map((section: any) => <div className="source-section-row" key={section.id}><b>{section.label}</b><span>{section.locator_type} {section.page_start ? `· p.${section.page_start}${section.page_end && section.page_end !== section.page_start ? `–${section.page_end}` : ""}` : ""} · exact version {section.document_version_id.slice(0, 8)}</span></div>) : <p>No exact source sections pinned.</p>}</section>
    <section className="form-governance-section readiness-panel"><h3>Readiness</h3><strong>{readiness.state.replaceAll("_", " ")}</strong>{readiness.blocking_reasons.length > 0 && <><b>Blocking reasons</b><ul>{readiness.blocking_reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul></>}{readiness.warnings.length > 0 && <><b>Warnings</b><ul>{readiness.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></>}</section>
    <V2GovernanceDetails item={item} role={role} onRefresh={onRefresh} />
    </>}
    {ownerRoles.has(role) && <ContentLibraryIntelligencePanel item={item} categories={categories} />}
    {(surface === "DASHBOARD" || !profile.restricted_reference_sample) && <a className="button-secondary" href={`/api/master-content/${item.id}/download`} download>Download current source</a>}
    {ownerRoles.has(role) && <div className="detail-actions"><button type="button" className="button-secondary" onClick={onModify}>Modify</button><button type="button" className="button-secondary" onClick={onModify}>Upload version</button></div>}
  </Drawer>;
}

const CONTENT_LIBRARY_INTELLIGENCE_SKILLS = [
  ["master-content.intake-governance-analysis", "Intake governance"],
  ["master-content.quality-gap-analysis", "Quality gaps"],
  ["master-content.version-change-analysis", "Version change"],
  ["master-content.dependency-impact-analysis", "Dependency impact"],
  ["master-content.reuse-applicability-analysis", "Reuse & applicability"],
  ["master-content.description-draft", "Description draft"],
  ["master-content.source-grounded-assist", "Source-grounded assist"],
] as const;

function ContentLibraryIntelligencePanel({ item, categories }: { item: CanonicalForm; categories: Category[] }) {
  return <ContentLibraryAiAssist itemId={item.id} sourceId={item.current_document_version_id || item.current_version_id || item.id} categories={categories} entityLabel="Form" />;
}

type ContentLibraryAiAssistProps = {
  itemId?: string;
  sourceId?: string;
  categories?: Category[];
  onApplyDraft?: (fields: Record<string, unknown>) => void;
  basePath?: string;
  entityLabel?: string;
};

export function ContentLibraryAiAssist({ itemId, sourceId, categories = [], onApplyDraft, basePath, entityLabel = "Form" }: ContentLibraryAiAssistProps) {
  const [busy, setBusy] = useState<string | null>(null);
  const [result, setResult] = useState<Record<string, any> | null>(null);
  const [selectedFields, setSelectedFields] = useState<Record<string, boolean>>({});
  const [reviewStatus, setReviewStatus] = useState<string | null>(null);
  const [error, setError] = useState("");
  const run = async (skillId: string) => {
    if (!itemId) return;
    setBusy(skillId); setError(""); setReviewStatus(null);
    try {
      const next = await api<Record<string, any>>(`${basePath || `/api/master-content/${itemId}/intelligence`}/${skillId}`, {
        method: "POST",
        headers: { "Idempotency-Key": crypto.randomUUID() },
      });
      setResult(next);
      setSelectedFields(Object.fromEntries(Object.keys(next.draft_fields || {}).map((key) => [key, true])));
    } catch (cause) {
      setError(userFacingError(cause, "Content Library intelligence is unavailable."));
    } finally { setBusy(null); }
  };
  const review = async (decision: "ACCEPT" | "REJECT") => {
    if (!itemId || !result?.work_product_id || !result.review_precondition_version) return;
    setBusy("review"); setError("");
    const acceptedFields = decision === "ACCEPT"
      ? Object.fromEntries(Object.entries(result.draft_fields || {}).filter(([key]) => selectedFields[key]))
      : {};
    try {
      await api(`${basePath || `/api/master-content/${itemId}/intelligence`}/${result.work_product_id}/review`, {
        method: "POST",
        headers: { "Idempotency-Key": crypto.randomUUID() },
        body: JSON.stringify({
          decision,
          idempotency_key: crypto.randomUUID(),
          precondition_version: result.review_precondition_version,
          accepted_fields: acceptedFields,
          reason: decision === "ACCEPT" ? "Owner accepted selected Content Library AI suggestions for draft use." : "Owner rejected Content Library AI suggestions.",
        }),
      });
      setReviewStatus(decision);
      if (decision === "ACCEPT" && onApplyDraft) onApplyDraft(acceptedFields);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The AI review decision could not be recorded.");
    } finally { setBusy(null); }
  };
  const output = result?.output || {};
  const citations = result?.citations || [];
  const draftFields = result?.draft_fields || {};
  const renderValue = (value: unknown) => typeof value === "string" ? value : JSON.stringify(value, null, 2);
  const categoryName = (value: unknown) => categories.find((category) => category.id === value)?.label || String(value);
  return <section className="form-governance-section content-library-intelligence" aria-label="Content Library Intelligence">
    <h3>Content Library Intelligence</h3>
    <p>Seven registered, source-grounded skills are available here. Results are immutable advisory work products; accepting a suggestion records your decision and updates only this editable {entityLabel} draft.</p>
    {!itemId && <div className="ai-review-note">Select a current governed source before running AI assistance.</div>}
    {itemId && !sourceId && <div className="ai-review-note">No current governed source revision is available for this {entityLabel}.</div>}
    <div className="v2-governance-actions">
      {CONTENT_LIBRARY_INTELLIGENCE_SKILLS.map(([skillId, label]) => <button key={skillId} type="button" className="button-secondary" disabled={Boolean(busy) || !itemId || !sourceId} onClick={() => void run(skillId)}>{busy === skillId ? "Running…" : label}</button>)}
    </div>
    {error && <div className="dashboard-error" role="alert">{error}</div>}
    {result && <div className="ai-result-review">
      <div className="ai-result-review-head"><b>{reviewStatus ? `Human review: ${reviewStatus}` : "Human review required"}</b><span>{result.work_product_id} · {result.output_class} · canonical mutation: no</span></div>
      <p className="ai-result-summary-text">{output.summary || "Advisory result is ready for human review."}</p>
      <div className="ai-result-meta"><span>Currentness: {result.review_precondition_version ? "CURRENT at capture" : "Not reported"}</span><span>Skill: {result.skill_id}</span><span>Citations: {citations.length || output.citations?.length || 0}</span></div>
      {Object.keys(draftFields).length > 0 && <section className="ai-result-section"><h4>Candidate draft fields</h4><p>Select exactly what should enter the editable {entityLabel} draft. Nothing is saved until you use the normal Save action.</p>{Object.entries(draftFields).map(([key, value]) => <label className="ai-draft-field" key={key}><input type="checkbox" checked={selectedFields[key] !== false} disabled={Boolean(reviewStatus)} onChange={(event) => setSelectedFields((current) => ({ ...current, [key]: event.target.checked }))} /><span><b>{key === "category_id" ? "Category" : key.replaceAll("_", " ")}</b><em>{key === "category_id" ? categoryName(value) : renderValue(value)}</em></span></label>)}</section>}
      {output.candidate_metadata && <AiStructuredObject title="Candidate metadata" value={output.candidate_metadata} valueFormatter={categoryName} />}
      {output.title || output.description ? <section className="ai-result-section"><h4>Description draft</h4>{output.title && <p><b>Title:</b> {output.title}</p>}{output.description && <p><b>Description:</b> {output.description}</p>}{output.keywords?.length > 0 && <p><b>Keywords:</b> {output.keywords.join(", ")}</p>}<small>Draft only: {String(output.draft_only ?? true)}</small></section> : null}
      {output.findings?.length > 0 && <AiStructuredList title="Findings" values={output.findings} />}
      {output.recommendations?.length > 0 && <AiStructuredList title="Recommendations" values={output.recommendations} />}
      {output.blockers?.length > 0 && <AiStructuredList title="Blockers" values={output.blockers} />}
      {output.impacts?.length > 0 && <AiStructuredList title="Impacts" values={output.impacts} />}
      {output.review_flags?.length > 0 && <AiStructuredList title="Review flags" values={output.review_flags} />}
      {output.open_questions?.length > 0 && <AiStructuredList title="Open questions" values={output.open_questions} />}
      {(output.analysis_kind || output.confidence) && <div className="ai-result-meta"><span>{output.analysis_kind ? `Analysis: ${output.analysis_kind}` : ""}</span><span>{output.confidence ? `Confidence: ${output.confidence}` : ""}</span></div>}
      <section className="ai-result-section"><h4>Citations &amp; evidence</h4>{citations.length ? <ol className="ai-citation-list">{citations.map((citation: any) => <li key={`${citation.ordinal}-${citation.source_id}`}><b>{citation.locator_json?.citation_key || `CIT-${String(citation.ordinal).padStart(3, "0")}`}</b><span>{citation.source_type} · {citation.source_id} · version/hash {citation.source_version_or_hash}</span></li>)}</ol> : <p>{(output.citations || []).join(", ") || "No citations returned."}</p>}</section>
      {!reviewStatus ? <div className="ai-review-actions"><button type="button" className="button-primary" disabled={Boolean(busy) || (Object.keys(draftFields).length > 0 && !Object.values(selectedFields).some(Boolean))} onClick={() => void review("ACCEPT")}>Accept selected suggestions</button><button type="button" className="button-secondary" disabled={Boolean(busy)} onClick={() => void review("REJECT")}>Reject result</button></div> : <div className="ai-review-note">Decision recorded. {reviewStatus === "ACCEPT" && onApplyDraft ? "Selected values are now in the editable draft; use Save to persist them." : "No canonical content was changed."}</div>}
    </div>}
  </section>;
}

function AiStructuredList({ title, values }: { title: string; values: unknown[] }) {
  return <section className="ai-result-section"><h4>{title}</h4><ul>{values.map((value, index) => <li key={`${title}-${index}`}>{String(value)}</li>)}</ul></section>;
}

function AiStructuredObject({ title, value, valueFormatter }: { title: string; value: Record<string, unknown>; valueFormatter?: (value: unknown) => string }) {
  return <section className="ai-result-section"><h4>{title}</h4><dl className="ai-result-object">{Object.entries(value).map(([key, entry]) => <div key={key}><dt>{key.replaceAll("_", " ")}</dt><dd>{valueFormatter ? valueFormatter(entry) : typeof entry === "string" ? entry : JSON.stringify(entry)}</dd></div>)}</dl></section>;
}

function V2GovernanceDetails({ item, role, onRefresh }: { item: CanonicalForm; role: string; onRefresh: () => Promise<void> }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const canWrite = ownerRoles.has(role);
  const catalogs = useState<V2Catalogs | null>(null);
  const [catalog, setCatalog] = catalogs;
  useEffect(() => { void api<V2Catalogs>("/api/dashboard-v2/catalogs").then(setCatalog).catch(() => undefined); }, []);
  const name = (kind: keyof V2Catalogs, id?: string | null) => {
    if (!id) return "Any";
    const row = catalog?.[kind]?.find((candidate) => candidate.id === id);
    return row?.name_en || row?.code || id.slice(0, 8);
  };
  const run = async (action: () => Promise<unknown>) => {
    setBusy(true); setError("");
    try { await action(); await onRefresh(); } catch (cause) { setError(cause instanceof Error ? cause.message : "Governance action failed."); } finally { setBusy(false); }
  };
  const profile = item.automation_profiles?.[0];
  const latest = profile?.releases?.[0];
  return <div className="v2-governance-detail">
    <section className="form-governance-section"><h3>Regulatory applicability</h3>
      {(item.applicability || []).length ? <div className="v2-governance-table-wrap"><table className="v2-governance-table"><thead><tr><th>External body</th><th>Jurisdiction</th><th>Service</th><th>Phase</th><th>Source version</th><th>Status</th></tr></thead><tbody>{(item.applicability || []).map((row) => <tr key={row.id}><td>{name("external_bodies", row.external_body_id)}</td><td>{name("jurisdictions", row.jurisdiction_id)}</td><td>{name("service_types", row.service_type_id)}</td><td>{name("lifecycle_phases", row.lifecycle_phase_id)}</td><td><code>{row.source_document_version_id.slice(0, 8)}</code></td><td><span className="tag">{row.status}</span></td></tr>)}</tbody></table></div> : <p className="empty-message">No explicit version-pinned applicability is confirmed.</p>}
    </section>
    <section className="form-governance-section"><h3>Policy and technical source lineage</h3>
      <div className="v2-lineage-columns"><div><b>Requirement policy sources</b>{(item.requirement_policy_lineage || []).length ? item.requirement_policy_lineage?.map((row) => <div className="v2-lineage-row" key={row.id}><span>{row.source_role} · {row.governance_status}</span><code>{row.document_version_id.slice(0, 8)}{row.source_section_id ? ` · section ${row.source_section_id.slice(0, 8)}` : ""}</code></div>) : <p className="empty-message">No policy source pinned.</p>}</div><div><b>Technical rule sources</b>{(item.technical_rule_lineage || []).length ? item.technical_rule_lineage?.map((row) => <div className="v2-lineage-row" key={row.id}><span>{row.source_role} · {row.governance_status}</span><code>{row.document_version_id.slice(0, 8)}{row.source_section_id ? ` · section ${row.source_section_id.slice(0, 8)}` : ""}</code></div>) : <p className="empty-message">No technical source pinned.</p>}</div></div>
    </section>
    <section className="form-governance-section"><h3>Form automation governance</h3>
      {profile ? <><div className="content-detail-grid"><div><span>Profile</span><b>{profile.id.slice(0, 8)} · {profile.automation_status}</b></div><div><span>Source version</span><b>{profile.source_document_version_id.slice(0, 8)} · {profile.source_version_state}</b></div><div><span>Derived readiness</span><b>{profile.readiness?.state?.replaceAll("_", " ") || "Not evaluated"}</b></div><div><span>Mapping release</span><b>{latest ? `${latest.version} · ${latest.status}` : "No release"}</b></div></div>
        {profile.readiness?.blocking_reasons?.length ? <ul>{profile.readiness.blocking_reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul> : null}
        <div className="v2-governance-actions">{canWrite && <><button className="button-secondary" disabled={busy} onClick={() => void run(() => api(`/api/dashboard-v2/profiles/${profile.id}/readiness/evaluate`, { method: "POST" }))}>Evaluate readiness</button>{!latest && <button className="button-secondary" disabled={busy} onClick={() => void run(() => api(`/api/dashboard-v2/forms/${item.id}/mapping-releases`, { method: "POST", body: JSON.stringify({ version: `V2-DRAFT-${crypto.randomUUID().slice(0, 8)}`, mapping_json: {} }) }))}>Create mapping draft</button>}{latest?.status === "DRAFT" && <button className="button-secondary" disabled={busy} onClick={() => void run(() => api(`/api/dashboard-v2/mapping-releases/${latest.id}/validate`, { method: "POST" }))}>Validate draft</button>}</>}</div>
      </> : <>{canWrite && <button className="button-primary" disabled={busy} onClick={() => void run(() => api(`/api/dashboard-v2/forms/${item.id}/automation-profile`, { method: "POST", body: JSON.stringify({ renderer_type: "SYNTHETIC_JSON", semantic_contract_version: "1.0" }) }))}>Create governed automation profile</button>}<p className="empty-message">Automation remains unavailable until an owner creates a source-pinned profile and governed mapping release.</p></>}
      {error && <div className="dashboard-error" role="alert">{error}</div>}
    </section>
  </div>;
}

function FormEditor({
  item,
  categories,
  sourceOptions,
  busy,
  onClose,
  onSave,
}: {
  item?: CanonicalForm;
  categories: Category[];
  sourceOptions: CanonicalForm[];
  busy: boolean;
  onClose: () => void;
  onSave: (request: SaveRequest) => Promise<void>;
}) {
  const [title, setTitle] = useState(item?.title || "");
  const [ref, setRef] = useState("");
  const [category, setCategory] = useState(item?.category?.id || "");
  const [description, setDescription] = useState(item?.description || "");
  const [usedIn, setUsedIn] = useState(item?.used_in || []);
  const [reason, setReason] = useState("");
  const [needsReview, setNeedsReview] = useState(Boolean(item?.needs_review));
  const [reviewNote, setReviewNote] = useState(item?.review_note || "");
  const [file, setFile] = useState<File | null>(null);
  const governedSources = sourceOptions.filter((source) => Boolean(source.current_document_version_id || source.current_version_id));
  const [aiSourceId, setAiSourceId] = useState(item?.id || governedSources[0]?.id || "");
  const applyAiDraft = (fields: Record<string, unknown>) => {
    if (typeof fields.title === "string") setTitle(fields.title);
    if (typeof fields.description === "string") setDescription(fields.description);
    if (typeof fields.category_id === "string" && categories.some((row) => row.id === fields.category_id && row.allowed_content_types.includes("FORM"))) setCategory(fields.category_id);
  };
  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!item) {
      const form = new FormData();
      form.append("content_type", "FORM");
      if (ref.trim()) form.append("ref", ref.trim());
      form.append("title", title);
      if (category) form.append("category_id", category);
      form.append("description", description);
      form.append("used_in", JSON.stringify(usedIn));
      form.append("needs_review", String(needsReview));
      if (reviewNote.trim()) form.append("review_note", reviewNote.trim());
      form.append("file", file as File);
      void onSave({ form });
      return;
    }
    if (file) {
      const form = new FormData();
      form.append("expected_current_version", String(item.version || 0));
      form.append("change_reason", reason);
      form.append("title", title);
      if (category) form.append("category_id", category);
      form.append("description", description);
      form.append("used_in", JSON.stringify(usedIn));
      form.append("needs_review", String(needsReview));
      if (reviewNote.trim()) form.append("review_note", reviewNote.trim());
      form.append("file", file);
      void onSave({ form });
    } else
      void onSave({
        metadata: {
          title,
          category_id: category || null,
          description,
          used_in: usedIn,
          needs_review: needsReview,
          review_note: needsReview ? reviewNote.trim() : null,
          change_reason: reason,
        },
      });
  };
  const action = item
    ? file
      ? "Save as New Version"
      : "Save Changes"
    : "Create Form";
  return (
    <Drawer
      title={item ? `Edit ${item.title}` : "New Form"}
      eyebrow={item ? "EDIT FORM" : "MASTER LIBRARY · FORMS"}
      onClose={onClose}
      footer={
        <>
          <button type="button" className="button-secondary" onClick={onClose}>
            Cancel
          </button>
          <button className="button-primary" disabled={busy}>
            {busy ? "Saving…" : action}
          </button>
        </>
      }
    >
      <form className="content-editor-form" onSubmit={submit}>
        <section className="editor-group">
          <h3>Basic Information</h3>
          <label>
            Form name
            <input
              aria-label="Title / Name"
              required
              value={title}
              onChange={(event) => setTitle(event.target.value)}
            />
          </label>
          <label>
            Reference
            {item ? (
              <input aria-label="Reference" readOnly value={item.ref} />
            ) : (
              <>
                <small>Auto-generated when saved. Example: F-0001.</small>
                <input
                  aria-label="Reference"
                  placeholder="Auto-generated on save"
                  value={ref}
                  onChange={(event) => setRef(event.target.value)}
                />
              </>
            )}
          </label>
          <label>
            Category
            <select
              required
              value={category}
              onChange={(event) => setCategory(event.target.value)}
            >
              <option value="">Choose a category</option>
              {categories
                .filter((row) => row.allowed_content_types.includes("FORM"))
                .map((row) => (
                  <option value={row.id} key={row.id}>
                    {row.label}
                  </option>
                ))}
            </select>
          </label>
          <label>
            Description
            <textarea
              required
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          </label>
        </section>
        <UsedInPicker type="FORM" value={usedIn} onChange={setUsedIn} />
        <section className="editor-group">
          <h3>Status</h3>
          <label className="status-choice"><input type="checkbox" checked={needsReview} onChange={(event) => setNeedsReview(event.target.checked)} /> Needs Review</label>
          {needsReview && <label>Review note<small>Keep this short and useful to the Owner.</small><textarea maxLength={500} value={reviewNote} onChange={(event) => setReviewNote(event.target.value)} placeholder="Why does this form need review?" required /></label>}
        </section>
        <section className="editor-group">
          <h3>Source Document</h3>
          {item && (
            <div className="current-source">
              <b>Current source</b>
              <span>
                {item.current_source_filename || "Source file recorded"}
              </span>
              <small>
                Version {item.version || "Draft"} · PDF preview where supported
                · Download available
              </small>
            </div>
          )}
          <label>
            {item ? "Replace source file (optional)" : "Upload source document"}
            <input
              aria-label="File"
              type="file"
              accept=".pdf,.docx,.doc"
              required={!item}
              onChange={(event) => setFile(event.target.files?.[0] || null)}
            />
            {item && file && (
              <small>
                Replacing the source document will create a new version.
              </small>
            )}
          </label>
        </section>
        <section className="editor-group">
          <h3>AI-assisted draft</h3>
          {!item && <label>Governed source for AI assistance<small>AI reads the selected current DocumentVersion. It does not become part of this new Form until you upload and save it.</small><select aria-label="Governed source for AI assistance" value={aiSourceId} onChange={(event) => setAiSourceId(event.target.value)}><option value="">Choose a current governed source</option>{governedSources.map((source) => <option key={source.id} value={source.id}>{source.ref} · {source.title}</option>)}</select></label>}
          <ContentLibraryAiAssist itemId={item?.id || aiSourceId || undefined} sourceId={item?.id || aiSourceId || undefined} categories={categories} onApplyDraft={applyAiDraft} />
        </section>
        {item && (
          <section className="editor-group">
            <h3>Change Reason</h3>
            <label>
              Why are you making this change?
              <input
                required
                value={reason}
                onChange={(event) => setReason(event.target.value)}
              />
            </label>
          </section>
        )}
      </form>
    </Drawer>
  );
}

function FormHistory({
  history,
  onClose,
}: {
  history: { itemId: string; title: string; versions: Version[] };
  onClose: () => void;
}) {
  return (
    <Drawer
      title={history.title}
      eyebrow="VERSION HISTORY"
      onClose={onClose}
      footer={
        <button type="button" className="button-secondary" onClick={onClose}>
          Close
        </button>
      }
      wide
    >
      <div className="history-list">
        {history.versions.length ? (
          history.versions.map((version) => (
            <article className="history-card" key={version.id}>
              <div>
                <strong>Version {version.version}</strong>
                <StatusBadge value={version.status} hasVersion />
                <span>{version.file_name}</span>
              </div>
              <small>
                {formatDateTime(version.updated_at)} · {version.updated_by} ·{" "}
                {version.change_reason || "No change reason"}
              </small>
              <div className="history-card-actions">
                <span>
                  {version.rendition?.available
                    ? "Preview PDF available"
                    : "Source document"}
                </span>
              <a
                className="table-action action-view"
                href={`/api/master-content/${history.itemId}/versions/${version.id}/download`}
                download={version.file_name}
              >
                Download
              </a>
              </div>
            </article>
          ))
        ) : (
          <p className="empty-message">No version history is available.</p>
        )}
      </div>
    </Drawer>
  );
}

function UsedInChips({ values = [] }: { values?: string[] }) {
  return values.length ? (
    <div className="used-in-chips">
      {values.map((value) => (
        <span className="used-in-chip" key={value}>
          {MODULE_LABELS[value] || value}
        </span>
      ))}
    </div>
  ) : (
    <span className="not-assigned">Not assigned</span>
  );
}
function StatusBadge({
  value,
  hasVersion,
}: {
  value?: string;
  hasVersion: boolean;
}) {
  return (
    <span
      className={`status-badge status-${friendlyStatus(value, hasVersion).toLowerCase().replaceAll(" ", "-")}`}
    >
      {friendlyStatus(value, hasVersion)}
    </span>
  );
}
function EmptyState({ noun, filtered }: { noun: string; filtered: boolean }) {
  return (
    <div className="dashboard-empty-state">
      <strong>
        {filtered ? `No ${noun} match these filters.` : `No ${noun} yet.`}
      </strong>
      <span>
        {filtered
          ? "Try changing your search or filters."
          : `Add the first ${noun.slice(0, -1)} to the AMEC master library.`}
      </span>
    </div>
  );
}
function formatDate(value?: string) {
  return value
    ? new Date(value).toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : "—";
}
function formatDateTime(value: string) {
  return new Date(value).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}
async function downloadForm(itemId: string) {
  const response = await fetch(`/api/master-content/${itemId}/download`, {
    headers: {
      "X-Dev-Role":
        sessionStorage.getItem("proposalops-role") || "SYSTEM_ADMIN",
    },
  });
  if (!response.ok) throw new Error("The Form could not be opened.");
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "form";
  link.click();
  URL.revokeObjectURL(url);
}
async function downloadFormVersion(
  itemId: string,
  versionId: string,
  fileName: string,
) {
  const response = await fetch(
    `/api/master-content/${itemId}/versions/${versionId}/download`,
    {
      headers: {
        "X-Dev-Role":
          sessionStorage.getItem("proposalops-role") || "SYSTEM_ADMIN",
      },
    },
  );
  if (!response.ok) throw new Error("The Form version could not be opened.");
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  link.click();
  URL.revokeObjectURL(url);
}
