import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { api } from "./api";
import { Icon } from "./Icon";

export type ProposalRole =
  | "SYSTEM_ADMIN"
  | "OWNER_SPONSOR"
  | "PROCESS_CHAMPION"
  | "COMMERCIAL_APPROVER"
  | "RESPONSIBLE_ENGINEER";
type ViewKey =
  | "overview"
  | "intake"
  | "engineering"
  | "commercial"
  | "response"
  | "outputs"
  | "history";

const views: Array<{ key: ViewKey; label: string; hint: string }> = [
  { key: "overview", label: "Overview", hint: "Operating summary" },
  {
    key: "intake",
    label: "Intake & Sources",
    hint: "Client, context, evidence",
  },
  { key: "engineering", label: "Engineering", hint: "Scope, risks, inputs" },
  { key: "commercial", label: "Commercial", hint: "Controls and acceptance" },
  {
    key: "response",
    label: "Client Response & Outcome",
    hint: "Release, response, LPO",
  },
  {
    key: "outputs",
    label: "Review & Outputs",
    hint: "Revisions and artifacts",
  },
  { key: "history", label: "History & Lineage", hint: "Audit and currentness" },
];
const owners = new Set<ProposalRole>([
  "SYSTEM_ADMIN",
  "OWNER_SPONSOR",
  "PROCESS_CHAMPION",
  "COMMERCIAL_APPROVER",
]);
const engineers = new Set<ProposalRole>([
  "SYSTEM_ADMIN",
  "OWNER_SPONSOR",
  "RESPONSIBLE_ENGINEER",
]);
const stageRank: Record<string, number> = {
  RECEIVED: 0,
  IN_REVIEW: 0,
  PROPOSAL_PREPARATION: 1,
  PROPOSAL_HANDOVER: 2,
  READY_FOR_QUOTATION: 2,
  COMMERCIAL_REVIEW: 2,
  QUOTATION_IN_PROGRESS: 2,
  CLIENT_RESPONSE_PENDING: 3,
  ACCEPTED: 4,
  CONTRACT_HANDOVER: 5,
  CLOSED: 6,
};
const sourceLabels: Record<string, string> = {
  TENDER_EMAIL: "Tender email",
  TENDER_DOCUMENT: "Tender document",
  TENDER_PHOTO: "Tender photo",
  CLIENT_DATA: "Client information",
  SITE_PHOTO: "Site photo",
};

const list = (value: unknown): any[] => (Array.isArray(value) ? value : []);
const record = (value: unknown): Record<string, any> =>
  value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, any>)
    : {};
const text = (value: unknown, fallback = "Not recorded"): string =>
  value === null || value === undefined || value === ""
    ? fallback
    : Array.isArray(value)
      ? value.length
        ? value.map((item) => text(item, "")).filter(Boolean).join(", ") || fallback
        : fallback
      : typeof value === "object"
        ? (() => {
            const item = record(value);
            for (const key of ["message", "detail", "code", "label", "name", "status"]) {
              const candidate = item[key];
              if (candidate !== undefined && typeof candidate !== "object") {
                return text(candidate, fallback);
              }
            }
            return fallback;
          })()
        : String(value);
const dateText = (value: unknown): string =>
  value
    ? new Date(String(value)).toLocaleString([], {
        dateStyle: "medium",
        timeStyle: "short",
      })
    : "Not recorded";
const statusText = (value: unknown): string =>
  String(value || "NOT_STARTED").replaceAll("_", " ");
const roleHeaders = (role: ProposalRole) => ({ "X-Dev-Role": role });
const unwrap = (value: any): any => value?.proposal || value;
type LookupOption = {
  value: string;
  label: string;
  email?: string;
  phone?: string;
  source_role?: string;
  content_hash?: string;
};
function useProposalLookups(proposalId: string, role: ProposalRole) {
  const [lookups, setLookups] = useState<{
    contacts: LookupOption[];
    parties: LookupOption[];
    evidence: LookupOption[];
  }>({ contacts: [], parties: [], evidence: [] });
  useEffect(() => {
    let active = true;
    Promise.resolve(
      api<any>(
        `/api/bd/proposals/lookups?proposal_id=${encodeURIComponent(proposalId)}`,
        { headers: roleHeaders(role) },
      ),
    )
      .then((data) => {
        if (active)
          setLookups({
            contacts: list(data?.contacts),
            parties: list(data?.parties),
            evidence: list(data?.evidence),
          });
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [proposalId, role]);
  return lookups;
}

function governedEvidenceOptions(proposal: any): LookupOption[] {
  const links = list(proposal.forms_v2?.source_links);
  return links
    .map((item: any) => ({
      value: item.document_version_id,
      label: `${item.source_role || "Proposal source"} · ${String(item.document_version_id).slice(0, 8)}`,
      source_role: item.source_role,
    }))
    .filter((item) => Boolean(item.value));
}

function normalize(raw: any): any {
  const item = raw || {};
  return {
    ...item,
    fields: record(item.fields),
    forms_v2: record(item.forms_v2),
    hardening: record(item.hardening),
    validation: record(item.validation),
    intake_readiness: record(item.intake_readiness),
    readiness_v2: record(item.readiness_v2),
    configuration: record(item.configuration),
    commercial_controls: record(item.commercial_controls),
    contract_eligibility: record(item.contract_eligibility),
    outputs: record(item.outputs),
    sources: list(item.sources),
    notes: list(item.notes),
    site_photos: list(item.site_photos),
    revision_history: list(item.revision_history),
    stage_history: list(item.stage_history),
  };
}

function Chip({ value, tone = "neutral" }: { value: unknown; tone?: string }) {
  return (
    <span className={`proposal-chip ${tone}`}>
      {tone === "pass" ? "✓ " : tone === "blocked" ? "! " : ""}
      {statusText(value)}
    </span>
  );
}
function Empty({ children }: { children: ReactNode }) {
  return (
    <div className="proposal-empty">
      <Icon name="minus" size={15} />
      <span>{children}</span>
    </div>
  );
}
function Section({
  title,
  eyebrow,
  children,
  action,
  id,
}: {
  title: string;
  eyebrow?: string;
  children: ReactNode;
  action?: ReactNode;
  id?: string;
}) {
  return (
    <section className="panel proposal-section" id={id}>
      <div className="proposal-section-head">
        <div>
          {eyebrow && <span className="eyebrow">{eyebrow}</span>}
          <h2>{title}</h2>
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}
function Field({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: unknown;
  mono?: boolean;
}) {
  return (
    <div className="proposal-fact">
      <small>{label}</small>
      <strong className={mono ? "mono" : ""}>{text(value)}</strong>
    </div>
  );
}
function ServerAction({
  label,
  onClick,
  disabled,
  reason,
  busy,
}: {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  reason?: string;
  busy?: boolean;
}) {
  return (
    <div className="proposal-action-wrap">
      <button
        type="button"
        className="button-primary"
        disabled={disabled || busy}
        onClick={onClick}
      >
        {busy ? "Working…" : label}
      </button>
      {disabled && reason && (
        <small className="proposal-action-reason">Blocked: {reason}</small>
      )}
    </div>
  );
}
function BusinessPicker({
  label,
  value,
  onChange,
  options,
  placeholder,
  disabled,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: Array<{ value: string; label: string }>;
  placeholder: string;
  disabled?: boolean;
}) {
  return (
    <label className="proposal-picker">
      {label}
      <select
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">{placeholder}</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
function Lineage({ item }: { item: any }) {
  return (
    <details className="proposal-lineage">
      <summary>Technical details / lineage</summary>
      <div className="proposal-lineage-grid">
        {Object.entries(item || {})
          .filter(([key]) =>
            /(^id$|_id$|hash|sha|storage|correlation|supersed|revision)/i.test(
              key,
            ),
          )
          .map(([key, value]) => (
            <Field
              key={key}
              label={key.replaceAll("_", " ")}
              value={value}
              mono
            />
          ))}
      </div>
    </details>
  );
}

function ProposalHeader({
  proposal,
  onBack,
  role,
  view,
  onNavigate,
}: {
  proposal: any;
  onBack: () => void;
  role: ProposalRole;
  view: ViewKey;
  onNavigate: (view: ViewKey) => void;
}) {
  const blockers =
    list(proposal.validation?.blockers).length +
    list(proposal.intake_readiness?.blockers).length +
    list(proposal.readiness_v2?.blocking).length;
  const accepted = proposal.current_revision;
  return (
    <>
      <header className="proposal-workspace-header">
        <div className="proposal-title-block">
          <button className="text-button" onClick={onBack}>
            <Icon name="arrow-left" size={14} /> Proposals
          </button>
          <span className="eyebrow">
            PROPOSAL OPERATING WORKSPACE · {role.replaceAll("_", " ")}
          </span>
          <h1>{text(proposal.title, "Proposal")}</h1>
          <p>
            {text(proposal.proposal_reference)} ·{" "}
            {text(proposal.client_name, "Canonical Client pending")}
          </p>
        </div>
        <div className="proposal-primary-actions">
          <Chip
            value={proposal.stage_label || proposal.stage}
            tone={proposal.stage === "ACCEPTED" ? "pass" : "neutral"}
          />
          {proposal.fixture_classification === "SYNTHETIC_OWNER_TEST" && (
            <span className="proposal-synthetic-badge">
              OWNER TEST · SYNTHETIC DATA · NO REAL AMEC DATA
            </span>
          )}
          <span className="proposal-next-action">
            Next: <b>{text(proposal.next_action?.label, "Review Proposal")}</b>
          </span>
        </div>
      </header>
      <div className="proposal-identity-strip">
        <Field
          label="Proposal reference"
          value={proposal.proposal_reference}
          mono
        />
        <Field label="Description" value={proposal.title} />
        <Field label="Canonical Client" value={proposal.client_name} />
        <Field
          label="Lifecycle stage"
          value={proposal.stage_label || proposal.stage}
        />
        <Field label="Owner / function" value={proposal.current_owner} />
        <Field
          label="Current revision"
          value={accepted ? `R${accepted.revision_number}` : "Working draft"}
        />
        <Field
          label="Accepted revision"
          value={
            accepted
              ? `R${accepted.revision_number} · ${String(accepted.content_hash || "").slice(0, 10)}`
              : "None"
          }
          mono
        />
        <Field
          label="Readiness / blockers"
          value={`${proposal.validation?.ready ? "Ready" : "Needs attention"} · ${blockers}`}
        />
      </div>
      <nav className="proposal-stage-nav" aria-label="Proposal workspace views">
        {views.map((item) => (
          <a
            key={item.key}
            className={view === item.key ? "active" : ""}
            href={`?view=${item.key}`}
            aria-current={view === item.key ? "page" : undefined}
            onClick={(event) => {
              event.preventDefault();
              onNavigate(item.key);
            }}
          >
            <span>{item.label}</span>
            <small>{item.hint}</small>
          </a>
        ))}
      </nav>
    </>
  );
}

function ContextRail({
  proposal,
  view,
  onRefresh,
}: {
  proposal: any;
  view: ViewKey;
  onRefresh: () => void;
}) {
  const blockers = [
    ...list(proposal.validation?.blockers),
    ...list(proposal.intake_readiness?.blockers),
    ...list(proposal.readiness_v2?.blocking),
  ];
  const evidence = list(proposal.sources).length;
  const stale = list(proposal.hardening?.active_staleness);
  return (
    <aside className="proposal-context-rail">
      <div className="proposal-rail-head">
        <div>
          <span className="eyebrow">CONTEXT</span>
          <h2>{views.find((item) => item.key === view)?.label}</h2>
        </div>
        <button
          className="icon-button"
          aria-label="Refresh Proposal projection"
          onClick={onRefresh}
        >
          <Icon name="refresh" size={15} />
        </button>
      </div>
      <div
        className={`proposal-rail-callout ${blockers.length ? "blocked" : "pass"}`}
      >
        <b>
          {blockers.length
            ? `${blockers.length} blocker(s)`
            : "No active blockers"}
        </b>
        <span>
          {blockers.length
            ? "Resolve from the linked working view."
            : "Server readiness is currently clear."}
        </span>
      </div>
      <h3>Readiness & blockers</h3>
      {blockers.length ? (
        <div className="proposal-rail-list">
          {blockers.map((item: any, index) => (
            <a
              key={`${item.code || item}-${index}`}
              href={`?view=${item.section === "sources" ? "intake" : item.section === "commercial" ? "commercial" : "engineering"}`}
            >
              <Chip value={item.label || item} tone="blocked" />
            </a>
          ))}
        </div>
      ) : (
        <Empty>Readiness has no blocking items.</Empty>
      )}
      <h3>Evidence</h3>
      <Field label="Linked sources" value={evidence} />
      <Field
        label="Currentness events"
        value={stale.length ? `${stale.length} active` : "Current"}
      />
      {stale.length > 0 && (
        <a className="text-button" href="?view=history">
          Review currentness
        </a>
      )}
      <h3>Lineage</h3>
      <Field
        label="Revision"
        value={
          proposal.current_revision
            ? `R${proposal.current_revision.revision_number}`
            : "Working draft"
        }
      />
      <Field
        label="Last activity"
        value={dateText(proposal.last_activity || proposal.updated_at)}
      />
      <details>
        <summary>Activity</summary>
        <div className="proposal-rail-list">
          {list(proposal.stage_history)
            .slice(-4)
            .reverse()
            .map((event: any, index) => (
              <div key={index}>
                <b>{statusText(event.event_type)}</b>
                <small>{dateText(event.occurred_at)}</small>
              </div>
            ))}
        </div>
      </details>
    </aside>
  );
}

function Overview({
  proposal,
  onNavigate,
}: {
  proposal: any;
  onNavigate: (view: ViewKey) => void;
}) {
  const forms = proposal.forms_v2;
  const controls = proposal.commercial_controls;
  const fields = proposal.fields;
  const blockerCount =
    list(proposal.validation?.blockers).length +
    list(proposal.intake_readiness?.blockers).length;
  const outputLinks = proposal.outputs?.available ? (
    <div className="proposal-output-links">
      <a
        className="button-secondary"
        href={`/api/bd/proposals/${proposal.id}/outputs/proposal`}
        download
      >
        Proposal Download
      </a>
      <a
        className="button-secondary"
        href={`/api/bd/proposals/${proposal.id}/outputs/checklist`}
        download
      >
        Checklist Download
      </a>
    </div>
  ) : (
    <Empty>Outputs become available after human Proposal acceptance.</Empty>
  );
  return (
    <div className="proposal-view-grid">
      <Section title="Executive operating summary" eyebrow="OVERVIEW">
        <div className="proposal-facts-grid">
          <Field label="What is this Proposal?" value={proposal.title} />
          <Field label="Canonical Client" value={proposal.client_name} />
          <Field
            label="Where are we?"
            value={proposal.stage_label || proposal.stage}
          />
          <Field
            label="Who owns next action?"
            value={`${text(proposal.current_owner)} · ${text(proposal.next_action?.label)}`}
          />
          <Field
            label="Commercial position"
            value={`${text(fields.price, "Amount pending")} ${text(fields.currency, "")}`}
          />
          <Field
            label="Source completeness"
            value={`${proposal.sources.length} governed source(s)`}
          />
          <Field
            label="Accepted/output state"
            value={
              proposal.current_revision
                ? `R${proposal.current_revision.revision_number} accepted`
                : "No accepted revision"
            }
          />
          <Field
            label="Client Response"
            value={text(
              proposal.hardening?.client_responses?.length
                ? "Recorded"
                : "Pending",
            )}
          />
          <Field
            label="Handoff readiness"
            value={
              proposal.contract_eligibility?.eligible
                ? "Eligible"
                : `${list(proposal.contract_eligibility?.blockers).length} requirement(s) pending`
            }
          />
        </div>
        <div className="proposal-drilldown-row">
          <button
            className="button-secondary"
            onClick={() => onNavigate("intake")}
          >
            Open Intake &amp; Sources
          </button>
          <button
            className="button-secondary"
            onClick={() => onNavigate("engineering")}
          >
            Open Engineering
          </button>
          <button
            className="button-secondary"
            onClick={() => onNavigate("commercial")}
          >
            Open Commercial
          </button>
        </div>
      </Section>
      <Section title="Readiness & blockers" eyebrow="SERVER-OWNED">
        <div
          className={`proposal-readiness-banner ${blockerCount ? "blocked" : "pass"}`}
        >
          <b>
            {blockerCount
              ? `${blockerCount} item(s) need attention`
              : "Ready to continue"}
          </b>
          <span>
            {text(proposal.next_action?.label, "No further Proposal action")}
          </span>
        </div>
        {list(proposal.validation?.blockers).length ? (
          <div className="proposal-blocker-list">
            {list(proposal.validation.blockers).map((item: any) => (
              <a key={item.code} href="?view=commercial">
                <Icon name="alert" size={14} />
                {text(item.label || item)}
              </a>
            ))}
          </div>
        ) : (
          <Empty>No validation blockers returned by the server.</Empty>
        )}
      </Section>
      <div className="proposal-overview-columns">
        <section className="panel proposal-section">
          <h3>Stakeholders</h3>
          <CompactRows
            items={list(forms.stakeholders)}
            empty="No stakeholders recorded yet."
          />
        </section>
        <section className="panel proposal-section">
          <h3>Source evidence</h3>
          <CompactRows
            items={proposal.sources}
            empty="No source evidence recorded yet."
          />
        </section>
        <section className="panel proposal-section">
          <h3>Regulatory Scoping</h3>
          <CompactRows
            items={list(forms.regulatory_scope_intents)}
            empty="No regulatory scoping intents recorded yet."
          />
        </section>
        <section className="panel proposal-section">
          <h3>Commercial Outcome</h3>
          <CompactRows
            items={
              proposal.hardening?.commercial_outcome
                ? [proposal.hardening.commercial_outcome]
                : []
            }
            empty="No commercial outcome recorded."
          />
        </section>
        <section className="panel proposal-section">
          <h3>Client Response</h3>
          <p className="muted">
            {text(
              proposal.hardening?.client_responses?.length
                ? "Client Response recorded."
                : "No Client Response recorded.",
            )}
          </p>
        </section>
        <section className="panel proposal-section">
          <h3>Decision risks</h3>
          <p className="muted">
            {list(proposal.hardening?.unknowns).length ||
            list(proposal.hardening?.conflicts).length
              ? "Material unknowns or conflicts need review."
              : "No assumptions, unknowns, or conflicts recorded."}
          </p>
        </section>
        <section className="panel proposal-section">
          <h3>Proposal history and lineage</h3>
          <p className="muted">
            {proposal.stage_history?.length
              ? `${proposal.stage_history.length} lifecycle event(s) available.`
              : "No stage history recorded yet."}
          </p>
        </section>
      </div>
      <Section
        title="Current accepted configuration & outputs"
        eyebrow="REVIEW / OUTPUTS"
      >
        <p className="muted">
          Dashboard configuration remains the source of truth for Proposal
          Template, Checklist, Definitions, and Engineering references.
        </p>
        <div className="proposal-facts-grid">
          <Field
            label="Proposal Template"
            value={`${text(proposal.configuration?.proposal_template?.ref)} · v${text(proposal.configuration?.proposal_template?.version)}`}
          />
          <Field
            label="Proposal Checklist"
            value={`${text(proposal.configuration?.proposal_checklist?.ref)} · v${text(proposal.configuration?.proposal_checklist?.version)}`}
          />
          <Field
            label="Proposal Form · existing Proposal context"
            value={
              list(forms.proposal_form)
                .map((item: any) => item.filename)
                .join(", ") || "Not recorded"
            }
          />
          <Field
            label="Decision context"
            value={text(
              proposal.authority?.status_label,
              "Server decision state pending",
            )}
          />
        </div>
        {outputLinks}
        <button className="text-button" onClick={() => onNavigate("outputs")}>
          View revision and artifact history →
        </button>
      </Section>
    </div>
  );
}
function CompactRows({ items, empty }: { items: any[]; empty: string }) {
  return items.length ? (
    <div className="proposal-compact-list">
      {items.slice(0, 5).map((item, index) => (
        <div key={item.id || index}>
          <b>
            {text(
              item.display_snapshot ||
                item.description ||
                item.statement ||
                item.response_type ||
                item.service_type ||
                item.filename,
              "Record",
            )}
          </b>
          <Chip value={item.status || item.verification_state || "CURRENT"} />
        </div>
      ))}
    </div>
  ) : (
    <Empty>{empty}</Empty>
  );
}

function GovernedContextControls({
  proposal,
  role,
  refresh,
  setError,
  setMessage,
}: any) {
  const lookups = useProposalLookups(proposal.id, role);
  const editable = owners.has(role);
  const client = proposal.forms_v2.commercial_client || {};
  const currentContact = proposal.forms_v2.proposal_contact || {};
  const [contactId, setContactId] = useState("");
  const [partyId, setPartyId] = useState(client.canonical_party_id || "");
  const [stakeholderPartyId, setStakeholderPartyId] = useState("");
  const [stakeholderRole, setStakeholderRole] = useState("CLIENT_CONTACT");
  const [sourceVersionId, setSourceVersionId] = useState("");
  const [busy, setBusy] = useState(false);
  const contact = lookups.contacts.find((item) => item.value === contactId);
  const call = async (
    path: string,
    method: string,
    payload: any,
    message: string,
  ) => {
    setBusy(true);
    try {
      const result = await api<any>(
        `/api/bd/proposals/${proposal.id}/${path}`,
        {
          method,
          headers: { ...roleHeaders(role), "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
      );
      await refresh(result?.proposal || result);
      setMessage(message);
    } catch (cause) {
      setError(cause);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="proposal-governed-controls">
      <div className="proposal-inline-form">
        <BusinessPicker
          label="Client Contact"
          value={contactId}
          onChange={setContactId}
          options={lookups.contacts}
          placeholder={
            lookups.contacts.length
              ? "Select canonical Client Contact"
              : currentContact.display_name || "No active Client Contacts"
          }
          disabled={!editable || !lookups.contacts.length}
        />
        <ServerAction
          label="Save selected contact"
          onClick={() =>
            void call(
              "contact",
              "PUT",
              {
                display_name:
                  contact?.label?.split(" · ")[0] ||
                  currentContact.display_name,
                email: contact?.email || currentContact.email,
                mobile: contact?.phone || currentContact.mobile,
                purpose: "PROPOSAL_CONTACT",
                status: "HUMAN_ENTERED",
              },
              "Canonical Client Contact saved.",
            )
          }
          disabled={!editable || !contact}
          reason="Select an active canonical Client Contact."
          busy={busy}
        />
        <BusinessPicker
          label="Canonical Client Party"
          value={partyId}
          onChange={setPartyId}
          options={lookups.parties}
          placeholder={
            lookups.parties.length
              ? "Select canonical Party"
              : "No current Parties available"
          }
          disabled={!editable || !lookups.parties.length}
        />
        <ServerAction
          label="Link Client Party"
          onClick={() =>
            void call(
              "client-party",
              "PUT",
              { canonical_party_id: partyId },
              "Canonical Client Party linkage saved.",
            )
          }
          disabled={
            !editable || !partyId || partyId === client.canonical_party_id
          }
          reason="Select a different governed Party."
          busy={busy}
        />
      </div>
      <div className="proposal-inline-form">
        <BusinessPicker
          label="Stakeholder Party"
          value={stakeholderPartyId}
          onChange={setStakeholderPartyId}
          options={lookups.parties}
          placeholder={
            lookups.parties.length
              ? "Select stakeholder Party"
              : "No current Parties available"
          }
          disabled={!editable || !lookups.parties.length}
        />
        <label>
          Stakeholder role
          <input
            value={stakeholderRole}
            onChange={(event) => setStakeholderRole(event.target.value)}
            disabled={!editable}
          />
        </label>
        <ServerAction
          label="Add stakeholder"
          onClick={() =>
            void call(
              "stakeholders",
              "POST",
              {
                party_id: stakeholderPartyId,
                role_code: stakeholderRole,
                status: "UNKNOWN",
                source_type: "HUMAN_ENTERED",
              },
              "Stakeholder Party added with provenance.",
            )
          }
          disabled={!editable || !stakeholderPartyId || !stakeholderRole.trim()}
          reason="Select a governed Party and role."
          busy={busy}
        />
        <BusinessPicker
          label="Link Proposal source"
          value={sourceVersionId}
          onChange={setSourceVersionId}
          options={lookups.evidence}
          placeholder={
            lookups.evidence.length
              ? "Select governed source version"
              : "No source versions available"
          }
          disabled={!editable || !lookups.evidence.length}
        />
        <ServerAction
          label="Link source version"
          onClick={() =>
            void call(
              "source-links",
              "POST",
              {
                document_version_id: sourceVersionId,
                source_role: "SUPPLEMENTAL",
              },
              "Proposal source version linked.",
            )
          }
          disabled={!editable || !sourceVersionId}
          reason="Select a governed source version."
          busy={busy}
        />
      </div>
      <small className="muted">
        Selectors use canonical business records. Transport identifiers are
        retained only in server lineage.
      </small>
    </div>
  );
}

function Intake({ proposal, role, refresh, setError, setMessage }: any) {
  const forms = proposal.forms_v2;
  const editable = owners.has(role) && (stageRank[proposal.stage] ?? 0) === 0;
  const [sourceType, setSourceType] = useState("TENDER_DOCUMENT");
  const [file, setFile] = useState<File | null>(null);
  const [selectedSource, setSelectedSource] = useState<any>(null);
  const [content, setContent] = useState("");
  const [busy, setBusy] = useState(false);
  const [location, setLocation] = useState(
    forms.site_context?.location_text || proposal.fields.location || "",
  );
  const contact = forms.proposal_contact || {};
  const client = forms.commercial_client || {};
  const saveSite = async () => {
    setBusy(true);
    try {
      await api(`/api/bd/proposals/${proposal.id}/site-context`, {
        method: "PUT",
        headers: { ...roleHeaders(role), "Content-Type": "application/json" },
        body: JSON.stringify({
          ...forms.site_context,
          location_text: location,
        }),
      });
      await refresh();
      setMessage("Site context saved and Proposal projection refreshed.");
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };
  const upload = async () => {
    if (!file) return;
    setBusy(true);
    try {
      const body = new FormData();
      body.append("source_type", sourceType);
      body.append("file", file);
      const result = await api<any>(
        `/api/bd/proposals/${proposal.id}/sources`,
        { method: "POST", headers: roleHeaders(role), body },
      );
      await refresh(result.proposal);
      setMessage("Source registered and read-back verified.");
      setFile(null);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };
  const readSource = async (item: any) => {
    setSelectedSource(item);
    setContent("");
    try {
      const response = await api<any>(
        `/api/bd/proposals/${proposal.id}/sources/${item.id}/content`,
        { headers: roleHeaders(role) },
      );
      setContent(typeof response === "string" ? response : text(response));
    } catch {
      setContent(
        "Preview is unavailable for this source type. Use the governed download action.",
      );
    }
  };
  return (
    <div className="proposal-view-grid">
      <Section title="Canonical Client & contact" eyebrow="INTAKE & SOURCES">
        <div className="proposal-facts-grid">
          <Field
            label="Canonical Client"
            value={client.display_name || proposal.client_name}
          />
          <Field
            label="Client reference"
            value={client.client_reference || "Available in Client workspace"}
            mono
          />
          <Field label="Proposal contact" value={contact.display_name} />
          <Field
            label="Contact details"
            value={`${text(contact.email, "Email pending")} · ${text(contact.mobile, "Phone pending")}`}
          />
        </div>
        <p className="muted">
          Client identity is canonical and cannot be replaced by intake wording.
          Contact and Party technical identifiers remain inside lineage details.
        </p>
        <CompactRows
          items={client.party ? [client.party] : []}
          empty="No Client Party linkage recorded yet."
        />
        <GovernedContextControls
          proposal={proposal}
          role={role}
          refresh={refresh}
          setError={setError}
          setMessage={setMessage}
        />
      </Section>
      <Section
        title="Project / request context"
        eyebrow="CLIENT WORDING → AMEC CONTEXT"
      >
        <div className="proposal-form-grid">
          <label>
            Location
            <input
              value={location}
              disabled={!editable}
              onChange={(event) => setLocation(event.target.value)}
            />
          </label>
          <Field
            label="Project / opportunity reference"
            value={proposal.project_reference}
          />
          <Field
            label="Client scope wording"
            value={proposal.fields.client_scope_of_work}
          />
          <Field
            label="AMEC normalized scope"
            value={proposal.fields.scope_of_work || proposal.fields.sow}
          />
        </div>
        {editable && (
          <ServerAction
            label="Save site context"
            onClick={() => void saveSite()}
            busy={busy}
          />
        )}
      </Section>
      <Section title="Stakeholders" eyebrow="PARTY / ROLE / PROVENANCE">
        <div className="proposal-table-wrap">
          <table>
            <thead>
              <tr>
                <th>Party / person</th>
                <th>Role</th>
                <th>Status</th>
                <th>Provenance</th>
              </tr>
            </thead>
            <tbody>
              {list(forms.stakeholders).map((item: any) => (
                <tr key={item.id}>
                  <td>{text(item.party?.name_en || item.display_snapshot)}</td>
                  <td>{text(item.role_code)}</td>
                  <td>
                    <Chip value={item.status} />
                  </td>
                  <td>{text(item.source_type || "Human entered")}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!forms.stakeholders?.length && (
            <Empty>No stakeholders recorded yet.</Empty>
          )}
        </div>
      </Section>
      <Section
        title="Source evidence register"
        eyebrow="DOCUMENT / VERSION / CURRENTNESS"
      >
        <div className="proposal-table-wrap">
          <table>
            <thead>
              <tr>
                <th>Source</th>
                <th>Role / version</th>
                <th>Verification</th>
                <th>Currentness</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {proposal.sources.map((item: any) => (
                <tr key={item.id}>
                  <td>
                    <b>
                      {text(
                        item.source_filename ||
                          item.filename ||
                          sourceLabels[item.source_type],
                      )}
                    </b>
                    <small>{text(item.source_type)}</small>
                  </td>
                  <td>
                    {text(
                      item.source_role || item.version || "Source evidence",
                    )}
                  </td>
                  <td>
                    <Chip
                      value={item.verification_state || item.status}
                      tone={
                        item.verification_state === "READ_BACK_VERIFIED"
                          ? "pass"
                          : "neutral"
                      }
                    />
                  </td>
                  <td>
                    {text(
                      item.currentness_state || item.currentness || item.status,
                    )}
                  </td>
                  <td>
                    <button
                      className="text-button"
                      onClick={() => void readSource(item)}
                    >
                      Preview
                    </button>
                    <Lineage item={item} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!proposal.sources.length && (
            <Empty>No source evidence recorded yet.</Empty>
          )}
        </div>
        <div className="proposal-upload-row">
          <BusinessPicker
            label="Source type"
            value={sourceType}
            onChange={setSourceType}
            options={Object.entries(sourceLabels)
              .filter(([key]) => key !== "SITE_PHOTO")
              .map(([value, label]) => ({ value, label }))}
            placeholder="Choose source type"
            disabled={!editable}
          />
          <label>
            Upload new version
            <input
              type="file"
              disabled={!editable}
              onChange={(event) => setFile(event.target.files?.[0] || null)}
            />
          </label>
          <ServerAction
            label="Register source"
            onClick={() => void upload()}
            disabled={!editable || !file}
            reason={
              !editable
                ? "Intake is read-only at the current lifecycle stage."
                : "Choose a source file."
            }
            busy={busy}
          />
        </div>
      </Section>
      <Section title="Site photos" eyebrow="PHOTO EVIDENCE">
        <div className="proposal-photo-grid">
          {proposal.site_photos.map((item: any) => (
            <div key={item.id}>
              <b>{text(item.source_filename || "Site photo")}</b>
              <small>
                {dateText(item.created_at)} ·{" "}
                {text(item.currentness_state || item.status)}
              </small>
              <Lineage item={item} />
            </div>
          ))}
        </div>
        {!proposal.site_photos.length && (
          <Empty>No site photos recorded yet.</Empty>
        )}
        <p className="muted">
          Site photos remain governed evidence; storage references are never
          shown as ordinary inputs.
        </p>
      </Section>
      {selectedSource && (
        <div
          className="proposal-drawer"
          role="dialog"
          aria-label="Source content viewer"
        >
          <div className="proposal-drawer-head">
            <h2>Source content viewer</h2>
            <button
              className="icon-button"
              aria-label="Close source viewer"
              onClick={() => setSelectedSource(null)}
            >
              ×
            </button>
          </div>
          <p>
            {text(selectedSource.source_filename || selectedSource.filename)} ·{" "}
            {text(selectedSource.verification_state || selectedSource.status)}
          </p>
          <pre>{content || "Loading controlled source content…"}</pre>
          <Lineage item={selectedSource} />
        </div>
      )}
    </div>
  );
}

function Engineering({ proposal, role, refresh, setError, setMessage }: any) {
  const forms = proposal.forms_v2;
  const editable = engineers.has(role);
  const [scope, setScope] = useState("");
  const [assumption, setAssumption] = useState("");
  const [unknown, setUnknown] = useState("");
  const [conflict, setConflict] = useState("");
  const [contribution, setContribution] = useState("");
  const [cost, setCost] = useState("");
  const [busy, setBusy] = useState(false);
  const post = async (path: string, payload: any, message: string) => {
    if (!payload) return;
    setBusy(true);
    try {
      await api(`/api/bd/proposals/${proposal.id}/${path}`, {
        method: "POST",
        headers: { ...roleHeaders(role), "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      await refresh();
      setMessage(message);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="proposal-view-grid">
      <Section
        title="Service scope & scope of work"
        eyebrow="ENGINEERING PREPARATION"
      >
        <div className="proposal-split">
          <div>
            <h3>Client Scope of Work</h3>
            <p className="proposal-source-wording">
              {text(proposal.fields.client_scope_of_work)}
            </p>
          </div>
          <div>
            <h3>AMEC SOW / normalized scope</h3>
            <p>{text(proposal.fields.scope_of_work || proposal.fields.sow)}</p>
          </div>
        </div>
        <div className="proposal-table-wrap">
          <table>
            <thead>
              <tr>
                <th>Scope item</th>
                <th>Service</th>
                <th>Discipline</th>
                <th>Status</th>
                <th>Currentness</th>
              </tr>
            </thead>
            <tbody>
              {list(forms.service_scope_items).map((item: any) => (
                <tr key={item.id}>
                  <td>{text(item.description)}</td>
                  <td>{text(item.service_offering_code)}</td>
                  <td>{text(item.discipline_code)}</td>
                  <td>
                    <Chip value={item.status} />
                  </td>
                  <td>
                    {text(
                      item.currentness_state || item.source_document_version_id
                        ? "Evidence linked"
                        : "Source pending",
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!forms.service_scope_items?.length && (
            <Empty>No typed scope items recorded yet.</Empty>
          )}
        </div>
        <div className="proposal-inline-form">
          <input
            aria-label="Scope item"
            value={scope}
            onChange={(event) => setScope(event.target.value)}
            placeholder="Add a typed scope item"
          />
          <ServerAction
            label="Add scope item"
            onClick={() =>
              void post(
                "scope-items",
                {
                  description: scope,
                  service_offering_code: "PERMITTING",
                  included: true,
                  status: "DRAFT",
                },
                "Scope item recorded.",
              )
            }
            disabled={!editable || !scope.trim()}
            reason="Engineering write capability is not available for this role."
            busy={busy}
          />
        </div>
      </Section>
      <Section
        title="Regulatory scope"
        eyebrow="INTENT · NOT AUTHORITY APPROVAL"
      >
        <CompactRows
          items={list(forms.regulatory_scope_intents)}
          empty="No regulatory scope intents recorded yet."
        />
        {list(forms.regulatory_scope_intents).map((item: any) => (
          <div className="proposal-record-row" key={item.id}>
            <span>
              {text(item.service_type || item.service_type_id)} ·{" "}
              {text(item.jurisdiction || item.external_body)}
            </span>
            <Chip value={item.status} />
            {item.status !== "HUMAN_CONFIRMED_FOR_PROPOSAL" && (
              <button
                className="text-button"
                onClick={() =>
                  void post(
                    `regulatory-scope/${item.id}/confirm`,
                    {},
                    "Regulatory scope confirmed for Proposal planning.",
                  )
                }
              >
                Confirm for Proposal planning
              </button>
            )}
          </div>
        ))}
      </Section>
      <Section
        title="Assumptions, unknowns & conflicts"
        eyebrow="MATERIAL RISK"
      >
        <div className="proposal-three-columns">
          <RiskTable
            title="Assumptions"
            items={list(forms.assumptions)}
            label={(item) => item.statement}
            action={(item) =>
              void post(
                `assumptions/${item.id}/acknowledge`,
                {},
                "Assumption acknowledgement recorded; it is not resolution.",
              )
            }
            actionLabel="Acknowledge"
          />
          <RiskTable
            title="Unknowns"
            items={list(proposal.hardening.unknowns)}
            label={(item) => item.statement}
            action={() => undefined}
          />
          <RiskTable
            title="Conflicts"
            items={list(proposal.hardening.conflicts)}
            label={(item) =>
              `${item.field_code}: ${item.value_a} ↔ ${item.value_b}`
            }
            action={() => undefined}
          />
        </div>
        <div className="proposal-inline-form">
          <input
            aria-label="Assumption"
            value={assumption}
            onChange={(event) => setAssumption(event.target.value)}
            placeholder="Add assumption"
          />
          <ServerAction
            label="Record assumption"
            onClick={() =>
              void post(
                "assumptions",
                {
                  statement: assumption,
                  category: "ENGINEERING",
                  materiality: "MATERIAL",
                },
                "Assumption recorded.",
              )
            }
            disabled={!editable || !assumption.trim()}
            busy={busy}
          />
          <input
            aria-label="Unknown"
            value={unknown}
            onChange={(event) => setUnknown(event.target.value)}
            placeholder="Add unknown"
          />
          <ServerAction
            label="Record unknown"
            onClick={() =>
              void post(
                "unknowns",
                {
                  statement: unknown,
                  category: "ENGINEERING",
                  materiality: "MATERIAL",
                },
                "Unknown recorded.",
              )
            }
            disabled={!editable || !unknown.trim()}
            busy={busy}
          />
          <input
            aria-label="Conflict"
            value={conflict}
            onChange={(event) => setConflict(event.target.value)}
            placeholder="Describe source conflict"
          />
          <ServerAction
            label="Record conflict"
            onClick={() =>
              void post(
                "conflicts",
                {
                  field_code: "ENGINEERING_REVIEW",
                  source_a: "Source evidence",
                  source_b: "Proposal context",
                  value_a: conflict,
                  value_b: "Needs adjudication",
                  materiality: "MATERIAL",
                },
                "Conflict recorded without selecting a winner.",
              )
            }
            disabled={!editable || !conflict.trim()}
            busy={busy}
          />
        </div>
      </Section>
      <Section
        title="Engineering contributions"
        eyebrow="RESPONSIBLE PROFESSIONAL / DISCIPLINE"
      >
        <CompactRows
          items={list(forms.engineering_contributions)}
          empty="No Engineering contributions recorded yet."
        />
        <div className="proposal-inline-form">
          <input
            aria-label="Engineering contribution"
            value={contribution}
            onChange={(event) => setContribution(event.target.value)}
            placeholder="Describe contribution"
          />
          <ServerAction
            label="Add contribution"
            onClick={() =>
              void post(
                "engineering-contributions",
                {
                  content: contribution,
                  contribution_type: "TECHNICAL_SCOPE",
                  discipline_code: "GENERAL",
                },
                "Engineering contribution recorded.",
              )
            }
            disabled={!editable || !contribution.trim()}
            busy={busy}
          />
        </div>
        <p className="muted">
          Responsible Professional and source evidence are selected as business
          records when available; internal IDs are retained only in lineage.
        </p>
      </Section>
      <Section title="Expected Client Inputs" eyebrow="POLICY-DERIVED">
        <CompactRows
          items={list(
            forms.expected_client_inputs?.items ||
              forms.expected_client_inputs?.requirements,
          )}
          empty={text(
            forms.expected_client_inputs?.status,
            "No preview generated yet.",
          )}
        />
        <button
          className="button-secondary"
          disabled={!editable || busy}
          onClick={() =>
            void post(
              "expected-client-inputs/preview",
              {},
              "Expected Client Inputs refreshed from policy.",
            )
          }
        >
          Refresh expected inputs
        </button>
      </Section>
      <Section title="External / pass-through costs">
        <CompactRows
          items={list(forms.external_cost_assumptions)}
          empty="No external cost assumptions recorded yet."
        />
        <div className="proposal-inline-form">
          <input
            aria-label="External cost"
            value={cost}
            onChange={(event) => setCost(event.target.value)}
            placeholder="External cost description"
          />
          <ServerAction
            label="Add external cost"
            onClick={() =>
              void post(
                "external-costs",
                { description: cost, treatment: "ESTIMATE_ONLY" },
                "External cost assumption recorded.",
              )
            }
            disabled={!editable || !cost.trim()}
            busy={busy}
          />
        </div>
      </Section>
      <Readiness
        proposal={proposal}
        title="Engineering readiness"
        onNavigate={() => undefined}
      />
    </div>
  );
}
function RiskTable({
  title,
  items,
  label,
  action,
  actionLabel,
}: {
  title: string;
  items: any[];
  label: (item: any) => string;
  action: (item: any) => void;
  actionLabel?: string;
}) {
  return (
    <div className="proposal-risk-table">
      <h3>{title}</h3>
      {items.length ? (
        items.map((item, index) => (
          <div key={item.id || index}>
            <span>{text(label(item))}</span>
            <Chip
              value={item.materiality || item.status}
              tone={item.status === "ACKNOWLEDGED" ? "pass" : "blocked"}
            />
            {actionLabel && item.status !== "ACKNOWLEDGED" && (
              <button className="text-button" onClick={() => action(item)}>
                {actionLabel}
              </button>
            )}
          </div>
        ))
      ) : (
        <Empty>None recorded.</Empty>
      )}
    </div>
  );
}
function Readiness({
  proposal,
  title,
  onNavigate,
}: {
  proposal: any;
  title: string;
  onNavigate: (view: ViewKey) => void;
}) {
  const blockers = [
    ...list(proposal.validation?.blockers),
    ...list(proposal.readiness_v2?.blocking),
    ...list(proposal.intake_readiness?.blockers),
  ];
  return (
    <Section title={title} eyebrow="SERVER-OWNED">
      <div
        className={`proposal-readiness-banner ${blockers.length ? "blocked" : "pass"}`}
      >
        <b>{blockers.length ? `${blockers.length} blocker(s)` : "Ready"}</b>
        <span>{text(proposal.next_action?.label)}</span>
      </div>
      {blockers.map((item: any, index) => (
        <button
          className="proposal-blocker-link"
          key={index}
          onClick={() =>
            onNavigate(item.section === "sources" ? "intake" : "commercial")
          }
        >
          {text(item.label || item)}
        </button>
      ))}
    </Section>
  );
}

function Commercial({
  proposal,
  role,
  refresh,
  setError,
  setMessage,
  onNavigate,
}: any) {
  const c = proposal.commercial_controls;
  const lookups = useProposalLookups(proposal.id, role);
  const [busy, setBusy] = useState(false);
  const [assessment, setAssessment] = useState("PASS");
  const [findings, setFindings] = useState("");
  const [assessmentEvidence, setAssessmentEvidence] = useState("");
  const [eligibilityEvidence, setEligibilityEvidence] = useState("");
  const [scope, setScope] = useState("");
  const [service, setService] = useState("PERMITTING");
  const [professionalPartyId, setProfessionalPartyId] = useState("");
  const [capabilityReference, setCapabilityReference] = useState("");
  const [policyReference, setPolicyReference] = useState("");
  const [policyVersion, setPolicyVersion] = useState("");
  const evidenceOptions = governedEvidenceOptions(proposal);
  const post = async (path: string, payload: any, message: string) => {
    setBusy(true);
    try {
      await api(`/api/bd/proposals/${proposal.id}/${path}`, {
        method: "POST",
        headers: { ...roleHeaders(role), "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      await refresh();
      setMessage(message);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };
  const gateBlockers = list(proposal.validation?.blockers);
  const canAccept = Boolean(
    proposal.authority?.status !== "BLOCKED" &&
    proposal.validation?.ready &&
    (stageRank[proposal.stage] ?? 0) >= 2,
  );
  return (
    <div className="proposal-view-grid">
      <Section title="Commercial summary" eyebrow="TYPED COMMERCIAL BASIS">
        <div className="proposal-facts-grid">
          <Field
            label="Amount"
            value={
              proposal.fields.price
                ? new Intl.NumberFormat(undefined, {
                    maximumFractionDigits: 2,
                  }).format(Number(proposal.fields.price) || 0)
                : "Fee pending"
            }
          />
          <Field label="Currency" value={proposal.fields.currency} />
          <Field
            label="Duration"
            value={proposal.fields.duration || proposal.fields.period}
          />
          <Field label="Payment terms" value={proposal.fields.payment_terms} />
          <Field label="Validity" value={proposal.fields.proposal_validity} />
          <Field
            label="Inclusions / exclusions"
            value={`${text(proposal.fields.inclusions)} · ${text(proposal.fields.exclusions)}`}
          />
        </div>
      </Section>
      <Section title="Technical assessment" eyebrow="CONTROL CHAIN">
        <div className="proposal-control-state">
          <Field
            label="Result"
            value={
              c.technical_assessment?.result ||
              c.technical_assessment?.status ||
              "Not assessed"
            }
          />
          <Field
            label="Actor / date"
            value={`${text(c.technical_assessment?.assessed_by)} · ${dateText(c.technical_assessment?.assessed_at)}`}
          />
        </div>
        <div className="proposal-inline-form">
          <select
            aria-label="Technical assessment result"
            value={assessment}
            onChange={(event) => setAssessment(event.target.value)}
          >
            <option>PASS</option>
            <option>CONDITIONAL</option>
            <option>FAIL</option>
          </select>
          <input
            aria-label="Technical assessment findings"
            value={findings}
            onChange={(event) => setFindings(event.target.value)}
            placeholder="Assessment findings"
          />
          <BusinessPicker
            label="Evidence"
            value={assessmentEvidence}
            onChange={setAssessmentEvidence}
            options={evidenceOptions}
            placeholder="Select governed evidence"
          />
          <ServerAction
            label="Record assessment"
            onClick={() =>
              void post(
                "technical-assessments",
                {
                  result: assessment,
                  findings,
                  evidence_document_version_id: assessmentEvidence,
                },
                "Technical assessment recorded.",
              )
            }
            disabled={
              !engineers.has(role) || !findings.trim() || !assessmentEvidence
            }
            busy={busy}
          />
        </div>
      </Section>
      <Section title="Scope confirmation">
        <Field
          label="Exact scope under confirmation"
          value={scope || proposal.fields.scope_of_work || proposal.fields.sow}
        />
        <div className="proposal-inline-form">
          <input
            aria-label="Scope confirmation statement"
            value={scope}
            onChange={(event) => setScope(event.target.value)}
            placeholder="Confirm exact normalized scope"
          />
          <ServerAction
            label="Confirm current scope"
            onClick={() =>
              void post(
                "scope-confirmations",
                {
                  scope_statement:
                    scope ||
                    proposal.fields.scope_of_work ||
                    proposal.fields.sow,
                },
                "Current Proposal scope confirmed.",
              )
            }
            disabled={
              !owners.has(role) ||
              !Boolean(
                scope || proposal.fields.scope_of_work || proposal.fields.sow,
              )
            }
            busy={busy}
          />
        </div>
      </Section>
      <Section title="Service eligibility">
        <div className="proposal-facts-grid">
          <Field label="Service" value={service} />
          <Field
            label="Professional / discipline"
            value={
              c.service_eligibility?.[0]?.authority_snapshot?.display_name ||
              "Server-selected authority"
            }
          />
          <Field
            label="Capability / policy basis"
            value="Server-owned eligibility policy"
          />
          <Field
            label="Evidence / currentness"
            value={
              c.service_eligibility?.[0]?.evidence_sha256
                ? "Evidence current"
                : "Evidence pending"
            }
          />
        </div>
        <div className="proposal-inline-form">
          <BusinessPicker
            label="Service"
            value={service}
            onChange={setService}
            options={[
              { value: "PERMITTING", label: "Permitting" },
              { value: "DESIGN", label: "Design" },
              { value: "CONSULTANCY", label: "Consultancy" },
            ]}
            placeholder="Choose service"
          />
          <BusinessPicker
            label="Responsible Professional / Party"
            value={professionalPartyId}
            onChange={setProfessionalPartyId}
            options={lookups.parties}
            placeholder={
              lookups.parties.length
                ? "Select current professional Party"
                : "No current Parties available"
            }
            disabled={!owners.has(role) || !lookups.parties.length}
          />
          <input
            aria-label="Capability reference"
            value={capabilityReference}
            onChange={(event) => setCapabilityReference(event.target.value)}
            placeholder="Dashboard capability reference"
          />
          <input
            aria-label="Policy reference"
            value={policyReference}
            onChange={(event) => setPolicyReference(event.target.value)}
            placeholder="Dashboard policy reference"
          />
          <input
            aria-label="Policy version"
            value={policyVersion}
            onChange={(event) => setPolicyVersion(event.target.value)}
            placeholder="Policy version"
          />
          <BusinessPicker
            label="Eligibility evidence"
            value={eligibilityEvidence}
            onChange={setEligibilityEvidence}
            options={evidenceOptions}
            placeholder="Select governed eligibility evidence"
          />
          <ServerAction
            label="Record service eligibility"
            onClick={() =>
              void post(
                "service-eligibility",
                {
                  service_offering_code: service,
                  result: "ELIGIBLE",
                  professional_party_id: professionalPartyId,
                  discipline: "GENERAL",
                  capability_reference: capabilityReference,
                  policy_reference: policyReference,
                  policy_version: policyVersion,
                  scope_confirmation_id: c.scope_confirmation?.id,
                  scope_revision_hash:
                    c.scope_confirmation?.scope_revision_hash,
                  evidence_document_version_id: eligibilityEvidence,
                },
                "Service eligibility recorded by the server.",
              )
            }
            disabled={
              !owners.has(role) ||
              !eligibilityEvidence ||
              !professionalPartyId ||
              !capabilityReference.trim() ||
              !policyReference.trim() ||
              !policyVersion.trim()
            }
            reason="Select a professional Party and provide Dashboard capability/policy references."
            busy={busy}
          />
        </div>
      </Section>
      <Section title="Proposal Acceptance" eyebrow="PROTECTED HUMAN ACTION">
        <div className="proposal-acceptance-gate">
          <Field
            label="Exact revision"
            value={
              proposal.draft_revision
                ? `Working R${proposal.draft_revision.revision_number}`
                : proposal.current_revision
                  ? `Accepted R${proposal.current_revision.revision_number}`
                  : "No accepted revision"
            }
            mono
          />
          <Field
            label="Readiness"
            value={proposal.validation?.ready ? "Ready" : "Blocked"}
          />
          <Field
            label="Template / checklist"
            value={`${text(proposal.configuration?.proposal_template?.ref)} · ${text(proposal.configuration?.proposal_checklist?.ref)}`}
          />
          <Field
            label="Material unresolved items"
            value={
              list(proposal.hardening?.material_open_unknowns).length +
              list(proposal.hardening?.material_open_conflicts).length
            }
          />
        </div>
        <ServerAction
          label={
            proposal.draft_revision
              ? `Accept revised Proposal R${proposal.draft_revision.revision_number}`
              : "Accept Proposal"
          }
          onClick={() =>
            void post(
              "accept",
              {},
              "Proposal revision accepted by a human operator.",
            )
          }
          disabled={!owners.has(role) || !canAccept}
          reason={
            !owners.has(role)
              ? "This protected action is not available to the current role."
              : gateBlockers[0]?.label || "Server readiness is not clear."
          }
          busy={busy}
        />
        <p className="muted">
          Proposal acceptance is separate from Commercial Release, Client
          Acceptance, and Contract Handoff.
        </p>
      </Section>
      <Readiness
        proposal={proposal}
        title="Commercial readiness"
        onNavigate={onNavigate}
      />
    </div>
  );
}

function Response({
  proposal,
  role,
  refresh,
  setError,
  setMessage,
  onNavigate,
}: any) {
  const c = proposal.commercial_controls;
  const accepted = proposal.current_revision;
  const lookups = useProposalLookups(proposal.id, role);
  const [busy, setBusy] = useState(false);
  const [response, setResponse] = useState("ACCEPTED");
  const [notes, setNotes] = useState("");
  const [evidence, setEvidence] = useState("");
  const [outcome, setOutcome] = useState("");
  const [lpo, setLpo] = useState("");
  const [clientContactId, setClientContactId] = useState("");
  const evidenceOptions = governedEvidenceOptions(proposal);
  const post = async (path: string, payload: any, message: string) => {
    setBusy(true);
    try {
      await api(`/api/bd/proposals/${proposal.id}/${path}`, {
        method: "POST",
        headers: { ...roleHeaders(role), "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      await refresh();
      setMessage(message);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };
  const distribution = c.distribution;
  const clientResponse = list(proposal.hardening?.client_responses).slice(
    -1,
  )[0];
  return (
    <div className="proposal-view-grid">
      <Section
        title="Commercial release → distribution → response"
        eyebrow="CHRONOLOGY"
      >
        <div className="proposal-chronology">
          <span className={c.commercial_release ? "done" : "pending"}>
            1. Commercial Release
          </span>
          <span className={distribution ? "done" : "pending"}>
            2. Distribution
          </span>
          <span className={clientResponse ? "done" : "pending"}>
            3. Client Response
          </span>
          <span className={c.acceptance_verification ? "done" : "pending"}>
            4. Acceptance Verification
          </span>
          <span className={c.lpo_reconciliation ? "done" : "pending"}>
            5. LPO / PO
          </span>
          <span
            className={
              proposal.contract_eligibility?.eligible ? "done" : "pending"
            }
          >
            6. Handoff
          </span>
        </div>
      </Section>
      <Section title="Commercial Release">
        <div className="proposal-facts-grid">
          <Field
            label="Accepted revision"
            value={accepted ? `R${accepted.revision_number}` : "Required"}
          />
          <Field
            label="Release state"
            value={c.commercial_release?.status || "Not released"}
          />
          <Field
            label="Scope state"
            value={c.scope_confirmation?.status || "Not confirmed"}
          />
          <Field
            label="Eligibility state"
            value={c.service_eligibility?.length ? "Recorded" : "Required"}
          />
        </div>
        <ServerAction
          label="Authorize Commercial Release"
          onClick={() =>
            void post(
              "commercial-release",
              {},
              "Commercial Release authorization recorded.",
            )
          }
          disabled={!owners.has(role) || !accepted}
          reason={
            !accepted
              ? "Accept an exact Proposal revision first."
              : "Role is not authorized."
          }
          busy={busy}
        />
      </Section>
      <Section title="Distribution">
        <div className="proposal-facts-grid">
          <Field
            label="Accepted revision"
            value={text(distribution?.accepted_revision_id, "Not distributed")}
            mono
          />
          <Field
            label="Artifact"
            value={
              distribution?.output_artifact_hash
                ? `Output ${String(distribution.output_artifact_hash).slice(0, 10)}`
                : "Required"
            }
            mono
          />
          <Field
            label="Recipient"
            value={distribution?.recipient_contact_reference}
          />
          <Field label="Status" value={distribution?.delivery_status} />
        </div>
        <div className="proposal-inline-form">
          <BusinessPicker
            label="Evidence"
            value={evidence}
            onChange={setEvidence}
            options={evidenceOptions}
            placeholder="Select distribution evidence"
          />
          <BusinessPicker
            label="Channel"
            value="CLIENT_PORTAL"
            onChange={() => undefined}
            options={[
              { value: "CLIENT_PORTAL", label: "Client portal" },
              { value: "EMAIL", label: "Email" },
              { value: "MEETING", label: "Meeting" },
            ]}
            placeholder="Choose channel"
          />
          <ServerAction
            label="Record distribution"
            onClick={() =>
              void post(
                "distribution",
                {
                  channel: "CLIENT_PORTAL",
                  evidence_document_version_id: evidence,
                  evidence_reference: "Selected governed evidence",
                  delivery_status: "EXTERNAL_EVIDENCE_RECORDED",
                  output_artifact_id: proposal.outputs?.proposal?.id,
                  output_artifact_hash:
                    proposal.outputs?.proposal?.content_hash,
                },
                "Distribution record saved.",
              )
            }
            disabled={!owners.has(role) || !evidence || !c.commercial_release}
            reason="Commercial Release and evidence are required."
            busy={busy}
          />
        </div>
      </Section>
      <Section title="Client Response">
        <div className="proposal-table-wrap">
          <table>
            <thead>
              <tr>
                <th>Response</th>
                <th>Revision</th>
                <th>Evidence</th>
                <th>Recorded</th>
              </tr>
            </thead>
            <tbody>
              {list(proposal.hardening?.client_responses).map((item: any) => (
                <tr key={item.id}>
                  <td>
                    <Chip value={item.response_type} />
                  </td>
                  <td>{text(item.accepted_revision_id, "Working context")}</td>
                  <td>{text(item.evidence_reference)}</td>
                  <td>{dateText(item.recorded_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!proposal.hardening?.client_responses?.length && (
            <Empty>No Client Response recorded.</Empty>
          )}
        </div>
        <div className="proposal-inline-form">
          <BusinessPicker
            label="Client Contact"
            value={clientContactId}
            onChange={setClientContactId}
            options={lookups.contacts}
            placeholder={
              lookups.contacts.length
                ? "Select Client Contact"
                : "No active Client Contacts"
            }
          />
          <BusinessPicker
            label="Evidence"
            value={evidence}
            onChange={setEvidence}
            options={evidenceOptions}
            placeholder="Select response evidence"
          />
          <select
            aria-label="Client Response type"
            value={response}
            onChange={(event) => setResponse(event.target.value)}
          >
            <option>ACCEPTED</option>
            <option>CHANGE_REQUESTED</option>
            <option>DECLINED</option>
            <option>EXPIRED</option>
          </select>
          <input
            aria-label="Client Response notes"
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            placeholder="Response notes"
          />
          <ServerAction
            label="Record Client Response"
            onClick={() =>
              void post(
                "client-responses",
                {
                  response_type: response,
                  notes,
                  accepted_revision_id: accepted?.id,
                  client_account_id: proposal.client_account_id,
                  client_contact_id: clientContactId,
                  evidence_document_version_id: evidence,
                  evidence_reference: "Selected governed evidence",
                },
                "Client Response recorded against the accepted revision.",
              )
            }
            disabled={
              !owners.has(role) || !accepted || !clientContactId || !evidence
            }
            reason="An accepted revision is required."
            busy={busy}
          />
        </div>
      </Section>
      <Section title="Acceptance verification" eyebrow="DISTINCT HUMAN CONTROL">
        <Field
          label="Verification state"
          value={c.acceptance_verification?.status || "Not verified"}
        />
        <ServerAction
          label="Verify Client Acceptance"
          onClick={() =>
            void post(
              "acceptance-verification",
              {
                client_response_id: clientResponse?.id,
                accepted_revision_id: accepted?.id,
                evidence_document_version_id: evidence,
                evidence_reference: "Selected governed evidence",
              },
              "Client Acceptance Verification recorded.",
            )
          }
          disabled={
            !owners.has(role) || clientResponse?.response_type !== "ACCEPTED"
          }
          reason="A recorded Accepted Client Response and evidence are required."
          busy={busy}
        />
      </Section>
      <Section title="Commercial outcome">
        <Field
          label="Current outcome"
          value={text(
            proposal.hardening?.commercial_outcome?.outcome,
            "Not recorded",
          )}
        />
        <div className="proposal-inline-form">
          <select
            aria-label="Commercial outcome"
            value={outcome}
            onChange={(event) => setOutcome(event.target.value)}
          >
            <option value="">Select outcome</option>
            <option>WON</option>
            <option>LOST</option>
            <option>WITHDRAWN</option>
            <option>EXPIRED</option>
          </select>
          <ServerAction
            label="Record outcome"
            onClick={() =>
              void post(
                "commercial-outcome",
                { outcome, reason: "Recorded in Proposal workspace" },
                "Commercial outcome recorded.",
              )
            }
            disabled={!owners.has(role) || !outcome}
            busy={busy}
          />
        </div>
      </Section>
      <Section title="LPO / PO comparison" eyebrow="SERVER RECONCILIATION">
        <div className="proposal-comparison">
          <b>Accepted Proposal</b>
          <b>LPO / PO</b>
          <span>Scope</span>
          <span>
            {text(proposal.fields.scope_of_work || proposal.fields.sow)}
          </span>
          <span>Amount / currency</span>
          <span>
            {text(proposal.fields.price)} {text(proposal.fields.currency, "")}
          </span>
          <span>Server result</span>
          <Chip
            value={c.lpo_reconciliation?.result || "Not compared"}
            tone={c.lpo_reconciliation?.result === "PASS" ? "pass" : "neutral"}
          />
        </div>
        <div className="proposal-inline-form">
          <BusinessPicker
            label="LPO evidence"
            value={lpo}
            onChange={setLpo}
            options={evidenceOptions}
            placeholder="Select LPO evidence"
          />
          <ServerAction
            label="Run LPO reconciliation"
            onClick={() =>
              void post(
                "lpo-reconciliation",
                { applies: true, client_document_version_id: lpo },
                "LPO reconciliation recorded by the server.",
              )
            }
            disabled={!owners.has(role) || !accepted || !lpo}
            reason="Accepted revision and governed LPO evidence are required."
            busy={busy}
          />
        </div>
      </Section>
      <Handoff
        proposal={proposal}
        role={role}
        busy={busy}
        post={post}
        onNavigate={onNavigate}
      />
    </div>
  );
}

function Handoff({ proposal, role, busy, post, onNavigate }: any) {
  const checks = list(proposal.contract_eligibility?.blockers);
  return (
    <Section
      title="Contract Handoff readiness"
      eyebrow="DETERMINISTIC PREFLIGHT"
    >
      <div className="proposal-preflight-list">
        {[
          "Accepted revision",
          "Commercial Release",
          "Current scope",
          "Service eligibility",
          "No active staleness",
          "Valid Proposal outputs",
          "Distribution",
          "Client acceptance",
          "LPO reconciliation",
        ].map((label) => {
          const serverBlocked = !proposal.contract_eligibility?.eligible;
          return (
            <div key={label}>
              <span>{label}</span>
              <Chip
                value={serverBlocked ? "BLOCKED" : "PASS"}
                tone={serverBlocked ? "blocked" : "pass"}
              />
            </div>
          );
        })}
      </div>
      <div className="proposal-facts-grid">
        <Field
          label="Server eligibility"
          value={
            proposal.contract_eligibility?.eligible ? "Eligible" : "Blocked"
          }
        />
        <Field label="Reasons" value={checks.join(" · ")} />
      </div>
      <ServerAction
        label="Open Contract Handoff"
        onClick={() =>
          void post(
            "handoff/contract",
            {},
            "Contract Handoff command accepted by the server.",
          )
        }
        disabled={!owners.has(role) || !proposal.contract_eligibility?.eligible}
        reason={checks[0] || "Current user is not authorized."}
        busy={busy}
      />
      <button className="text-button" onClick={() => onNavigate("history")}>
        View handoff lineage →
      </button>
    </Section>
  );
}

function ProposalIntelligencePanel({
  proposal,
  role,
  setError,
  setMessage,
}: any) {
  const [operation, setOperation] = useState("tender-intake-analysis");
  const [result, setResult] = useState<any>(null);
  const [reviews, setReviews] = useState<any[]>([]);
  const [editedDraft, setEditedDraft] = useState("");
  const [sectionType, setSectionType] = useState("Executive Summary");
  const [busy, setBusy] = useState(false);
  const requiresAccepted =
    operation === "lpo-variance-analysis" || operation === "handoff-preflight";
  const loadReviews = async () => {
    try {
      const response = await api<any>(
        `/api/bd/proposals/${proposal.id}/intelligence/reviews`,
        { headers: roleHeaders(role) },
      );
      setReviews(list(response?.items));
    } catch (cause) {
      setError(cause);
    }
  };
  const run = async () => {
    setBusy(true);
    try {
      const response = await api<any>(
        `/api/bd/proposals/${proposal.id}/intelligence`,
        {
          method: "POST",
          headers: { ...roleHeaders(role), "Content-Type": "application/json" },
          body: JSON.stringify({
            operation,
            idempotency_key: `proposal-intelligence-${proposal.id}-${operation}`,
          }),
        },
      );
      setResult(response);
      await loadReviews();
      setMessage(
        "Proposal Intelligence result is ready for human review; protected Proposal state was not changed.",
      );
    } catch (cause) {
      setError(cause);
    } finally {
      setBusy(false);
    }
  };
  const decide = async (item: any, decision: string) => {
    try {
      await api(
        `/api/bd/proposals/${proposal.id}/intelligence/reviews/${item.binding_id}/decision`,
        {
          method: "POST",
          headers: { ...roleHeaders(role), "Content-Type": "application/json" },
          body: JSON.stringify({
            decision,
            idempotency_key: `proposal-review-${item.binding_id}-${decision}`,
            precondition_version: item.precondition_version || "",
          }),
        },
      );
      await loadReviews();
      setMessage(
        `Proposal Intelligence review ${decision.toLowerCase()} recorded.`,
      );
    } catch (cause) {
      setError(cause);
    }
  };
  const latestReview = reviews.length ? reviews[reviews.length - 1] : undefined;
  // Provider responses are schema-validated on the server, but individual
  // structured fields may still be arrays/objects. Keep the browser render
  // boundary data-safe: React must never receive a provider object as a child
  // or as a textarea value.
  const rawOutput = result?.output || latestReview?.output;
  const output = rawOutput ? record(rawOutput) : null;
  const applyDraft = async () => {
    const workProductId =
      result?.work_product_id || latestReview?.work_product_id;
    if (!workProductId || !proposal.draft_revision || !editedDraft.trim())
      return;
    try {
      await api(
        `/api/bd/proposals/${proposal.id}/intelligence/section-draft/apply`,
        {
          method: "POST",
          headers: { ...roleHeaders(role), "Content-Type": "application/json" },
          body: JSON.stringify({
            work_product_id: workProductId,
            working_revision_id: proposal.draft_revision.id,
            working_revision_hash: proposal.draft_revision.content_hash,
            section_type: sectionType,
            edited_content: editedDraft,
          }),
        },
      );
      setMessage(
        "Human-edited section draft applied to the working Proposal revision; accepted history is unchanged.",
      );
    } catch (cause) {
      setError(cause);
    }
  };
  return (
    <Section
      title="Proposal Intelligence"
      eyebrow="ASSISTIVE · SOURCE-GROUNDED · HUMAN REVIEW"
    >
      <p className="muted">
        AI assistance can explain evidence, gaps, and draft content. It cannot
        verify facts, accept a Proposal, release commercially, or create a
        Contract handoff.
      </p>
      <div className="proposal-inline-form">
        <BusinessPicker
          label="Experience"
          value={operation}
          onChange={setOperation}
          options={[
            {
              value: "tender-intake-analysis",
              label: "Intake · Analyze Tender",
            },
            {
              value: "requirement-evidence-analysis",
              label: "Requirements & evidence gaps",
            },
            { value: "section-draft", label: "Draft with evidence" },
            {
              value: "commercial-consistency-review",
              label: "Commercial consistency review",
            },
            { value: "lpo-variance-analysis", label: "LPO compare" },
            { value: "handoff-preflight", label: "Handoff preflight" },
          ]}
          placeholder="Choose Proposal Intelligence experience"
        />
        <ServerAction
          label={busy ? "Running…" : "Run Proposal Intelligence"}
          onClick={() => void run()}
          disabled={busy || (requiresAccepted && !proposal.current_revision)}
          reason={
            requiresAccepted ? "An accepted revision is required." : undefined
          }
          busy={busy}
        />
      </div>
      {output && (
        <div className="proposal-intelligence-result" aria-live="polite">
          <b>
            {text(
              output.summary ||
                output.explanation ||
                output.draft_content ||
                "Structured result returned.",
            )}
          </b>
          {output.missing_information?.length > 0 && (
            <p>
              <strong>Missing information:</strong>{" "}
              {output.missing_information.join(" · ")}
            </p>
          )}
          {output.contradictions?.length > 0 && (
            <p>
              <strong>Contradictions:</strong>{" "}
              {output.contradictions.join(" · ")}
            </p>
          )}
          {output.deterministic_blockers?.length > 0 && (
            <p>
              <strong>Server blockers:</strong>{" "}
              {output.deterministic_blockers.join(" · ")}
            </p>
          )}
          {output.draft_only && (
            <>
              <label>
                Section
                <select
                  value={sectionType}
                  onChange={(event) => setSectionType(event.target.value)}
                >
                  <option>Executive Summary</option>
                  <option>Understanding of Requirements</option>
                  <option>Methodology</option>
                  <option>Scope of Services</option>
                  <option>Deliverables</option>
                  <option>Programme</option>
                  <option>Commercials</option>
                  <option>Assumptions</option>
                  <option>Exclusions</option>
                </select>
              </label>
              <label>
                Human-edited working draft
                <textarea
                  value={editedDraft || text(output.draft_content, "")}
                  onChange={(event) => setEditedDraft(event.target.value)}
                />
              </label>
              <ServerAction
                label="Apply to working draft"
                onClick={() => void applyDraft()}
                disabled={!proposal.draft_revision || !editedDraft.trim()}
                reason="A working Proposal revision and edited content are required."
                busy={busy}
              />
            </>
          )}
          <small>
            Citations: {(output.citation_keys || []).join(", ") || "none"} ·
            server-selected sources · human review required
          </small>
        </div>
      )}
      {reviews.length > 0 && (
        <div className="proposal-review-list">
          <b>Proposal-owned review work</b>
          {reviews.map((item: any) => (
            <div key={item.binding_id}>
              <span>
                {item.skill_id || "Proposal result"} ·{" "}
                {item.work_product_state || "UNKNOWN"}
              </span>
              {item.actionable && (
                <>
                  <button
                    className="text-button"
                    onClick={() => void decide(item, "ACCEPT")}
                  >
                    Accept review
                  </button>
                  <button
                    className="text-button"
                    onClick={() => void decide(item, "CORRECT")}
                  >
                    Correct
                  </button>
                  <button
                    className="text-button"
                    onClick={() => void decide(item, "REJECT")}
                  >
                    Reject
                  </button>
                  <button
                    className="text-button"
                    onClick={() => void decide(item, "DEFER")}
                  >
                    Defer
                  </button>
                  <button
                    className="text-button"
                    onClick={() => void decide(item, "ESCALATE")}
                  >
                    Escalate
                  </button>
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </Section>
  );
}

function Outputs({
  proposal,
  onNavigate,
  role,
  setError,
  setMessage,
}: {
  proposal: any;
  onNavigate: (view: ViewKey) => void;
  role: ProposalRole;
  setError: (error: any) => void;
  setMessage: (message: string) => void;
}) {
  const revisions = list(proposal.revision_history);
  const outputs = [
    proposal.outputs?.proposal,
    proposal.outputs?.checklist,
  ].filter(Boolean);
  const selected = revisions[0];
  return (
    <div className="proposal-view-grid">
      <Section title="Revision center" eyebrow="REVIEW / OUTPUTS">
        <div className="proposal-table-wrap">
          <table>
            <thead>
              <tr>
                <th>Revision</th>
                <th>Status</th>
                <th>Created / accepted</th>
                <th>Created by</th>
                <th>Content hash</th>
                <th>Compare</th>
              </tr>
            </thead>
            <tbody>
              {revisions.map((item: any) => (
                <tr key={item.id}>
                  <td>
                    <b>R{item.revision_number}</b>
                  </td>
                  <td>
                    <Chip value="ACCEPTED" tone="pass" />
                  </td>
                  <td>{dateText(item.accepted_at)}</td>
                  <td>{text(item.accepted_by)}</td>
                  <td className="mono">
                    {text(item.content_hash).slice(0, 14)}
                  </td>
                  <td>
                    <button
                      className="text-button"
                      onClick={() => onNavigate("history")}
                    >
                      Inspect lineage
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!revisions.length && (
            <Empty>No accepted revisions recorded yet.</Empty>
          )}
        </div>
        <p className="muted">
          The accepted revision remains pinned to its exact Proposal Template
          and Checklist versions. A later draft does not replace R1.
        </p>
        {selected && (
          <div className="proposal-pinned-grid">
            <Field
              label="Pinned Proposal Template"
              value={`${text(proposal.configuration?.accepted_revision?.proposal_template?.ref || selected.template?.ref)} · v${text(proposal.configuration?.accepted_revision?.proposal_template?.version || selected.template?.version)}`}
            />
            <Field
              label="Pinned Checklist"
              value={`${text(proposal.configuration?.accepted_revision?.proposal_checklist?.ref || selected.checklist?.ref)} · v${text(proposal.configuration?.accepted_revision?.proposal_checklist?.version || selected.checklist?.version)}`}
            />
            <Field
              label="Accepted content hash"
              value={selected.content_hash}
              mono
            />
          </div>
        )}
      </Section>
      <Section
        title="Accepted vs working Proposal"
        eyebrow="SELECTED REVISION COMPARISON"
      >
        {proposal.current_revision ? (
          <div className="proposal-table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Typed field</th>
                  <th>Accepted R{proposal.current_revision.revision_number}</th>
                  <th>Working revision</th>
                  <th>State</th>
                </tr>
              </thead>
              <tbody>
                {Array.from(
                  new Set([
                    ...Object.keys(
                      record(proposal.current_revision.snapshot?.fields),
                    ),
                    ...Object.keys(
                      record(
                        proposal.draft_revision?.snapshot?.fields ||
                          proposal.fields,
                      ),
                    ),
                  ]),
                )
                  .sort()
                  .map((key) => {
                    const acceptedValue = record(
                      proposal.current_revision.snapshot?.fields,
                    )[key];
                    const workingValue = record(
                      proposal.draft_revision?.snapshot?.fields ||
                        proposal.fields,
                    )[key];
                    const changed =
                      text(acceptedValue, "") !== text(workingValue, "");
                    return (
                      <tr key={key}>
                        <td>{key.replaceAll("_", " ")}</td>
                        <td>{text(acceptedValue, "—")}</td>
                        <td>{text(workingValue, "—")}</td>
                        <td>
                          <Chip
                            value={changed ? "CHANGED" : "UNCHANGED"}
                            tone={changed ? "blocked" : "pass"}
                          />
                        </td>
                      </tr>
                    );
                  })}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty>
            Accept a Proposal revision before comparing a working Proposal.
          </Empty>
        )}
        <p className="muted">
          The comparison is presentation-only. Acceptance, revision hashes,
          currentness, and server readiness remain authoritative in the backend.
        </p>
      </Section>
      <Section title="Output artifact history">
        <div className="proposal-table-wrap">
          <table>
            <thead>
              <tr>
                <th>Artifact</th>
                <th>Revision</th>
                <th>Filename</th>
                <th>Hash</th>
                <th>Created</th>
                <th>Download</th>
              </tr>
            </thead>
            <tbody>
              {outputs.map((item: any) => (
                <tr key={item.id || item.filename}>
                  <td>{item.artifact_type || "Proposal output"}</td>
                  <td>{selected ? `R${selected.revision_number}` : "—"}</td>
                  <td>{text(item.filename)}</td>
                  <td className="mono">
                    {text(item.content_hash).slice(0, 14)}
                  </td>
                  <td>{dateText(item.created_at)}</td>
                  <td>
                    <a
                      className="text-button"
                      href={`/api/bd/proposals/${proposal.id}/outputs/${String(item.artifact_type || "proposal").toLowerCase()}`}
                      download
                    >
                      Download
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!outputs.length && (
            <Empty>No Proposal or Checklist artifacts available yet.</Empty>
          )}
        </div>
      </Section>
      <ProposalIntelligencePanel
        proposal={proposal}
        role={role}
        setError={setError}
        setMessage={setMessage}
      />
    </div>
  );
}

function History({ proposal, role, refresh, setError, setMessage }: any) {
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");
  const stale = list(proposal.hardening?.active_staleness);
  const revalidate = async () => {
    setBusy(true);
    try {
      await api(`/api/bd/proposals/${proposal.id}/staleness/revalidate`, {
        method: "POST",
        headers: { ...roleHeaders(role), "Content-Type": "application/json" },
        body: JSON.stringify({
          revision_id: proposal.draft_revision?.id,
          result: "PASS",
          event_ids: stale.map((item: any) => item.id),
        }),
      });
      await refresh();
      setMessage(
        "Staleness revalidation submitted and server projection refreshed.",
      );
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };
  const command = async (path: string, payload: any, message: string) => {
    setBusy(true);
    try {
      await api(`/api/bd/proposals/${proposal.id}/${path}`, {
        method: "POST",
        headers: { ...roleHeaders(role), "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      await refresh();
      setMessage(message);
      if (path === "notes") setNote("");
    } catch (cause) {
      setError(cause);
    } finally {
      setBusy(false);
    }
  };
  const events = list(proposal.stage_history);
  return (
    <div className="proposal-view-grid">
      <Section title="History & lineage" eyebrow="AUDIT SURFACE">
        <div className="proposal-filter-pills">
          <span>Lifecycle events</span>
          <span>Revisions</span>
          <span>Sources</span>
          <span>Evidence</span>
          <span>Outputs</span>
          <span>Commercial controls</span>
          <span>Staleness</span>
          <span>Acknowledgements</span>
          <span>Handoff</span>
        </div>
        <div className="proposal-timeline">
          {events.map((event: any, index) => (
            <div key={index}>
              <span className="proposal-timeline-dot" />
              <div>
                <b>{statusText(event.event_type)}</b>
                <p>
                  {text(event.actor)} · {dateText(event.occurred_at)}
                </p>
                <small>{text(event.after, "Business event recorded")}</small>
                <Lineage item={event} />
              </div>
            </div>
          ))}
        </div>
        {!events.length && <Empty>No lifecycle history recorded yet.</Empty>}
      </Section>
      <Section title="Currentness / staleness" eyebrow="DEPENDENCY REVIEW">
        <div
          className={`proposal-readiness-banner ${stale.length ? "blocked" : "pass"}`}
        >
          <b>
            {stale.length
              ? `${stale.length} active staleness event(s)`
              : "No active staleness events"}
          </b>
          <span>
            {stale.length
              ? "A new draft is not the same as a resolved review."
              : "Current evidence is not reporting an active event."}
          </span>
        </div>
        {stale.map((item: any) => (
          <div className="proposal-record-row" key={item.id}>
            <div>
              <b>{text(item.reason_code || item.trigger)}</b>
              <small>
                {text(item.impacted_sections)} · {dateText(item.created_at)}
              </small>
            </div>
            <Chip value={item.status} tone="blocked" />
            <Lineage item={item} />
          </div>
        ))}
        {stale.length > 0 && (
          <ServerAction
            label="Review / revalidate currentness"
            onClick={() => void revalidate()}
            disabled={!proposal.draft_revision}
            reason="Create a working Proposal revision before causal revalidation."
            busy={busy}
          />
        )}
        <ServerAction
          label="Record server staleness review"
          onClick={() =>
            void command(
              "staleness/review",
              {},
              "Staleness review submitted to the server.",
            )
          }
          disabled={!stale.length || busy}
          reason="There are no active staleness events."
          busy={busy}
        />
      </Section>
      <Section
        title="Material acknowledgements & notes"
        eyebrow="AUDITABLE HUMAN CONTEXT"
      >
        <div className="proposal-risk-table">
          {[
            ...list(proposal.hardening?.unknowns).map((item: any) => ({
              ...item,
              target_type: "PROPOSAL_UNKNOWN",
              label: "Unknown",
            })),
            ...list(proposal.hardening?.conflicts).map((item: any) => ({
              ...item,
              target_type: "PROPOSAL_CONFLICT",
              label: "Conflict",
            })),
          ].map((item: any) => (
            <div key={`${item.target_type}-${item.id}`}>
              <span>
                {item.label}: {text(item.statement || item.field_code)}
              </span>
              <ServerAction
                label="Acknowledge"
                onClick={() =>
                  void command(
                    "acknowledgments",
                    {
                      target_type: item.target_type,
                      target_id: item.id,
                      note: "Acknowledged in Proposal history.",
                    },
                    `${item.label} acknowledgement recorded; it is not resolution.`,
                  )
                }
                disabled={!owners.has(role) || busy}
                busy={busy}
              />
            </div>
          ))}
          {!proposal.hardening?.unknowns?.length &&
            !proposal.hardening?.conflicts?.length && (
              <Empty>
                No material unknowns or conflicts require acknowledgement.
              </Empty>
            )}
        </div>
        <div className="proposal-inline-form">
          <label>
            Internal Proposal note
            <textarea
              aria-label="Proposal history note"
              value={note}
              onChange={(event) => setNote(event.target.value)}
              placeholder="Record context without converting it into a verified fact."
            />
          </label>
          <ServerAction
            label="Add note"
            onClick={() =>
              void command(
                "notes",
                { content: note, note_type: "INTERNAL_INTAKE" },
                "Proposal note recorded in audit history.",
              )
            }
            disabled={!owners.has(role) || !note.trim()}
            reason="Enter a note first."
            busy={busy}
          />
        </div>
        <CompactRows
          items={list(proposal.notes)}
          empty="No notes recorded yet."
        />
      </Section>
      <Section title="Configuration & decision history">
        <div className="proposal-facts-grid">
          <Field
            label="Proposal Template"
            value={
              proposal.configuration?.proposal_template?.title ||
              proposal.configuration?.proposal_template?.ref
            }
          />
          <Field
            label="Proposal Checklist"
            value={
              proposal.configuration?.proposal_checklist?.title ||
              proposal.configuration?.proposal_checklist?.ref
            }
          />
          <Field
            label="Definitions"
            value={proposal.configuration?.definitions?.count}
          />
          <Field
            label="Engineering references"
            value={proposal.configuration?.engineering_references?.status}
          />
        </div>
        <p className="muted">
          Owner settings are managed through the Decision Center; their history
          remains server-owned and is not stored in React.
        </p>
        <button
          className="button-secondary"
          onClick={() =>
            window.history.pushState({}, "", "/opportunities?view=settings")
          }
        >
          Open Decision Center
        </button>
      </Section>
    </div>
  );
}

export function ProposalWorkspace({
  role,
  proposal,
  setProposal,
  onBack,
  message,
  setMessage,
  error,
  setError,
}: any) {
  const [view, setView] = useState<ViewKey>(
    () =>
      (new URLSearchParams(window.location.search).get("view") as ViewKey) ||
      "overview",
  );
  const [railOpen, setRailOpen] = useState(true);
  const refresh = async (next?: any) => {
    try {
      const current =
        next ||
        (await api<any>(`/api/bd/proposals/${proposal.id}`, {
          headers: roleHeaders(role),
        }));
      setProposal(normalize(unwrap(current)));
    } catch (e) {
      setError(e);
    }
  };
  useEffect(() => {
    const onPop = () =>
      setView(
        (new URLSearchParams(window.location.search).get("view") as ViewKey) ||
          "overview",
      );
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);
  const navigate = (next: ViewKey) => {
    window.history.pushState(
      {},
      "",
      `${window.location.pathname}?view=${next}`,
    );
    setView(next);
  };
  const common = {
    proposal,
    role,
    refresh,
    setError,
    setMessage,
    onNavigate: navigate,
  };
  const errorMessage =
    error instanceof Error
      ? error.message
      : error
        ? text(error, "Proposal action failed.")
        : "";
  return (
    <div className="proposal-workspace-shell">
      <ProposalHeader
        proposal={proposal}
        onBack={onBack}
        role={role}
        view={view}
        onNavigate={navigate}
      />
      <div className="proposal-toolbar">
        <span className="proposal-toolbar-status">
          {message || errorMessage || "Canonical Proposal projection loaded"}
        </span>
        <button
          className="button-secondary"
          onClick={() => setRailOpen((open) => !open)}
          aria-expanded={railOpen}
        >
          {railOpen ? "Hide context" : "Show context"}
        </button>
        <button className="button-secondary" onClick={() => void refresh()}>
          Refresh
        </button>
      </div>
      {error && (
        <div className="error-state" role="alert">
          {errorMessage}
          <button className="text-button" onClick={() => setError("")}>
            Dismiss
          </button>
        </div>
      )}
      <div
        className={`proposal-workspace-body ${railOpen ? "with-rail" : "full-width"}`}
      >
        <main className="proposal-main-view">
          {view === "overview" && (
            <Overview proposal={proposal} onNavigate={navigate} />
          )}
          {view === "intake" && <Intake {...common} />}
          {view === "engineering" && <Engineering {...common} />}
          {view === "commercial" && <Commercial {...common} />}
          {view === "response" && <Response {...common} />}
          {view === "outputs" && (
            <Outputs
              proposal={proposal}
              onNavigate={navigate}
              role={role}
              setError={setError}
              setMessage={setMessage}
            />
          )}
          {view === "history" && <History {...common} />}
        </main>
        {railOpen && (
          <ContextRail
            proposal={proposal}
            view={view}
            onRefresh={() => void refresh()}
          />
        )}
      </div>
    </div>
  );
}

export function ProposalCreate({
  role,
  onBack,
  onCreated,
}: {
  role: ProposalRole;
  onBack: () => void;
  onCreated: (id: string) => void;
}) {
  const [clients, setClients] = useState<any[]>([]);
  const [description, setDescription] = useState("");
  const [reference, setReference] = useState("");
  const [clientId, setClientId] = useState("");
  const [sourceType, setSourceType] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    void api<any>("/api/proposals-main?persona=SYSTEM_ADMIN&view=proposals", {
      headers: roleHeaders(role),
    })
      .then((data) => setClients(list(data.clients)))
      .catch(() => setClients([]));
  }, [role]);
  const sourceOptions = [
    { value: "TENDER_EMAIL", label: "Tender Email" },
    { value: "TENDER_DOCUMENT", label: "Tender Document" },
    { value: "TENDER_PHOTO", label: "Tender Photo / Image" },
    { value: "CLIENT_DATA", label: "Client Information" },
  ];
  const create = async () => {
    if (!description.trim() || !clientId) {
      setError("Select a canonical Client and enter a Proposal description.");
      return;
    }
    if (sourceType && !file) {
      setError("Choose the selected source file before creating the Proposal.");
      return;
    }
    setBusy(true);
    try {
      let result: any;
      if (sourceType && file) {
        const body = new FormData();
        body.append("proposal_description", description.trim());
        body.append("project_reference", reference);
        body.append("client_account_id", clientId);
        body.append("initial_source_type", sourceType);
        body.append("file", file);
        result = await api<any>("/api/bd/proposals/intake", {
          method: "POST",
          headers: roleHeaders(role),
          body,
        });
      } else {
        result = await api<any>("/api/bd/proposals", {
          method: "POST",
          headers: { ...roleHeaders(role), "Content-Type": "application/json" },
          body: JSON.stringify({
            proposal_description: description.trim(),
            project_reference: reference,
            client_account_id: clientId,
          }),
        });
      }
      onCreated(result.proposal?.id || result.id);
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "Proposal could not be created. No source was claimed.",
      );
    } finally {
      setBusy(false);
    }
  };
  return (
    <section className="panel route-detail-page proposal-create-panel">
      <div className="panel-head">
        <div>
          <span className="eyebrow">BD · NEW PROPOSAL</span>
          <h2>New Proposal Intake</h2>
          <p>
            Start from one canonical Client, then add Proposal context and
            optional source evidence. Client identity is never free text.
          </p>
        </div>
        <button className="text-button" onClick={onBack}>
          ← Proposal list
        </button>
      </div>
      {error && (
        <div className="error-state" role="alert">
          {error}
        </div>
      )}
      <div className="proposal-form-grid">
        <BusinessPicker
          label="Canonical Client"
          value={clientId}
          onChange={setClientId}
          options={clients.map((item: any) => ({
            value: item.id,
            label: `${text(item.name || item.display_name || item.legal_name)} · ${text(item.reference || item.client_reference)}`,
          }))}
          placeholder={
            clients.length
              ? "Select canonical Client"
              : "No canonical Clients available"
          }
        />
        <label>
          Proposal / opportunity description
          <input
            aria-label="Proposal Description"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />
        </label>
        <label>
          Opportunity reference
          <input
            aria-label="Opportunity reference"
            value={reference}
            onChange={(event) => setReference(event.target.value)}
            placeholder="Optional provisional reference"
          />
        </label>
      </div>
      <div className="proposal-intake-step">
        <h3>Optional initial source</h3>
        <div className="bd-source-grid">
          {sourceOptions.map((item) => (
            <button
              type="button"
              key={item.value}
              aria-pressed={sourceType === item.value}
              className={`bd-source-card ${sourceType === item.value ? "complete" : ""}`}
              onClick={() => setSourceType(item.value)}
            >
              <b>{item.label}</b>
              <small>
                {sourceType === item.value
                  ? `${item.label} Selected · intake panel open`
                  : "Choose to prepare this source"}
              </small>
            </button>
          ))}
        </div>
        {sourceType && (
          <div className="bd-source-intake-panel" aria-live="polite">
            <h4>
              {sourceOptions.find((item) => item.value === sourceType)?.label}{" "}
              intake
            </h4>
            <p className="muted">
              This source remains evidence with provenance. Extraction does not
              overwrite Proposal values.
            </p>
            <div className="proposal-upload-row">
              <label>
                Source file
                <input
                  aria-label={`${sourceOptions.find((item) => item.value === sourceType)?.label} source file`}
                  type="file"
                  onChange={(event) => setFile(event.target.files?.[0] || null)}
                />
              </label>
            </div>
          </div>
        )}
      </div>
      <button
        className="button-primary"
        onClick={() => void create()}
        disabled={busy || !clientId}
      >
        {busy
          ? "Creating…"
          : sourceType
            ? `Create Proposal & Add ${sourceOptions.find((item) => item.value === sourceType)?.label}`
            : "Create Proposal"}
      </button>
    </section>
  );
}
