# E5 engineering review contract

`EngineeringReviewScope` governs project, discipline, supported drawing types, selected regulation versions, applicability basis, objectives, exclusions, authorized role, Stage 2 disposition, and evidence class. `EngineeringReviewRun` pins the exact `DocumentVersion`, hash, revision label, scope, applicability snapshot, model/config bundle, prompt bundle, and evidence recipe. A trusted run requires `APPROVED_FOR_TEST` or `APPROVED_CONTROLLED_SOURCE` plus `APPROVED_APPLICABLE` human applicability. AI output is `PROPOSED_BY_AI` and never an approval.
