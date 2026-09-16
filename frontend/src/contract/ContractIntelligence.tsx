import { useEffect, useState } from "react";
import { executeContractIntelligence, getContractIntelligence } from "./contractApi";
import type { ContractIntelligence, ContractIntelligenceResult, IntelligenceSkill } from "./contractTypes";

const groups = [
  [
    "understanding",
    "Understanding",
    [
      "contract.document-understand",
      "contract.executed-copy-review",
      "contract.payment-terms-extract",
      "contract.deliverables-extract",
    ],
  ],
  [
    "reconciliation",
    "Reconciliation",
    ["contract.compare-to-proposal", "contract.compare-to-po-lpo"],
  ],
  ["changes", "Changes", ["contract.revision-impact"]],
  ["risks", "Risks", ["contract.review-brief", "contract.operations-brief"]],
  [
    "open-questions",
    "Open questions",
    ["contract.client-inputs-extract", "contract.communication-draft"],
  ],
] as const;

const stateLabel = (value: string) => value.replaceAll("_", " ");

function SkillCard({ skill, running, result, error, onRun }: { skill: IntelligenceSkill; running: boolean; result?: ContractIntelligenceResult; error?: string; onRun: () => void }) {
  const eligible = skill.eligibility_state === "EXECUTABLE_WHEN_ELIGIBLE" && skill.runtime_ready === true;
  return (
    <article className="ci-skill-card" data-testid={`skill-${skill.skill_id}`}>
      <div className="ci-skill-card-top">
        <span className="ci-ai-mark">AI assist</span>
        <span
          className={`ci-skill-state ci-state-${skill.status.toLowerCase()}`}
        >
          {stateLabel(skill.eligibility_state || skill.status)}
        </span>
      </div>
      <h4>{skill.name}</h4>
      <p>{skill.purpose}</p>
      <div className="ci-skill-meta">
        <span>v{skill.version}</span>
        <span>
          {skill.human_review_required
            ? "Human review required"
            : "Review policy not set"}
        </span>
      </div>
      <small className="ci-skill-reason">{skill.eligibility_reason}</small>
      {skill.runtime_reason && <small className="ci-skill-reason">{skill.runtime_reason}</small>}
      {eligible && !result && (
        <button className="ci-run-button" type="button" onClick={onRun} disabled={running}>
          {running ? "Preparing advisory result…" : "Run advisory skill"}
        </button>
      )}
      {error && <p className="ci-error" role="alert">{error}</p>}
      {result && (
        <div className="ci-result" data-testid={`result-${skill.skill_id}`}>
          <strong>Advisory result</strong>
          <p>{result.output.summary}</p>
          {result.output.findings.map((finding) => <div className="ci-finding" key={finding.title}><b>{finding.title}</b><span>{finding.detail}</span></div>)}
          <small>Human review required · {result.citation_count} current citation{result.citation_count === 1 ? "" : "s"} · no canonical mutation</small>
        </div>
      )}
    </article>
  );
}

export function ContractIntelligence({ contractId }: { contractId: string }) {
  const [data, setData] = useState<ContractIntelligence | null>(null);
  const [error, setError] = useState("");
  const [running, setRunning] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, ContractIntelligenceResult>>({});
  const [skillErrors, setSkillErrors] = useState<Record<string, string>>({});
  useEffect(() => {
    let active = true;
    getContractIntelligence(contractId)
      .then((result) => {
        if (active) setData(result);
      })
      .catch((cause) => {
        if (active)
          setError(
            cause instanceof Error
              ? cause.message
              : "Intelligence status unavailable.",
          );
      });
    return () => {
      active = false;
    };
  }, [contractId]);
  const skillById = new Map(
    (data?.skills || []).map((skill) => [skill.skill_id, skill]),
  );
  const runSkill = (skillId: string) => {
    setRunning(skillId);
    setSkillErrors((current) => ({ ...current, [skillId]: "" }));
    const key = globalThis.crypto?.randomUUID?.() || `${contractId}:${skillId}:${Date.now()}`;
    executeContractIntelligence(contractId, skillId, key)
      .then((result) => setResults((current) => ({ ...current, [skillId]: result })))
      .catch((cause) => setSkillErrors((current) => ({ ...current, [skillId]: cause instanceof Error ? cause.message : "The advisory run could not be completed." })))
      .finally(() => setRunning(null));
  };
  return (
    <aside
      className="contract-intelligence"
      aria-label="Contract Intelligence"
      tabIndex={0}
    >
      <div className="ci-header">
        <div>
          <span className="eyebrow">CONTRACT INTELLIGENCE</span>
          <h2>Capability catalogue</h2>
        </div>
        <span className="ci-ai-mark">Advisory</span>
      </div>
      <div className="ci-runtime-state" role="status">
        <span className="ci-runtime-dot" />
        {data?.execution_state === "EXECUTABLE_WHEN_ELIGIBLE" ? "Shared Intelligence runtime integrated · advisory only" : "Intelligence status unavailable"}
      </div>
      <p className="ci-intro">
        These governed skills use server-compiled Contract context. Eligible
        skills can prepare advisory work for human review. They cannot change
        canonical Contract state or perform protected actions.
      </p>
      {error && (
        <p className="ci-error" role="alert">
          {error}
        </p>
      )}
      <div className="ci-groups">
        {groups.map(([id, label, skillIds]) => (
          <section className="ci-group" key={id} aria-labelledby={`ci-${id}`}>
            <h3 id={`ci-${id}`}>{label}</h3>
            {skillIds.map((skillId) => {
              const skill = skillById.get(skillId);
              return skill ? (
                <SkillCard key={skillId} skill={skill} running={running === skillId} result={results[skillId]} error={skillErrors[skillId]} onRun={() => runSkill(skillId)} />
              ) : (
                <div className="ci-empty" key={skillId}>
                  Skill catalogue unavailable
                </div>
              );
            })}
          </section>
        ))}
      </div>
      <div className="ci-boundary">
        <strong>Human authority boundary</strong>
        <span>
          Findings remain advisory, citation-backed, and separate from the blue
          canonical Contract state and orange human actions.
        </span>
      </div>
    </aside>
  );
}
