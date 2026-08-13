import { useEffect, useState } from "react";
import { api } from "./api";
import {
  AIAssistCompact,
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
  governanceMode = false,
  filters,
}: {
  role: string;
  surface?: "DASHBOARD" | "ADMINISTRATION";
  compact?: boolean;
  governanceMode?: boolean;
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
  const canWrite = ownerRoles.has(role);
  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams({ content_type: "FORM" });
      if (filters?.q) params.set("q", filters.q);
      if (filters?.category) params.set("category_label", filters.category);
      if (filters?.status) params.set("status", filters.status);
      if (filters?.module) params.set("module", filters.module);
      if (governanceMode) Object.entries(governanceFilters).forEach(([key, value]) => { if (value) params.set(key, value); });
      const [content, categoryRows] = await Promise.all([
        api<CanonicalForm[]>(`/api/master-content?${params}`),
        api<Category[]>("/api/master-content/categories"),
      ]);
      setForms(content);
      setCategories(categoryRows);
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
  }, [filters?.q, filters?.category, filters?.status, filters?.module, governanceMode, governanceFilters.ownership, governanceFilters.artifact_kind, governanceFilters.currentness, governanceFilters.readiness, governanceFilters.quality_state, governanceFilters.restricted_sample, governanceFilters.language]);
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
  const filtered = Boolean(
    filters?.q || filters?.category || filters?.status || filters?.module,
  );
  return (
    <section
      id="forms"
      className={`panel dashboard-section canonical-forms-library ${compact ? "canonical-forms-library-compact" : ""}`}
      data-testid={`${governanceMode ? "dashboard-v2" : surface.toLowerCase()}-forms`}
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
      {governanceMode && <details className="forms-advanced-filters">
        <summary>Advanced governance filters</summary>
        <div className="dashboard-filter-bar forms-governance-filters">
          {([['ownership', 'Content ownership', ['AMEC_OWNED', 'EXTERNAL_OFFICIAL', 'EXTERNAL_REFERENCE', 'REFERENCE_SAMPLE', 'NEEDS_REVIEW']], ['artifact_kind', 'Artifact kind', ['AUTHORITY_FORM', 'AMEC_FORM', 'CHECKLIST', 'AUTHORIZATION', 'SERVICE_REQUEST', 'OTHER', 'UNKNOWN']], ['currentness', 'Currentness', ['UNVERIFIED', 'VERIFIED_CURRENT', 'VERIFIED_NOT_CURRENT', 'NEEDS_REVIEW']], ['readiness', 'Readiness', ['REFERENCE_ONLY', 'BLOCKED', 'MANUAL_USE_READY', 'SUPERSEDED']], ['quality_state', 'Quality state', ['OPEN', 'ACCEPTED_RISK', 'RESOLVED']], ['language', 'Language', ['AR', 'EN', 'AR_EN_BILINGUAL', 'OTHER']]] as const).map(([key, label, options]) => <label key={key}>{label}<select aria-label={label} value={governanceFilters[key]} onChange={(event) => setGovernanceFilters((current) => ({ ...current, [key]: event.target.value }))}><option value="">All</option>{options.map((option) => <option key={option} value={option}>{option.replaceAll('_', ' ')}</option>)}</select></label>)}
          <label>Restricted sample<select aria-label="Restricted sample" value={governanceFilters.restricted_sample} onChange={(event) => setGovernanceFilters((current) => ({ ...current, restricted_sample: event.target.value }))}><option value="">All</option><option value="true">Restricted</option><option value="false">Not restricted</option></select></label>
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
          governanceMode={governanceMode}
          onEdit={setEditor}
          onOpen={async (form) => setDetails(await api<CanonicalForm>(`/api/master-content/${form.id}`))}
          onHistory={async (form) => {
            const detail = await api<CanonicalForm>(
              `/api/master-content/${form.id}`,
            );
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
          busy={busy}
          onClose={() => setEditor(undefined)}
          onSave={save}
        />
      )}
      {history && (
        <FormHistory history={history} onClose={() => setHistory(null)} />
      )}
      {details && <FormDetails item={details} governanceMode={governanceMode} onClose={() => setDetails(null)} />}
    </section>
  );
}

function FormTable({
  forms,
  canWrite,
  governanceMode,
  onEdit,
  onOpen,
  onHistory,
}: {
  forms: CanonicalForm[];
  canWrite: boolean;
  governanceMode: boolean;
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
            {!governanceMode && <th>Version</th>}
            <th>Reference</th>
            <th>Form</th>
            <th>Category</th>
            <th>Description</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {forms.map((form, index) => (
            <tr key={form.id}>
              <td>{form.serial_number || index + 1}</td>
              {!governanceMode && <td>{versionLabel(form.version)}</td>}
              <td>
                <code className="content-reference">{form.ref}</code>
              </td>
              <td>
                <b>{form.title}</b>
                {governanceMode && <><small className="table-subline">Version {form.version || "—"}</small><div className="governance-badges">{(form.governance?.badges || []).slice(0, 2).map((badge) => <span key={badge} className="tag">{badge}</span>)}</div></>}
              </td>
              <td>{form.category?.label || "Uncategorized"}</td>
              <td
                className="description-cell"
                title={form.description || "No description"}
              >
                {form.description || "No description"}
              </td>
              <td className="dashboard-actions">
                <button className="table-action action-view" onClick={() => onOpen(form)}>Open</button>
                {canWrite && (
                  <button
                    className="table-action action-edit"
                    onClick={() => onEdit(form)}
                  >
                    Edit
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

function FormDetails({ item, governanceMode, onClose }: { item: CanonicalForm; governanceMode: boolean; onClose: () => void }) {
  const governance = item.governance || {};
  const profile = governance.profile || {};
  const readiness = governance.readiness || { state: "BLOCKED", blocking_reasons: ["Governance profile is not available."], warnings: [] };
  if (!governanceMode) return <Drawer title={`${item.ref} · ${item.title}`} eyebrow="FORM DETAILS" onClose={onClose} footer={<button type="button" className="button-secondary" onClick={onClose}>Close</button>}>
    <div className="content-detail-grid"><div><span>Category</span><b>{item.category?.label || "Uncategorized"}</b></div><div><span>Version</span><b>{versionLabel(item.version)}</b></div><div><span>Status</span><b>{friendlyStatus(item.version_status, Boolean(item.version))}</b></div><div><span>Used In</span><b>{(item.used_in || []).map(module => MODULE_LABELS[module] || module).join(", ") || "Not assigned"}</b></div></div>
    <p className="detail-description">{item.description || "No description"}</p>
    <div className="detail-purpose-list"><h3>Purpose bindings</h3>{(item.purpose_bindings || []).map(binding => <span key={`${binding.module}-${binding.usage_type}`}>{MODULE_LABELS[binding.module] || binding.module} · {binding.usage_type}</span>)}</div>
    {!profile.restricted_reference_sample && <a className="button-secondary" href={`/api/master-content/${item.id}/download`} download>Download current source</a>}
  </Drawer>;
  return <Drawer title={`${item.ref} · ${item.title}`} eyebrow="FORM DETAILS" onClose={onClose} footer={<button type="button" className="button-secondary" onClick={onClose}>Close</button>}>
    <section className="form-governance-section"><h3>Overview</h3><div className="content-detail-grid">
      <div><span>Category</span><b>{item.category?.label || "Uncategorized"}</b></div>
      <div><span>Version</span><b>{versionLabel(item.version)}</b></div>
      <div><span>Status</span><b>{friendlyStatus(item.version_status, Boolean(item.version))}</b></div>
      <div><span>Used In</span><b>{(item.used_in || []).map(module => MODULE_LABELS[module] || module).join(", ") || "Not assigned"}</b></div>
      <div><span>Artifact kind</span><b>{String(profile.artifact_kind || "UNKNOWN").replaceAll("_", " ")}</b></div>
      <div><span>Readiness</span><b>{readiness.state.replaceAll("_", " ")}</b></div>
    </div><p className="detail-description">{item.description || "No description"}</p></section>
    <section className="form-governance-section"><h3>Source &amp; Authority</h3><div className="content-detail-grid"><div><span>Ownership</span><b>{String(profile.content_ownership_class || "NEEDS_REVIEW").replaceAll("_", " ")}</b></div><div><span>Publisher / Origin</span><b>{profile.publisher_name || "Not recorded"}</b></div><div><span>Official Form No.</span><b>{profile.official_form_no || "Not recorded"}</b></div><div><span>Issue / Date</span><b>{[profile.official_issue_no, profile.official_issue_date].filter(Boolean).join(" · ") || "Not recorded"}</b></div><div><span>Language</span><b>{String(profile.language_profile || "OTHER").replaceAll("_", " ")}</b></div><div><span>Currentness</span><b>{String(profile.currentness_status || "UNVERIFIED").replaceAll("_", " ")}</b></div></div></section>
    <section className="form-governance-section"><h3>Quality &amp; Sensitivity</h3><p>{profile.sensitivity_flags?.length ? `Sensitive flags: ${profile.sensitivity_flags.join(", ")}` : "No sensitivity flags recorded."}</p>{(governance.quality_flags || []).map((flag: any) => <div className={`quality-flag quality-${String(flag.severity).toLowerCase()}`} key={flag.id}><b>{String(flag.code).replaceAll("_", " ")}</b><span>{flag.status} · {flag.description}</span></div>)}</section>
    <section className="form-governance-section"><h3>Source Sections</h3>{(governance.source_sections || []).length ? (governance.source_sections || []).map((section: any) => <div className="source-section-row" key={section.id}><b>{section.label}</b><span>{section.locator_type} {section.page_start ? `· p.${section.page_start}${section.page_end && section.page_end !== section.page_start ? `–${section.page_end}` : ""}` : ""} · exact version {section.document_version_id.slice(0, 8)}</span></div>) : <p>No exact source sections pinned.</p>}</section>
    <section className="form-governance-section readiness-panel"><h3>Readiness</h3><strong>{readiness.state.replaceAll("_", " ")}</strong>{readiness.blocking_reasons.length > 0 && <><b>Blocking reasons</b><ul>{readiness.blocking_reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul></>}{readiness.warnings.length > 0 && <><b>Warnings</b><ul>{readiness.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></>}</section>
    <div className="detail-purpose-list"><h3>Purpose bindings</h3>{(item.purpose_bindings || []).map(binding => <span key={`${binding.module}-${binding.usage_type}`}>{MODULE_LABELS[binding.module] || binding.module} · {binding.usage_type}</span>)}</div>
    {!profile.restricted_reference_sample && <a className="button-secondary" href={`/api/master-content/${item.id}/download`} download>Download current source</a>}
  </Drawer>;
}

function FormEditor({
  item,
  categories,
  busy,
  onClose,
  onSave,
}: {
  item?: CanonicalForm;
  categories: Category[];
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
  const [file, setFile] = useState<File | null>(null);
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
      form.append("file", file);
      void onSave({ form });
    } else
      void onSave({
        metadata: {
          title,
          category_id: category || null,
          description,
          used_in: usedIn,
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
        <AIAssistCompact />
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
