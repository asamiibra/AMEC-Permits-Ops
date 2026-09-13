import { useEffect, useState } from "react";
import { getContractIntelligence } from "./contractApi";
import type { ContractIntelligence, IntelligenceSkill } from "./contractTypes";

const groups = [
  ["understanding", "Understanding", ["contract.document-understand", "contract.executed-copy-review", "contract.payment-terms-extract", "contract.deliverables-extract"]],
  ["reconciliation", "Reconciliation", ["contract.compare-to-proposal", "contract.compare-to-po-lpo"]],
  ["changes", "Changes", ["contract.revision-impact"]],
  ["risks", "Risks", ["contract.review-brief", "contract.operations-brief"]],
  ["open-questions", "Open questions", ["contract.client-inputs-extract", "contract.communication-draft"]],
] as const;

const stateLabel = (value: string) => value.replaceAll("_", " ");

function SkillCard({ skill }: { skill: IntelligenceSkill }) {
  return <article className="ci-skill-card" data-testid={`skill-${skill.skill_id}`}>
    <div className="ci-skill-card-top"><span className="ci-ai-mark">AI assist</span><span className={`ci-skill-state ci-state-${skill.status.toLowerCase()}`}>{stateLabel(skill.status)}</span></div>
    <h4>{skill.name}</h4>
    <p>{skill.purpose}</p>
    <div className="ci-skill-meta"><span>v{skill.version}</span><span>{skill.human_review_required ? "Human review required" : "Review policy not set"}</span></div>
    <small className="ci-skill-reason">{skill.eligibility_reason}</small>
  </article>;
}

export function ContractIntelligence({ contractId }: { contractId: string }) {
  const [data, setData] = useState<ContractIntelligence | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { let active = true; getContractIntelligence(contractId).then((result) => { if (active) setData(result); }).catch((cause) => { if (active) setError(cause instanceof Error ? cause.message : "Intelligence status unavailable."); }); return () => { active = false; }; }, [contractId]);
  const skillById = new Map((data?.skills || []).map((skill) => [skill.skill_id, skill]));
  return <aside className="contract-intelligence" aria-label="Contract Intelligence" tabIndex={0}>
    <div className="ci-header"><div><span className="eyebrow">CONTRACT INTELLIGENCE</span><h2>Assistance rail</h2></div><span className="ci-ai-mark">Governed</span></div>
    <div className="ci-runtime-state" role="status"><span className="ci-runtime-dot" />{data?.runtime.external_inference_enabled ? "Intelligence runtime enabled" : "Available architecture · real-content execution not enabled"}</div>
    <p className="ci-intro">AI can explain evidence and prepare review material. It cannot accept, execute, verify payment, activate, send, or close a Contract.</p>
    {error && <p className="ci-error" role="alert">{error}</p>}
    <div className="ci-groups">{groups.map(([id, label, skillIds]) => <section className="ci-group" key={id} aria-labelledby={`ci-${id}`}><h3 id={`ci-${id}`}>{label}</h3>{skillIds.map((skillId) => { const skill = skillById.get(skillId); return skill ? <SkillCard key={skillId} skill={skill} /> : <div className="ci-empty" key={skillId}>Skill catalogue unavailable</div>; })}</section>)}</div>
    <div className="ci-boundary"><strong>Human authority boundary</strong><span>Findings remain advisory, citation-backed, and separate from the blue canonical Contract state and orange human actions.</span></div>
  </aside>;
}
