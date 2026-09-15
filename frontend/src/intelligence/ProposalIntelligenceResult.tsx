import { asList, asRecord, text } from "../features/proposals/helpers";
import type { JsonRecord } from "../features/proposals/types";

type Citation = JsonRecord;

function stringList(value: unknown): string[] {
  return Array.isArray(value) ? value.map((item) => text(item, "Not identified")) : [];
}

function Section({ title, values }: { title: string; values: unknown }) {
  const items = stringList(values);
  return <section className="proposal-intelligence-output-section"><h5>{title}</h5>{items.length ? <ul>{items.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul> : <p className="muted">None identified.</p>}</section>;
}

function Differences({ values }: { values: unknown }) {
  const items = asList(values);
  return <section className="proposal-intelligence-output-section"><h5>Differences</h5>{items.length ? <div className="proposal-intelligence-differences"><table><thead><tr><th>Field</th><th>Proposal value</th><th>LPO value</th><th>Evidence key</th></tr></thead><tbody>{items.map((item, index) => <tr key={`${text(item.field, "field")}-${index}`}><th>{text(item.field, "Not identified")}</th><td>{text(item.proposal_value, "—")}</td><td>{text(item.lpo_value, "—")}</td><td>{text(item.evidence_key, "Not identified")}</td></tr>)}</tbody></table></div> : <p className="muted">None identified.</p>}</section>;
}

export function ProposalIntelligenceEvidence({ citations }: { citations: Citation[] }) {
  return <section className="proposal-intelligence-output-section" aria-label="Citations and evidence"><h5>Citations / evidence</h5>{citations.length ? <ul className="proposal-intelligence-citations">{citations.map((citation, index) => { const locator = asRecord(citation.locator); return <li key={`${text(citation.citation_key, `citation-${index}`)}-${index}`}><b>{text(citation.citation_key, `CIT-${index + 1}`)}</b><span>{text(citation.source_type, "Governed evidence")} · {text(citation.source_id, "Canonical identity not supplied")}</span><small>Version / hash: {text(citation.source_version_or_hash, "Not supplied")} · Locator: {text(locator.context_key ?? locator.locator ?? locator.context_snapshot_id, "Not supplied")}</small></li>; })}</ul> : <p className="muted">No persisted citation metadata was returned.</p>}</section>;
}

export function ProposalIntelligenceResult({ operation, output, citations = [] }: { operation: string; output: JsonRecord; citations?: Citation[] }) {
  const summary = text(output.summary ?? output.explanation, "Structured Proposal result");
  return <div className="proposal-intelligence-result" data-testid="proposal-intelligence-result" aria-live="polite"><b>{summary}</b>{operation === "intake-analysis" && <><Section title="Missing information" values={output.missing_information} /><Section title="Contradictions" values={output.contradictions} /><Section title="Unresolved candidate facts" values={output.unresolved_candidate_facts} /><Section title="Source currentness issues" values={output.source_currentness_issues} /></>}{operation === "scope-technical-analysis" && <><Section title="Assumptions" values={output.assumptions} /><Section title="Exclusions" values={output.exclusions} /><Section title="Unresolved technical questions" values={output.unresolved_technical_questions} /><Section title="Eligibility dependencies" values={output.eligibility_dependencies} /><Section title="Recommendation notes" values={output.recommendation_notes} /></>}{operation === "lpo-variance-analysis" && <><div className="proposal-intelligence-output-meta"><span>Accepted revision: <b>{text(output.accepted_revision_id, "Not supplied")}</b></span><span>LPO evidence: <b>{text(output.lpo_evidence_id, "Not supplied")}</b></span></div><Differences values={output.differences} /></>}{operation === "readiness-explanation" && <><Section title="Blockers" values={output.blockers} /><Section title="Stale dependencies" values={output.stale_dependencies} /><Section title="Missing information" values={output.missing_information} /><Section title="Next permissible human actions" values={output.next_permissible_human_actions} /></>}<ProposalIntelligenceEvidence citations={citations} /><small>Human review required · canonical state unchanged · protected actions remain unavailable.</small></div>;
}
