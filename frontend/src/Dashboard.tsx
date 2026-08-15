import { useEffect, useMemo, useState } from "react";
import { api } from "./api";
import { CanonicalFormsLibrary } from "./MasterContentForms";
import {
  AIAssistCompact,
  CONTENT_LABELS,
  Drawer,
  MODULE_LABELS,
  UsedInPicker,
  friendlyStatus,
  MODULE_OPTIONS,
  versionLabel,
} from "./masterContentUi";

type Category = {
  id: string;
  label: string;
  allowed_content_types: string[];
  source_kind?: string;
};
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
type MasterItem = {
  id: string;
  serial_number?: number;
  ref: string;
  content_type: "REPORT" | "ENGINEERING_WORK";
  title: string;
  category?: { id: string; label: string } | null;
  description?: string;
  used_in?: string[];
  purpose_bindings?: { module: string; usage_type: string; active: boolean }[];
  source_type_code?: string | null;
  engineering_metadata?: Record<string, unknown>;
  version?: number;
  version_status: string;
  current_source_filename?: string;
  updated?: string;
  versions?: Version[];
};
type DefinitionRevision = {
  id: string;
  revision: number;
  category?: string;
  description: string;
  used_in?: string[];
  changed_by: string;
  changed_at: string;
  change_reason?: string;
  status: string;
};
type Definition = {
  id: string;
  serial_number?: number;
  ref?: string;
  term: string;
  category?: string;
  description?: string;
  used_in?: string[];
  status?: string;
  revision?: number;
  updated?: string;
  revisions?: DefinitionRevision[];
};
type SaveRequest = { form?: FormData; metadata?: Record<string, unknown> };
type MasterType = "REPORT" | "ENGINEERING_WORK";

const ownerRoles = new Set(["SYSTEM_ADMIN", "OWNER_SPONSOR"]);

type DashboardFormSummary = {
  owner_status?: "Current" | "Needs Review" | "Inactive";
  needs_review?: boolean;
  current_document_version_id?: string | null;
};

export function CurrentDashboard({ role }: { role: string }) {
  const [items, setItems] = useState<MasterItem[]>([]);
  const [definitions, setDefinitions] = useState<Definition[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [status, setStatus] = useState("");
  const [module, setModule] = useState("");
  const [editor, setEditor] = useState<{
    type: MasterType;
    item?: MasterItem;
  } | null>(null);
  const [definitionEditor, setDefinitionEditor] = useState<
    Definition | null | undefined
  >(undefined);
  const [history, setHistory] = useState<{
    title: string;
    itemId?: string;
    versions?: Version[];
    revisions?: DefinitionRevision[];
  } | null>(null);
  const [details, setDetails] = useState<MasterItem | Definition | null>(null);
  const [busy, setBusy] = useState(false);
  const canWrite = ownerRoles.has(role);
  const filtersActive = Boolean(query || category || status || module);
  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams({ q: query });
      if (category) params.set("category_label", category);
      if (status) params.set("owner_status", status);
      if (module) params.set("module", module);
      const defParams = new URLSearchParams({ q: query });
      if (category) defParams.set("category", category);
      if (status) defParams.set("status", status);
      if (module) defParams.set("module", module);
      const [master, defs, cats] = await Promise.all([
        api<MasterItem[]>(`/api/master-content?${params}`),
        api<Definition[]>(`/api/definitions?${defParams}`),
        api<Category[]>("/api/master-content/categories"),
      ]);
      setItems(master);
      setDefinitions(defs);
      setCategories(cats);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Dashboard data could not be loaded.",
      );
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    void load();
  }, [query, category, status, module]);
  const categoryOptions = useMemo(
    () =>
      Array.from(
        new Map(categories.map((item) => [item.label, item])).values(),
      ).sort((a, b) => a.label.localeCompare(b.label)),
    [categories],
  );
  const clearFilters = () => {
    setQuery("");
    setCategory("");
    setStatus("");
    setModule("");
  };
  const saveMaster = async (request: SaveRequest) => {
    setBusy(true);
    try {
      if (request.metadata && editor?.item)
        await api(`/api/master-content/${editor.item.id}/metadata`, {
          method: "PATCH",
          body: JSON.stringify(request.metadata),
          headers: {
            "Content-Type": "application/json",
            "Idempotency-Key": crypto.randomUUID(),
            "X-Source-Surface": "DASHBOARD",
          },
        });
      else if (request.form)
        await api(
          editor?.item
            ? `/api/master-content/${editor.item.id}/versions`
            : "/api/master-content",
          {
            method: "POST",
            body: request.form,
            headers: {
              "Idempotency-Key": crypto.randomUUID(),
              "X-Source-Surface": "DASHBOARD",
            },
          },
        );
      setEditor(null);
      await load();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "The change could not be saved.",
      );
    } finally {
      setBusy(false);
    }
  };
  const saveDefinition = async (data: Record<string, unknown>) => {
    setBusy(true);
    try {
      await api(
        definitionEditor
          ? `/api/definitions/${definitionEditor.id}/revisions`
          : "/api/definitions",
        { method: "POST", body: JSON.stringify(data) },
      );
      setDefinitionEditor(undefined);
      await load();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "The definition could not be saved.",
      );
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="dashboard-page current-dashboard-v2" data-dashboard-root="v2-evolution" data-testid="current-dashboard">
      <header className="dashboard-page-header">
        <div>
          <span className="eyebrow">AMEC · MASTER / REFERENCE CONTENT</span>
          <h2>Dashboard</h2>
          <p>Govern the shared Forms, Reports, Engineering Works, and Definitions foundation.</p>
        </div>
        <div className="dashboard-counts">
          <span>
            <b>
              {items.filter((item) => item.content_type === "REPORT").length}
            </b>{" "}
            Reports
          </span>
          <span>
            <b>
              {
                items.filter((item) => item.content_type === "ENGINEERING_WORK")
                  .length
              }
            </b>{" "}
            Engineering Works
          </span>
          <span>
            <b>{definitions.length}</b> Definitions
          </span>
          <a className="button-secondary" href="/dashboard/inputs-go-live">
            Inputs &amp; Go-Live
          </a>
        </div>
      </header>
      <DashboardGovernanceOverview />
      <DashboardLibraryNavigation />
      <section id="categories" className="dashboard-filter-bar" aria-label="Dashboard filters">
        <label>
          Search
          <input
            aria-label="Search master content"
            placeholder="Search title, term, or reference"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
        <label>
          Category
          <select
            aria-label="Filter by category"
            value={category}
            onChange={(event) => setCategory(event.target.value)}
          >
            <option value="">All categories</option>
            {categoryOptions.map((item) => (
              <option value={item.label} key={item.label}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Status
          <select
            aria-label="Filter by status"
            value={status}
            onChange={(event) => setStatus(event.target.value)}
          >
            <option value="">All statuses</option>
            <option value="CURRENT">Current</option>
            <option value="NEEDS_REVIEW">Needs Review</option>
            <option value="INACTIVE">Inactive</option>
          </select>
        </label>
        <label>
          Used In
          <select
            aria-label="Filter by Used In"
            value={module}
            onChange={(event) => setModule(event.target.value)}
          >
            <option value="">All modules</option>
            {Object.entries(MODULE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        {filtersActive && (
          <button
            className="button-secondary clear-filter-button"
            onClick={clearFilters}
          >
            Clear filters
          </button>
        )}
      </section>
      {error && (
        <div className="dashboard-error" role="alert">
          <b>Dashboard unavailable</b>
          <span>{error}</span>
          <button className="button-secondary" onClick={() => void load()}>
            Retry
          </button>
        </div>
      )}
      {loading && (
        <div className="panel dashboard-state" role="status">
          Loading master content…
        </div>
      )}
      {!loading && !error && (
        <>
          <CanonicalFormsLibrary
            role={role}
            filters={{ q: query, category, status, module }}
          />
          <MasterSection
            type="REPORT"
            items={items.filter((item) => item.content_type === "REPORT")}
            canWrite={canWrite}
            filtered={filtersActive}
            onNew={() => setEditor({ type: "REPORT" })}
            onEdit={(item) => setEditor({ type: "REPORT", item })}
            onOpen={async (item) => setDetails(await api<MasterItem>(`/api/master-content/${item.id}`))}
            onHistory={async (item) => {
              const detail = await api<MasterItem>(
                `/api/master-content/${item.id}`,
              );
              setHistory({
                itemId: item.id,
                title: `${item.ref} · ${item.title}`,
                versions: detail.versions,
              });
            }}
          />
          <MasterSection
            type="ENGINEERING_WORK"
            items={items.filter(
              (item) => item.content_type === "ENGINEERING_WORK",
            )}
            canWrite={canWrite}
            filtered={filtersActive}
            onNew={() => setEditor({ type: "ENGINEERING_WORK" })}
            onEdit={(item) => setEditor({ type: "ENGINEERING_WORK", item })}
            onOpen={async (item) => setDetails(await api<MasterItem>(`/api/master-content/${item.id}`))}
            onHistory={async (item) => {
              const detail = await api<MasterItem>(
                `/api/master-content/${item.id}`,
              );
              setHistory({
                itemId: item.id,
                title: `${item.ref} · ${item.title}`,
                versions: detail.versions,
              });
            }}
          />
          <DefinitionSection
            definitions={definitions}
            canWrite={canWrite}
            filtered={filtersActive}
            onNew={() => setDefinitionEditor(null)}
            onEdit={setDefinitionEditor}
            onOpen={async (item) => setDetails(await api<Definition>(`/api/definitions/${item.id}`))}
            onHistory={async (item) => {
              const detail = await api<Definition>(
                `/api/definitions/${item.id}`,
              );
              setHistory({
                title: `${item.ref || "Definition"} · ${item.term}`,
                revisions: detail.revisions,
              });
            }}
          />
        </>
      )}
      {editor && (
        <MasterEditor
          type={editor.type}
          item={editor.item}
          categories={categories}
          busy={busy}
          onClose={() => setEditor(null)}
          onSave={saveMaster}
        />
      )}
      {definitionEditor !== undefined && (
        <DefinitionEditor
          item={definitionEditor || undefined}
          categories={categories}
          busy={busy}
          onClose={() => setDefinitionEditor(undefined)}
          onSave={saveDefinition}
        />
      )}
      {history && (
        <HistoryDrawer history={history} onClose={() => setHistory(null)} />
      )}
      {details && <ContentDetails item={details} onClose={() => setDetails(null)} />}
    </div>
  );
}

function DashboardGovernanceOverview() {
  const [forms, setForms] = useState<DashboardFormSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    void api<DashboardFormSummary[]>("/api/master-content?content_type=FORM")
      .then(setForms)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, []);

  const count = (status: DashboardFormSummary["owner_status"]) =>
    forms.filter((form) => form.owner_status === status).length;

  return (
    <section className="dashboard-v2-overview" aria-label="Dashboard governance overview" data-testid="dashboard-governance-overview">
      <div className="dashboard-v2-overview-heading">
        <div>
          <span className="eyebrow">GOVERNANCE OVERVIEW</span>
          <h3>Canonical control plane</h3>
          <p>One governed view of currentness, review state, source authority, and immutable version history.</p>
        </div>
        <span className="dashboard-v2-overview-state">{error ? "Summary unavailable" : loading ? "Reading canonical Forms…" : String(forms.length) + " canonical Forms"}</span>
      </div>
      <div className="dashboard-v2-overview-grid">
        <article className="dashboard-v2-summary-card" data-testid="dashboard-current-summary"><span>Current</span><strong>{loading ? "—" : count("Current")}</strong><small>Eligible business status</small></article>
        <article className="dashboard-v2-summary-card dashboard-v2-summary-review" data-testid="dashboard-review-summary"><span>Needs Review</span><strong>{loading ? "—" : count("Needs Review")}</strong><small>Visible, not resolver eligible</small></article>
        <article className="dashboard-v2-summary-card" data-testid="dashboard-inactive-summary"><span>Inactive</span><strong>{loading ? "—" : count("Inactive")}</strong><small>Historical versions retained</small></article>
        <article className="dashboard-v2-source-card" data-testid="dashboard-source-authority-panel"><span className="eyebrow">SOURCE / VERSION</span><strong>Canonical records remain linked</strong><small>MasterContentItem → Document → DocumentVersion</small></article>
      </div>
    </section>
  );
}

function DashboardLibraryNavigation() {
  return (
    <nav className="dashboard-v2-library-nav" aria-label="Dashboard master libraries" data-testid="dashboard-library-navigation">
      <a href="#forms"><span className="eyebrow">PRIMARY LIBRARY</span><strong>Forms</strong><small>Governed templates and automation readiness</small></a>
      <a href="#reports"><span className="eyebrow">REFERENCE LIBRARY</span><strong>Reports</strong><small>Reusable reporting references</small></a>
      <a href="#engineering-works"><span className="eyebrow">TECHNICAL LIBRARY</span><strong>Engineering Works</strong><small>Controlled technical references</small></a>
      <a href="#definitions"><span className="eyebrow">SEMANTIC LIBRARY</span><strong>Definitions</strong><small>Shared business language</small></a>
    </nav>
  );
}

function MasterSection({
  type,
  items,
  canWrite,
  filtered,
  onNew,
  onEdit,
  onOpen,
  onHistory,
}: {
  type: "REPORT" | "ENGINEERING_WORK";
  items: MasterItem[];
  canWrite: boolean;
  filtered: boolean;
  onNew: () => void;
  onEdit: (item: MasterItem) => void;
  onOpen: (item: MasterItem) => void;
  onHistory: (item: MasterItem) => void;
}) {
  const label = CONTENT_LABELS[type];
  return (
    <section
      id={type === "ENGINEERING_WORK" ? "engineering-works" : "reports"}
      className="panel dashboard-section"
      data-testid={`dashboard-${type.toLowerCase()}`}
    >
      <div className="dashboard-section-head">
        <div>
          <span className="eyebrow">MASTER LIBRARY</span>
          <h3>
            {type === "ENGINEERING_WORK" ? "Engineering Works" : "Reports"}
          </h3>
          <p className="section-description">
            {type === "ENGINEERING_WORK"
              ? "Controlled technical references for engineering and permit work."
              : "Reusable AMEC reports and reporting references."}
          </p>
        </div>
        <div className="section-head-actions">
          <span className="record-count">
            {items.length} {items.length === 1 ? "record" : "records"}
          </span>
          {canWrite && (
            <button className="button-primary" onClick={onNew}>
              New {label}
            </button>
          )}
        </div>
      </div>
      {items.length ? (
        <div className="dashboard-table-wrap">
          <table className="dashboard-table">
            <thead>
              <tr>
                <th>S/N</th>
                <th>Version</th>
                <th>Reference</th>
                <th>{type === "ENGINEERING_WORK" ? "Document" : "Report"}</th>
                <th>Category</th>
                <th>Description</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, index) => (
                <tr key={item.id}>
                  <td>{item.serial_number || index + 1}</td>
                  <td>{versionLabel(item.version)}</td>
                  <td>
                    <code className="content-reference">{item.ref}</code>
                  </td>
                  <td>
                    <b>{item.title}</b>
                  </td>
                  <td>{item.category?.label || "Uncategorized"}</td>
                  <td
                    className="description-cell"
                    title={item.description || "No description"}
                  >
                    {item.description || "No description"}
                  </td>
                  <td className="dashboard-actions">
                    <button className="table-action action-view" onClick={() => onOpen(item)}>Open</button>
                    {canWrite && (
                      <button
                        className="table-action action-edit"
                        onClick={() => onEdit(item)}
                      >
                        Edit
                      </button>
                    )}
                    <button
                      className="table-action action-history"
                      onClick={() => onHistory(item)}
                    >
                      History
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState
          noun={type === "ENGINEERING_WORK" ? "engineering works" : "reports"}
          filtered={filtered}
        />
      )}
    </section>
  );
}

function DefinitionSection({
  definitions,
  canWrite,
  filtered,
  onNew,
  onEdit,
  onOpen,
  onHistory,
}: {
  definitions: Definition[];
  canWrite: boolean;
  filtered: boolean;
  onNew: () => void;
  onEdit: (item: Definition) => void;
  onOpen: (item: Definition) => void;
  onHistory: (item: Definition) => void;
}) {
  return (
    <section
      id="definitions"
      className="panel dashboard-section"
      data-testid="dashboard-definitions"
    >
      <div className="dashboard-section-head">
        <div>
          <span className="eyebrow">STRUCTURED SEMANTICS</span>
          <h3>Definitions</h3>
          <p className="section-description">
            Shared business language for client, project, proposal, and permit
            work.
          </p>
        </div>
        <div className="section-head-actions">
          <span className="record-count">
            {definitions.length}{" "}
            {definitions.length === 1 ? "record" : "records"}
          </span>
          {canWrite && (
            <button className="button-primary" onClick={onNew}>
              New Definition
            </button>
          )}
        </div>
      </div>
      {definitions.length ? (
        <div className="dashboard-table-wrap">
          <table className="dashboard-table">
            <thead>
              <tr>
                <th>S/N</th>
                <th>Reference</th>
                <th>Term</th>
                <th>Category</th>
                <th>Meaning</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {definitions.map((item, index) => (
                <tr key={item.id}>
                  <td>{item.serial_number || index + 1}</td>
                  <td>
                    <code className="content-reference">
                      {item.ref || "Unassigned"}
                    </code>
                  </td>
                  <td>
                    <b>{item.term}</b>
                  </td>
                  <td>{item.category || "Uncategorized"}</td>
                  <td
                    className="description-cell"
                    title={item.description || "No meaning recorded"}
                  >
                    {item.description || "No meaning recorded"}
                  </td>
                  <td className="dashboard-actions">
                    <button className="table-action action-view" onClick={() => onOpen(item)}>Open</button>
                    {canWrite && (
                      <button
                        className="table-action action-edit"
                        onClick={() => onEdit(item)}
                      >
                        Edit
                      </button>
                    )}
                    <button
                      className="table-action action-history"
                      onClick={() => onHistory(item)}
                    >
                      History
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState noun="definitions" filtered={filtered} />
      )}
    </section>
  );
}

function MasterEditor({
  type,
  item,
  categories,
  busy,
  onClose,
  onSave,
}: {
  type: MasterType;
  item?: MasterItem;
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
  const [metadata, setMetadata] = useState(
    JSON.stringify(item?.engineering_metadata || {}, null, 2),
  );
  const [sourceType, setSourceType] = useState(item?.source_type_code || "");
  const [discipline, setDiscipline] = useState(String(item?.engineering_metadata?.discipline || "GENERAL"));
  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!item) {
      const form = new FormData();
      form.append("content_type", type);
      if (ref.trim()) form.append("ref", ref.trim());
      form.append("title", title);
      if (category) form.append("category_id", category);
      form.append("description", description);
      form.append("used_in", JSON.stringify(usedIn));
      if (type === "ENGINEERING_WORK") {
        if (sourceType) form.append("source_type_code", sourceType);
        form.append("engineering_metadata", JSON.stringify({ ...parseJson(metadata), discipline }));
      }
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
      if (type === "ENGINEERING_WORK") {
        if (sourceType) form.append("source_type_code", sourceType);
        form.append("engineering_metadata", JSON.stringify({ ...parseJson(metadata), discipline }));
      }
      form.append("file", file);
      void onSave({ form });
    } else
      void onSave({
        metadata: {
          title,
          category_id: category || null,
          description,
          used_in: usedIn,
          engineering_metadata:
            type === "ENGINEERING_WORK" ? { ...parseJson(metadata), discipline, source_type_code: sourceType || undefined } : null,
          source_type_code: type === "ENGINEERING_WORK" ? sourceType || null : null,
          change_reason: reason,
        },
      });
  };
  const label = CONTENT_LABELS[type];
  const action = item
    ? file
      ? "Save as New Version"
      : "Save Changes"
    : `Create ${label}`;
  return (
    <Drawer
      title={item ? `Edit ${item.title}` : `New ${label}`}
      eyebrow={
        item
          ? `EDIT ${label.toUpperCase()}`
          : `MASTER LIBRARY · ${label.toUpperCase()}`
      }
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
            {type === "ENGINEERING_WORK"
              ? "Engineering Work name"
              : "Report name"}
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
                <small>
                  Auto-generated when saved. Example:{" "}
                  {type === "REPORT" ? "R-0001" : "E-0001"}.
                </small>
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
                .filter((row) => row.allowed_content_types.includes(type))
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
        <UsedInPicker type={type} value={usedIn} onChange={setUsedIn} />
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
        {type === "ENGINEERING_WORK" && (
          <section className="editor-group">
            <h3>Engineering reference details</h3>
            <label>
              Source Type
              <select aria-label="Engineering Source Type" required value={sourceType} onChange={(event) => setSourceType(event.target.value)}>
                <option value="">Choose a source type</option>
                {['REGULATION','QCS','MUNICIPALITY_COMMENT','AUTHORITY_GUIDANCE','ENGINEERING_STANDARD','DESIGN_GUIDE','TECHNICAL_REFERENCE','OTHER'].map(value => <option key={value} value={value}>{value.replaceAll('_', ' ')}</option>)}
              </select>
            </label>
            <label>
              Discipline
              <select aria-label="Engineering Discipline" value={discipline} onChange={(event) => setDiscipline(event.target.value)}>
                {['GENERAL','DESIGN','ARCHITECTURE','STRUCTURAL','CIVIL','MEP','FIRE_LIFE_SAFETY','PERMIT','OTHER'].map(value => <option key={value} value={value}>{value.replaceAll('_', ' ')}</option>)}
              </select>
            </label>
            <label>
              Additional metadata (authority, edition, effective date, clause/section, applicability notes)
              <textarea
                aria-label="Engineering metadata"
                value={metadata}
                onChange={(event) => setMetadata(event.target.value)}
              />
            </label>
          </section>
        )}
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

function DefinitionEditor({
  item,
  categories,
  busy,
  onClose,
  onSave,
}: {
  item?: Definition;
  categories: Category[];
  busy: boolean;
  onClose: () => void;
  onSave: (data: Record<string, unknown>) => Promise<void>;
}) {
  const [term, setTerm] = useState(item?.term || "");
  const [category, setCategory] = useState(item?.category || "");
  const [description, setDescription] = useState(item?.description || "");
  const [usedIn, setUsedIn] = useState(item?.used_in || []);
  const [reason, setReason] = useState("");
  const definitionCategories = categories.filter((row) =>
    row.allowed_content_types.includes("DEFINITION"),
  );
  return (
    <Drawer
      title={item ? `Edit ${item.term}` : "New Definition"}
      eyebrow="STRUCTURED BUSINESS LANGUAGE"
      onClose={onClose}
      footer={
        <>
          <button type="button" className="button-secondary" onClick={onClose}>
            Cancel
          </button>
          <button className="button-primary" disabled={busy}>
            {busy ? "Saving…" : item ? "Save Revision" : "Create Definition"}
          </button>
        </>
      }
    >
      <form
        className="content-editor-form"
        onSubmit={(event) => {
          event.preventDefault();
          void onSave(
            item
              ? {
                  term,
                  category,
                  description,
                  used_in: usedIn,
                  change_reason: reason,
                  expected_revision: item.revision || 0,
                }
              : { term, category, description, used_in: usedIn },
          );
        }}
      >
        <section className="editor-group">
          <h3>Definition</h3>
          <label>
            Term
            <input
              aria-label="Word / Term"
              required
              value={term}
              onChange={(event) => setTerm(event.target.value)}
            />
          </label>
          <label>
            Reference
            {item ? (
              <input
                readOnly
                aria-label="Reference"
                value={item.ref || "Unassigned"}
              />
            ) : (
              <small>Auto-generated when saved. Example: D-0001.</small>
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
              {definitionCategories.map((row) => (
                <option value={row.label} key={row.id}>
                  {row.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Meaning
            <textarea
              aria-label="Description / Meaning"
              required
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          </label>
        </section>
        <UsedInPicker type="DEFINITION" value={usedIn} onChange={setUsedIn} />
        {item && (
          <section className="editor-group">
            <h3>Change Reason</h3>
            <label>
              Why are you changing this definition?
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

function HistoryDrawer({
  history,
  onClose,
}: {
  history: {
    title: string;
    itemId?: string;
    versions?: Version[];
    revisions?: DefinitionRevision[];
  };
  onClose: () => void;
}) {
  return (
    <Drawer
      title={history.title}
      eyebrow={history.revisions ? "REVISION HISTORY" : "VERSION HISTORY"}
      onClose={onClose}
      footer={
        <button type="button" className="button-secondary" onClick={onClose}>
          Close
        </button>
      }
      wide
    >
      <div className="history-list">
        {history.versions?.map((version) => (
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
        ))}
        {history.revisions?.map((revision) => (
          <article className="history-card" key={revision.id}>
            <div>
              <strong>Revision {revision.revision}</strong>
              <StatusBadge value={revision.status} hasVersion />
              <span>{revision.description}</span>
            </div>
            <small>
              {formatDateTime(revision.changed_at)} · {revision.changed_by} ·{" "}
              {revision.change_reason || "No change reason"}
            </small>
            <div className="history-card-actions">
              <span>
                {revision.category || "Uncategorized"} ·{" "}
                {(revision.used_in || [])
                  .map((item) => MODULE_LABELS[item] || item)
                  .join(" · ") || "Not assigned"}
              </span>
            </div>
          </article>
        ))}
        {!history.versions?.length && !history.revisions?.length && (
          <p className="empty-message">No history is available.</p>
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
  const text = friendlyStatus(value, hasVersion);
  return (
    <span
      className={`status-badge status-${text.toLowerCase().replaceAll(" ", "-")}`}
    >
      {text}
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
          : `Add the first ${noun.replace(/s$/, "")} to the AMEC master library.`}
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
function ContentDetails({ item, onClose }: { item: MasterItem | Definition; onClose: () => void }) {
  const isDefinition = "term" in item;
  return <Drawer title={`${item.ref || "Definition"} · ${isDefinition ? item.term : item.title}`} eyebrow={isDefinition ? "DEFINITION DETAILS" : `${item.content_type.replaceAll("_", " ")} DETAILS`} onClose={onClose} footer={<button type="button" className="button-secondary" onClick={onClose}>Close</button>}>
    <div className="content-detail-grid">
      <div><span>Category</span><b>{isDefinition ? item.category || "Uncategorized" : item.category?.label || "Uncategorized"}</b></div>
      <div><span>{isDefinition ? "Revision" : "Version"}</span><b>{isDefinition ? versionLabel(item.revision, true) : versionLabel(item.version)}</b></div>
      <div><span>Status</span><b>{isDefinition ? friendlyStatus(item.status, true) : friendlyStatus(item.version_status, Boolean(item.version))}</b></div>
      {!isDefinition && <div><span>Source Type</span><b>{item.source_type_code || "Not classified"}</b></div>}
      <div><span>Used In</span><b>{(item.used_in || []).map(module => MODULE_LABELS[module] || module).join(", ") || "Not assigned"}</b></div>
    </div>
    <p className="detail-description">{item.description || "No description"}</p>
    {!isDefinition && <div className="detail-purpose-list"><h3>Purpose bindings</h3>{(item.purpose_bindings || []).map(binding => <span key={`${binding.module}-${binding.usage_type}`}>{MODULE_LABELS[binding.module] || binding.module} · {binding.usage_type}</span>)}{!item.purpose_bindings?.length && <small>No explicit purpose binding.</small>}</div>}
    {!isDefinition && <a className="button-secondary" href={`/api/master-content/${item.id}/download`} download>Download current source</a>}
  </Drawer>;
}

function parseJson(value: string) {
  try {
    const parsed = JSON.parse(value);
    return typeof parsed === "object" && parsed ? parsed : {};
  } catch {
    return {};
  }
}
async function downloadMaster(itemId: string) {
  const response = await fetch(`/api/master-content/${itemId}/download`, {
    headers: {
      "X-Dev-Role":
        sessionStorage.getItem("proposalops-role") || "SYSTEM_ADMIN",
    },
  });
  if (!response.ok) throw new Error("The source document could not be opened.");
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "master-content";
  link.click();
  URL.revokeObjectURL(url);
}
async function downloadVersion(
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
  if (!response.ok)
    throw new Error("The source version could not be downloaded.");
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  link.click();
  URL.revokeObjectURL(url);
}
