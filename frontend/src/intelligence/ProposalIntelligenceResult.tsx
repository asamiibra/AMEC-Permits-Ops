import { asList, asRecord, text } from "../features/proposals/helpers";
import type { JsonRecord } from "../features/proposals/types";
import { BidiCode, BidiText } from "../BidiText";

type Citation = JsonRecord;

function stringList(value: unknown): string[] {
  return Array.isArray(value) ? value.map((item) => text(item, "Not identified")) : [];
}

function Section({ title, values }: { title: string; values: unknown }) {
  const items = stringList(values);
  return <section className="proposal-intelligence-output-section"><h5>{title}</h5>{items.length ? <ul>{items.map((item, index) => <li key={`${item}-${index}`}><BidiText>{item}</BidiText></li>)}</ul> : <p className="muted">None identified.</p>}</section>;
}

function Differences({ values }: { values: unknown }) {
  const items = asList(values);
  return <section className="proposal-intelligence-output-section"><h5>Differences</h5>{items.length ? <div className="proposal-intelligence-differences"><table><thead><tr><th>Field</th><th>Proposal value</th><th>LPO value</th><th>Evidence key</th></tr></thead><tbody>{items.map((item, index) => <tr key={`${text(item.field, "field")}-${index}`}><th><BidiText>{text(item.field, "Not identified")}</BidiText></th><td><BidiText>{text(item.proposal_value, "—")}</BidiText></td><td><BidiText>{text(item.lpo_value, "—")}</BidiText></td><td><BidiCode>{text(item.evidence_key, "Not identified")}</BidiCode></td></tr>)}</tbody></table></div> : <p className="muted">None identified.</p>}</section>;
}

export function ProposalIntelligenceEvidence({ citations }: { citations: Citation[] }) {
  return <section className="proposal-intelligence-output-section" aria-label="Citations and evidence"><h5>Citations / evidence</h5>{citations.length ? <ul className="proposal-intelligence-citations">{citations.map((citation, index) => { const locator = asRecord(citation.locator); return <li key={`${text(citation.citation_key, `citation-${index}`)}-${index}`}><BidiCode as="b">{text(citation.citation_key, `CIT-${index + 1}`)}</BidiCode><BidiText as="span">{text(citation.source_type, "Governed evidence")} · {text(citation.source_id, "Canonical identity not supplied")}</BidiText><BidiText as="small">Version / hash: {text(citation.source_version_or_hash, "Not supplied")} · Locator: {text(locator.context_key ?? locator.locator ?? locator.context_snapshot_id, "Not supplied")}</BidiText></li>; })}</ul> : <p className="muted">No persisted citation metadata was returned.</p>}</section>;
}

export function ProposalIntelligenceResult({ operation, output, citations = [] }: { operation: string; output: JsonRecord; citations?: Citation[] }) {
  const summary = text(output.summary ?? output.explanation, "Structured Proposal result");
  const intake = operation === "intake-analysis" || operation === "tender-intake-analysis";
  const technical = operation === "scope-technical-analysis" || operation === "section-draft";
  const readiness = operation === "readiness-explanation" || operation === "handoff-preflight";
  return <div className="proposal-intelligence-result" data-testid="proposal-intelligence-result" aria-live="polite"><BidiText as="b">{summary}</BidiText>{intake && <><Section title="Missing information" values={output.missing_information} /><Section title="Contradictions" values={output.contradictions} /><Section title="Unresolved candidate facts" values={output.unresolved_candidate_facts} /><Section title="Source currentness issues" values={output.source_currentness_issues} /></>}{operation === "requirement-evidence-analysis" && <><Section title="Candidate requirements" values={output.requirement_candidates} /><Section title="Open questions" values={output.open_questions} /></>}{technical && <><Section title="Draft content" values={output.draft_content ? [output.draft_content] : []} /><Section title="Assumptions" values={output.assumptions} /><Section title="Exclusions" values={output.exclusions} /><Section title="Unresolved technical questions" values={output.unresolved_technical_questions} /><Section title="Recommendation notes" values={output.recommendation_notes} /></>}{operation === "commercial-consistency-review" && <><Section title="Variances" values={output.variances} /><Section title="Open questions" values={output.open_questions} /></>}{operation === "lpo-variance-analysis" && <><div className="proposal-intelligence-output-meta"><span>Accepted revision: <BidiCode as="b">{text(output.accepted_revision_id, "Not supplied")}</BidiCode></span><span>LPO evidence: <BidiCode as="b">{text(output.lpo_evidence_id, "Not supplied")}</BidiCode></span></div><Differences values={output.differences} /></>}{readiness && <><Section title="Blockers" values={output.blockers || output.deterministic_blockers} /><Section title="Stale dependencies" values={output.stale_dependencies} /><Section title="Missing information" values={output.missing_information} /><Section title="Next permissible human actions" values={output.next_permissible_human_actions} /></>}<ProposalIntelligenceEvidence citations={citations} /><small>Human review required · canonical state unchanged · protected actions remain unavailable.</small></div>;
}
