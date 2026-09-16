import { useEffect, useState, type FormEvent } from "react";
import type { ContractData } from "./contractTypes";
import { getStartPrerequisites, recordTimingFact, recordTimingRequirement } from "./contractApi";
import { timingFacts, type StartPrerequisites, type TimingFactType, type TimingTransition } from "./timingTypes";

const transitions: Record<TimingTransition, string> = {
  COMMERCIAL_START: "Commercial start", PROJECT_ACTIVATION: "Project activation",
  DESIGN_START: "Design start", CONTRACT_DURATION_START: "Contract duration start",
  MUNICIPALITY_WORK_START: "Municipality work start",
};
const human = (value: string) => value.toLowerCase().replaceAll("_", " ").replace(/^./, c => c.toUpperCase());

export function ContractTiming({ data, onRefresh }: { data: ContractData; onRefresh: () => Promise<void> | void }) {
  const [projection, setProjection] = useState<StartPrerequisites | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [fact, setFact] = useState<TimingFactType>("CLIENT_ARCHITECTURE_APPROVED");
  const [applicable, setApplicable] = useState(true);
  const [requiredFor, setRequiredFor] = useState<TimingTransition[]>([]);
  const [clause, setClause] = useState("");
  const [policy, setPolicy] = useState("");
  const [documentId, setDocumentId] = useState("");
  const [effectiveDate, setEffectiveDate] = useState("");
  const [reason, setReason] = useState("");
  const [retry, setRetry] = useState(0);
  const accepted = Boolean(data.current_revision?.accepted);
  const immutable = accepted || ["FINALIZED", "EXECUTED_EVIDENCE_RECORDED"].includes(data.current_revision?.status || "");
  const requirement = projection?.facts.find(item => item.fact === fact);
  const documents = [data.client_document?.document, data.po?.document, data.lpo?.document,
    ...(data.evidence || []).map(item => item.document)].filter((item): item is NonNullable<typeof item> => Boolean(item?.id));
  const uniqueDocuments = [...new Map(documents.map(item => [item.id, item])).values()];
  const selectedDocument = uniqueDocuments.find(item => item.id === documentId);

  useEffect(() => {
    let current = true;
    setError("");
    getStartPrerequisites(data.id).then(value => { if (current) setProjection(value); }).catch(cause => { if (current) setError(cause instanceof Error ? cause.message : "Timing requirements could not be loaded."); });
    return () => { current = false; };
  }, [data, retry]);

  const save = async (event: FormEvent) => {
    event.preventDefault();
    if (busy || !projection || !selectedDocument) return;
    setBusy(true); setError(""); setMessage("");
    let recorded = false;
    try {
      if (accepted) {
        if (!requirement?.applicable || !requirement.policy_version || !projection.contract_revision_id) throw new Error("An applicable requirement on the accepted revision is needed first.");
        await recordTimingFact(data.id, fact, {
          contract_revision_id: projection.contract_revision_id, effective_date: effectiveDate,
          trigger_type: fact, source_clause: requirement.source_clause,
          policy_version: requirement.policy_version, source_document_version_id: documentId,
          source_reference: selectedDocument.source_path_or_reference || selectedDocument.filename || "Supporting Contract document",
          reason,
        });
      } else {
        await recordTimingRequirement(data.id, { fact, applicable, required_for: applicable ? requiredFor : [], source_clause: clause, source_document_version_id: documentId, policy_version: policy, reason });
      }
      recorded = true;
      await onRefresh();
      setProjection(await getStartPrerequisites(data.id));
      setMessage(accepted ? "Timing fact recorded and refreshed from the Contract record." : "Timing requirement recorded and refreshed from the Contract record.");
      setReason("");
    } catch (cause) {
      setError(`${recorded ? "The event was recorded, but refresh failed. Refresh before making another change. " : ""}${cause instanceof Error ? cause.message : "Timing could not be saved."}`);
    } finally { setBusy(false); }
  };

  return <section id="contract-timing" className="contract-panel" aria-labelledby="contract-timing-title">
    <div className="contract-panel-heading"><div><span className="eyebrow">START REQUIREMENTS & DATES</span><h2 id="contract-timing-title">Timing requirements & facts</h2><p>Contract duration, architecture approval, municipality start and Project Activation have separate evidence and dates.</p></div></div>
    {error && <div role="alert" className="contract-error"><p>{error}</p><button type="button" className="button-secondary" onClick={() => setRetry(value => value + 1)}>Refresh timing</button></div>}
    {!projection && !error && <p role="status">Loading governing requirements…</p>}
    {projection && <>
      <div className="contract-table-scroll" tabIndex={0} role="region" aria-label="Independent Contract start facts"><table className="contract-facts-table"><caption>Independent start facts — current Contract revision</caption><thead><tr><th scope="col">Fact</th><th scope="col">Applicability</th><th scope="col">State</th><th scope="col">Required before</th></tr></thead><tbody>{projection.facts.map(item => <tr key={item.fact}><th scope="row">{timingFacts[item.fact as TimingFactType] || human(item.fact)}</th><td>{item.applicable ? "Applicable" : "Not applicable"}</td><td>{human(item.state)}</td><td>{item.required_for.map(value => transitions[value as TimingTransition] || human(value)).join(", ") || "No transition specified"}</td></tr>)}</tbody></table></div>
      <h3>{accepted ? "Record a downstream timing fact" : "Record a revision timing requirement"}</h3>
      {immutable && !accepted ? <p>This revision is immutable. Its timing requirements are read-only.</p> : <form onSubmit={save}>
        <fieldset disabled={busy || Boolean(error)} className="contract-edit-form">
          <legend>{accepted ? "Evidence for the accepted revision" : "Requirement for the editable revision"}</legend>
          <label>Timing fact<select value={fact} onChange={event => { setFact(event.target.value as TimingFactType); setRequiredFor([]); }}>{Object.entries(timingFacts).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
          {!accepted && <><label>Applicability<select value={String(applicable)} onChange={event => setApplicable(event.target.value === "true")}><option value="true">Applicable</option><option value="false">Not applicable</option></select></label>
            <fieldset><legend>Required before</legend>{Object.entries(transitions).filter(([key]) => !(fact === "CLIENT_ARCHITECTURE_APPROVED" && key === "DESIGN_START")).map(([key, label]) => <label key={key}><input type="checkbox" disabled={!applicable} checked={requiredFor.includes(key as TimingTransition)} onChange={event => setRequiredFor(values => event.target.checked ? [...values, key as TimingTransition] : values.filter(value => value !== key))} />{label}</label>)}</fieldset>
            <label>Exact source clause<textarea required maxLength={1000} value={clause} onChange={event => setClause(event.target.value)} /></label>
            <label>Governing policy version<input required maxLength={120} value={policy} onChange={event => setPolicy(event.target.value)} /><small>Use the version identified by the governing Contract requirement.</small></label></>}
          {accepted && <><p>Governing clause: {requirement?.source_clause || "No governing requirement recorded"}</p><p>Policy: {requirement?.policy_version || "Not recorded"}</p><label>Effective date<input type="date" required value={effectiveDate} onChange={event => setEffectiveDate(event.target.value)} /></label></>}
          <label>{accepted ? "Supporting document version" : "Source document version"}<select required value={documentId} onChange={event => setDocumentId(event.target.value)}><option value="">Select a current Contract document…</option>{uniqueDocuments.map(item => <option key={item.id} value={item.id}>{item.filename || "Contract document"} · version {item.version_number || "—"}</option>)}</select></label>
          {!uniqueDocuments.length && <p>Add the source in Documents & Evidence before recording timing.</p>}
          <label>Reason<textarea required minLength={3} maxLength={1000} value={reason} onChange={event => setReason(event.target.value)} /></label>
          {accepted && !requirement?.applicable && <p>This fact is not applicable to the accepted revision; recording is unavailable.</p>}
          <button className="button-primary" disabled={!selectedDocument || (accepted && (!requirement?.applicable || !requirement.policy_version))}>{busy ? "Saving and refreshing…" : accepted ? "Record timing fact" : "Record timing requirement"}</button>
        </fieldset>
      </form>}
    </>}
    {message && <p role="status">{message}</p>}
  </section>;
}
