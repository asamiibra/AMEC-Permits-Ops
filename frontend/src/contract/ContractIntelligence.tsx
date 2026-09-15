import { useEffect, useState } from "react";
import { getContractIntelligence, runContractIntelligence } from "./contractApi";
import { userFacingError } from "../api";
import type { ContractIntelligence, IntelligenceSkill } from "./contractTypes";

const groups = [
  ["understanding", "Understanding", ["contract.document-understand", "contract.executed-copy-review", "contract.payment-terms-extract", "contract.deliverables-extract"]],
  ["reconciliation", "Reconciliation", ["contract.compare-to-proposal", "contract.compare-to-po-lpo"]],
  ["changes", "Changes", ["contract.revision-impact"]],
  ["risks", "Risks", ["contract.review-brief", "contract.operations-brief"]],
  ["open-questions", "Open questions", ["contract.client-inputs-extract", "contract.communication-draft"]],
] as const;

const stateLabel = (value: string) => value.replaceAll("_", " ");

function SkillCard({ skill, onRun, busy }: { skill: IntelligenceSkill; onRun: (skill: IntelligenceSkill) => void; busy: boolean }) {
  return <article className="ci-skill-card" data-testid={`skill-${skill.skill_id}`}>
    <div className="ci-skill-card-top"><span className="ci-ai-mark">AI assist</span><span className={`ci-skill-state ci-state-${skill.status.toLowerCase()}`}>{stateLabel(skill.status)}</span></div>
    <h4>{skill.name}</h4>
    <p>{skill.purpose}</p>
    <div className="ci-skill-meta"><span>v{skill.version}</span><span>{skill.human_review_required ? "Human review required" : "Review policy not set"}</span></div>
    <small className="ci-skill-reason">{skill.eligibility_reason}</small>
    {skill.status === "AVAILABLE" && <button className="button-secondary" disabled={busy} onClick={() => onRun(skill)}>{busy ? "Running…" : "Run governed analysis"}</button>}
  </article>;
}

export function ContractIntelligence({ contractId }: { contractId: string }) {
  const [data, setData] = useState<ContractIntelligence | null>(null);
  const [error, setError] = useState("");
  const [busySkill, setBusySkill] = useState("");
  const [result, setResult] = useState<Record<string, any> | null>(null);
  const [message, setMessage] = useState("");
  useEffect(() => { let active = true; getContractIntelligence(contractId).then((result) => { if (active) setData(result); }).catch((cause) => { if (active) setError(userFacingError(cause, "Intelligence status unavailable.")); }); return () => { active = false; }; }, [contractId]);
  const skillById = new Map((data?.skills || []).map((skill) => [skill.skill_id, skill]));
  const run = async (skill: IntelligenceSkill) => {
    setBusySkill(skill.skill_id); setMessage(""); setError("");
    try {
      const response = await runContractIntelligence(contractId, skill.skill_id, `contract-ui-${contractId}-${skill.skill_id}-${Date.now()}`);
      setResult(response); setMessage("Result persisted as a current, citation-backed candidate for human Contract review.");
    } catch (cause) { setError(userFacingError(cause, "Contract Intelligence could not run.")); }
    finally { setBusySkill(""); }
  };
  return <aside className="contract-intelligence" aria-label="Contract Intelligence" tabIndex={0}>
    <div className="ci-header"><div><span className="eyebrow">CONTRACT INTELLIGENCE</span><h2>Governed runtime</h2></div><span className="ci-ai-mark">Advisory</span></div>
    <div className="ci-runtime-state" role="status"><span className="ci-runtime-dot" />{data?.execution_state || "Loading runtime state"} · shared model gateway and context compiler</div>
    <p className="ci-intro">The 11 Contract skills use server-selected, authorized context and the shared runtime. Results are persisted, currentness-bound, citation-backed, and always require human review; they cannot mutate Contract or protected state.</p>
    {error && <p className="ci-error" role="alert">{error}</p>}
    {message && <p className="ci-success" role="status">{message}</p>}
    <div className="ci-groups">{groups.map(([id, label, skillIds]) => <section className="ci-group" key={id} aria-labelledby={`ci-${id}`}><h3 id={`ci-${id}`}>{label}</h3>{skillIds.map((skillId) => { const skill = skillById.get(skillId); return skill ? <SkillCard key={skillId} skill={skill} busy={busySkill === skillId} onRun={run} /> : <div className="ci-empty" key={skillId}>Skill catalogue unavailable</div>; })}</section>)}</div>
    {result && <section className="ci-result" aria-label="Latest Contract Intelligence result"><h3>Latest candidate</h3><strong>{result.summary || "Governed Contract result"}</strong><p>{(result.findings || []).join(" · ")}</p><small>Citations: {(result.citations || []).map((item: any) => item.citation_key || item).join(", ") || "none"} · review task {result.review_task_id || "created"}</small></section>}
    <div className="ci-boundary"><strong>Human authority boundary</strong><span>Findings remain advisory, citation-backed, and separate from the blue canonical Contract state and orange human actions.</span></div>
  </aside>;
}
