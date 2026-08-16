import { useEffect, useMemo, useState } from "react";
import { api } from "./api";
import { Icon } from "./Icon";

type InputItem = {
  key: string;
  title: string;
  group: string;
  group_label: string;
  what: string;
  why: string;
  current: Record<string, any>;
  status: string;
  status_label: string;
  blocking: string;
  blocking_label: string;
  notes?: string | null;
  route?: string | null;
  history?: {
    event: string;
    actor: string;
    at?: string | null;
    note?: string | null;
  }[];
};
type InputPayload = {
  summary: {
    confirmed: number;
    remaining: number;
    technical_remaining: number;
    ready: boolean;
  };
  groups: { key: string; label: string; items: InputItem[] }[];
  items: InputItem[];
  source_blocker_rollup?: { blocking: number; needs_review: number; restricted_samples: number; currentness_unknown: number };
};

const statusClass = (value: string) =>
  `dashboard-input-status status-${value.toLowerCase().replaceAll("_", "-")}`;
const ownerRoles = new Set(["SYSTEM_ADMIN", "OWNER_SPONSOR"]);
const actionLabel = (item: InputItem) =>
  item.status === "NEEDS_CONTENT"
    ? "Manage content"
    : item.status === "WAITING_ON_AMEC_IT"
      ? "Open connection setup"
      : item.status === "NEEDS_DECISION"
        ? "Review decision"
        : "Review proposal";
const currentSummary = (item: InputItem) =>
  item.current?.summary ||
  Object.entries(item.current || {})
    .filter(([key]) => !["categories", "patterns", "policy"].includes(key))
    .map(
      ([key, value]) =>
        `${key.replaceAll("_", " ")}: ${Array.isArray(value) ? value.join(", ") : String(value)}`,
    )
    .join(" · ") ||
  "No current value recorded.";

function useDashboardInputs(includeGovernance = false) {
  const [data, setData] = useState<InputPayload | null>(null);
  const [error, setError] = useState("");
  const load = () =>
    api<InputPayload>(`/api/dashboard-inputs${includeGovernance ? "?include_governance=true" : ""}`)
      .then(setData)
      .catch((reason) => setError(String(reason)));
  useEffect(() => {
    void load();
  }, [includeGovernance]);
  return { data, error, reload: load };
}

function SummaryHeader({ summary }: { summary: InputPayload["summary"] }) {
  return (
    <div className="dashboard-input-progress">
      <div className="dashboard-input-progress-top">
        <strong>
          {summary.ready
            ? "Master content setup"
            : "Demo-ready master content setup"}
        </strong>
        <span>
          {summary.confirmed} confirmed · {summary.remaining} remaining
        </span>
      </div>
      <div className="dashboard-input-progress-bar">
        <span
          style={{
            width: `${Math.round((summary.confirmed / Math.max(summary.confirmed + summary.remaining, 1)) * 100)}%`,
          }}
        />
      </div>
      <small>
        {summary.technical_remaining
          ? `${summary.technical_remaining} technical connection remaining`
          : "No open technical connections"}
      </small>
    </div>
  );
}

export function DashboardInputsLauncher({
  role,
  onNavigate,
  includeGovernance = false,
}: {
  role: string;
  onNavigate: (page: string) => void;
  includeGovernance?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const { data, error } = useDashboardInputs(includeGovernance);
  const unresolved = useMemo(
    () =>
      (data?.items || []).filter(
        (item) =>
          !["CONFIRMED", "COMPLETE", "NOT_APPLICABLE", "OPTIONAL"].includes(
            item.status,
          ),
      ),
    [data],
  );
  return (
    <>
      <button className="readiness-launcher" onClick={() => setOpen(true)}>
        <span className="readiness-launcher-icon"><Icon name="check" size={16} /></span>
        <span>Inputs &amp; Go-Live</span>
        {data && <b className="readiness-count">{data.summary.remaining}</b>}
      </button>
      {open && (
        <div
          className="readiness-overlay"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setOpen(false);
          }}
        >
          <aside
            className="readiness-drawer dashboard-input-summary-drawer"
            role="dialog"
            aria-modal="true"
            aria-labelledby="dashboard-input-summary-title"
          >
            <div className="readiness-drawer-head">
              <div>
                <span className="eyebrow">
                  DASHBOARD · INPUTS &amp; GO-LIVE
                </span>
                <h2 id="dashboard-input-summary-title">
                  Master Content Setup &amp; Go-Live
                </h2>
                <p className="dashboard-input-drawer-subtitle">
                  Track the AMEC decisions, content, and technical inputs needed
                  to move Forms, Reports, Engineering Works, and Definitions
                  from demo-ready to production-ready.
                </p>
              </div>
              <button
                className="readiness-close"
                onClick={() => setOpen(false)}
                aria-label="Close Inputs & Go-Live"
              ><Icon name="close" size={16} /></button>
            </div>
            <div className="readiness-drawer-body">
              {error && (
                <p className="dashboard-input-error">
                  Dashboard setup could not be loaded.
                </p>
              )}
              {data && (
                <>
                  <SummaryHeader summary={data.summary} />
                  {data.source_blocker_rollup && <section className="source-blocker-rollup"><h3>Master Content Source Blockers</h3><div className="source-blocker-grid"><span><b>{data.source_blocker_rollup.blocking}</b>Blocking</span><span><b>{data.source_blocker_rollup.needs_review}</b>Needs review</span><span><b>{data.source_blocker_rollup.restricted_samples}</b>Restricted samples</span><span><b>{data.source_blocker_rollup.currentness_unknown}</b>Currentness unknown</span></div></section>}
                  <section>
                    <h3>What we need from AMEC</h3>
                    <div className="dashboard-input-summary-list">
                      {unresolved.slice(0, 8).map((item) => (
                        <article
                          key={item.key}
                          className="dashboard-input-summary-row"
                        >
                          <div>
                            <strong>{item.title}</strong>
                            <p>{currentSummary(item)}</p>
                          </div>
                          <span className={statusClass(item.status)}>
                            {item.status_label}
                          </span>
                        </article>
                      ))}
                    </div>
                  </section>
                  <section className="dashboard-input-boundary">
                    <h3>Production boundary</h3>
                    <p>
                      Master content remains synthetic/demo data until AMEC
                      confirms the business inputs and AMEC IT verifies the real
                      Synology source of record.
                    </p>
                  </section>
                </>
              )}
            </div>
            <footer className="readiness-drawer-footer">
              <button
                className="button-secondary"
                onClick={() => setOpen(false)}
              >
                Close
              </button>
              {ownerRoles.has(role) && (
                <button
                  className="button-primary"
                  onClick={() => {
                    setOpen(false);
                    onNavigate("dashboard-inputs");
                  }}
                >
                  View all setup items
                </button>
              )}
            </footer>
          </aside>
        </div>
      )}
    </>
  );
}

function InputCard({
  item,
  role,
  onUpdate,
}: {
  item: InputItem;
  role: string;
  onUpdate: (key: string, action: string, notes?: string) => Promise<void>;
}) {
  const [expanded, setExpanded] = useState(false);
  const [note, setNote] = useState(item.notes || "");
  const canWrite = ownerRoles.has(role);
  const isSynology = item.key === "DASHBOARD_SYNOLOGY_CONNECTION";
  return (
    <article
      className={`dashboard-input-card ${expanded ? "is-expanded" : ""}`}
      data-input-key={item.key}
    >
      <button
        className="dashboard-input-card-head"
        onClick={() => setExpanded((value) => !value)}
        aria-expanded={expanded}
      >
        <span>
          <strong>{item.title}</strong>
          <small>{item.why}</small>
        </span>
        <span className={statusClass(item.status)}>{item.status_label}</span>
        <span className="dashboard-input-chevron"><Icon name={expanded ? "minus" : "plus"} size={16} /></span>
      </button>
      <div className="dashboard-input-card-preview">
        <div>
          <b>Current state</b>
          <span>{currentSummary(item)}</span>
        </div>
        <div>
          <b>Action</b>
          <span>{actionLabel(item)}</span>
        </div>
      </div>
      {expanded && (
        <div className="dashboard-input-card-detail">
          <div className="dashboard-input-detail-grid">
            <div>
              <b>What AMEC needs</b>
              <p>{item.what}</p>
            </div>
            <div>
              <b>Why it matters</b>
              <p>{item.why}</p>
            </div>
            <div>
              <b>Current state</b>
              <p>{currentSummary(item)}</p>
            </div>
            <div>
              <b>Readiness</b>
              <p>
                {item.blocking_label}
                {isSynology ? " · Manual confirmation is disabled" : ""}
              </p>
            </div>
          </div>
          {item.current?.patterns && (
            <div className="dashboard-input-evidence">
              <b>Proposed pattern</b>
              <span>{item.current.patterns.join(" · ")}</span>
            </div>
          )}
          <label className="dashboard-input-note">
            <b>Notes / evidence</b>
            <textarea
              value={note}
              onChange={(event) => setNote(event.target.value)}
              placeholder="Add a short Owner note"
              disabled={!canWrite}
            />
          </label>
          {item.history?.length ? (
            <div className="dashboard-input-history">
              <b>Recent history</b>
              {item.history.map((event, index) => (
                <small key={`${event.at}-${index}`}>
                  {event.actor} ·{" "}
                  {event.event.replaceAll("_", " ").toLowerCase()}
                  {event.note ? ` · ${event.note}` : ""}
                </small>
              ))}
            </div>
          ) : null}
          <div className="dashboard-input-actions">
            {item.route && (
              <a className="button-secondary" href={item.route}>
                {actionLabel(item)} <Icon name="arrow-up-right" size={14} />
              </a>
            )}
            {canWrite && !isSynology && item.status !== "NOT_APPLICABLE" && (
              <>
                <button
                  className="button-primary"
                  onClick={() => void onUpdate(item.key, "confirm", note)}
                >
                  Confirm current proposal
                </button>
                <button
                  className="button-secondary"
                  onClick={() => void onUpdate(item.key, "note", note)}
                >
                  Save note
                </button>
                {item.status !== "OPTIONAL" && (
                  <button
                    className="text-button"
                    onClick={() => void onUpdate(item.key, "reopen")}
                  >
                    Reopen
                  </button>
                )}
              </>
            )}
            {canWrite &&
              item.blocking === "OPTIONAL" &&
              item.status === "OPTIONAL" && (
                <button
                  className="button-secondary"
                  onClick={() =>
                    void onUpdate(item.key, "not_applicable", note)
                  }
                >
                  Mark not applicable
                </button>
              )}
          </div>
        </div>
      )}
    </article>
  );
}

export function DashboardInputsPage({
  role,
  onNavigate,
  backPage = "dashboard",
}: {
  role: string;
  onNavigate: (page: string) => void;
  backPage?: string;
}) {
  const { data, error, reload } = useDashboardInputs(true);
  const update = async (key: string, action: string, notes?: string) => {
    await api(`/api/dashboard-inputs/${key}`, {
      method: "PATCH",
      body: JSON.stringify({ action, notes }),
    });
    await reload();
  };
  return (
    <div className="dashboard-inputs-page">
      <div className="dashboard-inputs-hero">
        <div>
          <span className="eyebrow">DASHBOARD · OWNER CHECKLIST</span>
          <h2>Master Content Setup &amp; Go-Live</h2>
          <p>
            Track the AMEC decisions, content, and technical inputs needed to
            move Forms, Reports, Engineering Works, and Definitions from
            demo-ready to production-ready.
          </p>
        </div>
        <button
          className="button-secondary"
          onClick={() => onNavigate(backPage)}
        >
          <Icon name="arrow-left" size={14} /> Back to Dashboard
        </button>
      </div>
      {error && (
        <div className="dashboard-input-error">
          Unable to load the persistent setup checklist. {error}
        </div>
      )}
      {data && (
        <>
          <SummaryHeader summary={data.summary} />
          <div className="dashboard-inputs-groups">
            {data.groups.map((group) => (
              <section className="dashboard-input-group" key={group.key}>
                <div className="dashboard-input-group-heading">
                  <div>
                    <span className="eyebrow">
                      {group.key === "BUSINESS_DECISION"
                        ? "DECISIONS"
                        : group.key === "CONTENT_READINESS"
                          ? "LIBRARY HEALTH"
                          : group.key === "TECHNICAL_GO_LIVE"
                            ? "CONNECTIONS & POLICY"
                            : "LATER"}
                    </span>
                    <h3>{group.label}</h3>
                  </div>
                  <span>
                    {
                      group.items.filter(
                        (item) =>
                          ![
                            "CONFIRMED",
                            "COMPLETE",
                            "NOT_APPLICABLE",
                            "OPTIONAL",
                          ].includes(item.status),
                      ).length
                    }{" "}
                    open
                  </span>
                </div>
                {group.items.map((item) => (
                  <InputCard
                    key={item.key}
                    item={item}
                    role={role}
                    onUpdate={update}
                  />
                ))}
              </section>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
