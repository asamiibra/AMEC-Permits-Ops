# ProposalOps / AMEC — Phase 5 Classifier v2 Freeze + Shadow/Review + LOCAL/POSTGRESQL/BROWSER Validation
## Locked master execution design

## Phase identity
Phase 5 closes the missing classifier step before shadowing. It includes: content-assisted Classifier v2 calibration from verified evidence; robustness/regression; classifier freeze; integration with accepted Phase4; SHADOW replay/review; `VERIFIED_LOCAL`; `VERIFIED_POSTGRESQL`; `VERIFIED_BROWSER`.

It does not include production auto-promotion, real continuous Synology monitoring unless separately authorized, Synology writeback, Azure deployed certification, or cloud LLM processing of real AMEC content without authority.

## Hard entry gate
Require `PHASE4_INDEPENDENT_ACCEPTANCE=PASS`, exact `PHASE4_ACCEPTED_SHA`, exact Phase4 integration/freeze SHAs, Phase3C independent acceptance, exact Module Truth SHA, Stage1R-A complete and Stage1R-B not required. Otherwise `RESULT=PHASE5_NOT_AUTHORIZED_PHASE4_ACCEPTANCE_MISSING`, STOP.

Create `phase5-classifier-shadow-validation-v1` zero-delta from exact Phase4 accepted SHA.

## Robustness corpus
Create/freeze `AMEC_CLASSIFIER_ROBUSTNESS_CORPUS_V2`. Allowed: existing sanitized/golden fixtures; dangerous negatives; VERIFIED Stage1R evidence; sanitized derivatives; synthetic counterfactual/adversarial variants; reviewed correction events only for future versions. Never use unverified classifier output as ground truth. Raw AMEC content stays outside Git.

Track source family, format, business scope, source role, instantiation, module, family, Master Content candidacy, revision/currentness, project/entity link, duplicate/version, sensitivity, noise, path reliability. Cover M1-M7, FINANCE, MASTER_CONTENT FORM/REPORT/ENGINEERING_WORK/DEFINITION, REPORTS. Mark ADEQUATE/THIN/MISSING; do not invent quotas.

## Leakage-safe splits
Freeze CALIBRATION_DEVELOPMENT, VALIDATION, HOLDOUT_ADVERSARIAL. Group by source artifact/version, duplicates, template family, project/entity where feasible. Holdout remains untouched during development. Freeze manifest SHAs.

## Hybrid classifier
`DocumentEvidenceEnvelope → L0 prior-state/source mode → L1 hard gates → L2 typed rules/resolvers → L3 optional learned lane → L4 bounded LLM resolver → L5 cross-axis consistency → material review → ClassificationEnvelope proposal`.

LLM/model are not authority. Human review is not failure.

L0 distinguishes EXISTING_KNOWN_SOURCE, NEW_UNKNOWN_SOURCE, MODIFIED_KNOWN_SOURCE, MOVE_RENAME_CANDIDATE. Reuse frozen axes for known sources; reevaluate affected axes for modified sources; move/rename reuse only after identity proof.

L1 hard gates include object kind/noise, business scope, known identity, business/project identifiers, template IDs, duplicate graph, sensitivity. Scope values: CORE_IN_SCOPE, ADJACENT_RECOGNIZED, OUT_OF_SCOPE, AMBIGUOUS_REVIEW. OUT_OF_SCOPE means no deeper classifier, no LLM, no projection. SECRET_EXCLUDE means no LLM/index/preview/training/projection.

L2 decisions record rule_id, rule_version, axis, evidence_ids and cannot overwrite higher-authority evidence.

## Optional learned lane
Only if verified labels are sufficient. Compare rules-only vs rules+learned on untouched validation/holdout. Promote only with measurable benefit and no increase in critical false promotions. Otherwise `LEARNED_CLASSIFIER_MODE=NOT_PROMOTED_DATA_INSUFFICIENT`.

## LLM seam
Default `LLM_REAL_CONTENT_MODE=DISABLED`. Validate with synthetic/sanitized fixtures. LLM cannot override OUT_OF_SCOPE, declare canonical source, authorize Finance/professional approval, choose current version from prose, or execute protected actions.

## Confusable regressions
Mandatory: technical artifact vs business doc; blank vs false positive; directory vs file; backup vs active source; personal IBAN/payroll vs AMEC Finance; executed guarantee vs blank template; professional registration vs project permit; employee vs project handover; Shop Drawing vs Submittal; drawing vs authority submission; material technical data vs submittal; blank vs executed form; report template vs output; historical vs current; duplicate vs revision; path/filename hints vs stronger evidence; unresolved external provenance vs canonical AMEC authority. Contradiction→NEEDS_REVIEW.

## Acceptance philosophy and freeze
Optimize for `CRITICAL_FALSE_PROMOTIONS=0`, evidence-backed routing, useful coverage, safe abstention, bounded review, repeatability, cross-format/context robustness, low I/O, reproducibility. Require zero critical false promotions on golden, validation, untouched holdout/adversarial.

Freeze taxonomy revision, classifier version, rules version, ClassifierEnvelope schema SHA, calibration/validation/holdout manifests, golden/cross-format/cross-context/adversarial result SHAs, optional learned/LLM identities, LLM real-content mode, Document Intelligence Runtime/DocumentEvidenceEnvelope identity, Module Truth SHA, Phase4 Integration Contract SHA.

## SHADOW integration
Integrate frozen classifier with accepted Phase4:
`Source event/App Upload/replay → stability/version → Source Intake → DocumentEvidenceEnvelope → frozen Classifier v2 → ClassificationEnvelope → review comparison`.

SHADOW means classification generated and comparison recorded, but NO classifier-only VerifiedAssertion promotion, NO classifier-only typed projection, NO Synology writeback. VerifiedAssertion/projection may be exercised only through explicit review/test actions.

Review triggers: contradictions, AMBIGUOUS_REVIEW, low-confidence material module/family, project-link ambiguity, Master Content ambiguity, canonical conflict, external conflict, provenance dependency, unsupported parser. Optional unknown axis alone need not force review.

Every correction is immutable ClassifierCorrectionEvent. It cannot mutate this frozen version; changes belong to a future version.

## Shadow data sources / authority
Offline/replay shadow may use verified Stage1R evidence, golden/validation/holdout fixtures, and synthetic app uploads with no new NAS reads.

Real continuous shadow is separately authorized. Default:
- `REAL_LIVE_SHADOW_ENABLED=false`
- `NEW_SMB_CONNECTIONS=0`
- `NEW_AMEC_SOURCE_READS=0`
- no NAS secret
- no watcher

A future `AMEC_LIVE_SHADOW_ACTIVATION_MANIFEST_v1` is a separate gate.

## Verification states
Prove separately: `VERIFIED_LOCAL`, `VERIFIED_POSTGRESQL`, `VERIFIED_BROWSER`. Never infer `VERIFIED_DEPLOYED`.

### LOCAL
Full backend; full frontend; production build; golden/validation/holdout; cross-format/context; path counterfactual; unknown-family abstention; unsupported-capability review; Phase4 integration targeted suite.

### POSTGRESQL
Fresh disposable supported-major PostgreSQL; full migration chain; source-event idempotency; intake race/locks; immutable ClassificationEnvelope; review concurrency; append-only correction; VerifiedAssertion supersession; projection idempotency; side-effect de-duplication; rollback-on-failure; checkpoint/resume where applicable. SQLite cannot substitute.

### BROWSER
Use existing Playwright real-stack harness: real frontend→local backend→disposable PostgreSQL. Required paths:
1. NEW synthetic/app-upload→intake→classification→review→accept/correct→VerifiedAssertion→projection→audit/work.
2. AMBIGUOUS→reason visible→no auto-promotion.
3. OUT_OF_SCOPE→no deeper classifier/projection.
4. SECRET_EXCLUDE→no preview/model content.
5. modified known source→new version/affected-axis review.
6. move/rename→no duplicate logical record.
7. missing source→Issue/Notification/history retained.
8. correction→original envelope unchanged and correction event visible.
9. protected consequential action→server denial.
10. personas Owner/Business Development/Engineering see appropriate review/work.

Browser quality: no console errors/uncaught network failures in golden paths; loading/error/empty states; keyboard-accessible actions; basic axe pass; deep links resolve; root/correlation inspectable.

## Observability and drift
Each chain reconstructs root event, source/version/token, runtime/parser, classifier/rules/taxonomy/ModuleTruth/Phase4 identities, rule/evidence IDs, classification, review, optional reviewed projection, latency/bytes, LLM usage/cost, errors/retries. No secrets.

Track unknown/review/correction rates, module/business-scope/family/project/MasterContent corrections, unseen terms/families. Drift creates review/version-candidate work; never mutates frozen classifier.

## Production boundary after Phase5
Even after pass:
- `AUTO_PROMOTION_ENABLED=false`
- `REAL_LIVE_SHADOW_ENABLED=false` unless separately authorized
- `SYNOLOGY_WRITEBACK_ENABLED=false`
- `VERIFIED_DEPLOYED=false`

Allowed claim after actual pass: `PRODUCTION_CLASSIFIER_CANDIDATE=true` and `PRODUCTION_APP_CLASSIFICATION_READY_LOCAL_POSTGRESQL_BROWSER=true`, not deployed readiness.

## Artifacts and acceptance
Create Phase5 classifier freeze/runtime/input manifests plus coverage, regression, shadow, local, PostgreSQL, browser, and acceptance reports.

Codex must run at least 180 actual acceptance checks with per-check ID/category/assertion/method/evidence/result covering entry/ancestry, corpus provenance, no raw data, leakage, module coverage, negatives, source-mode/hard gates/rules, optional learned lane, LLM disabled-real-content, cross-axis invariants, critical false promotions, freeze identities, shadow boundaries, review/corrections, Phase4 integration, LOCAL/POSTGRESQL/BROWSER, persona/RBAC/protected actions, observability/drift, no NAS/SMB, no deployed claim, deterministic freeze.

Terminal if actually green:
- `PHASE5_CANDIDATE_COMPLETE=true`
- `CLASSIFIER_V2_FROZEN=true`
- `PRODUCTION_CLASSIFIER_CANDIDATE=true`
- `VERIFIED_LOCAL=true`
- `VERIFIED_POSTGRESQL=true`
- `VERIFIED_BROWSER=true`
- `VERIFIED_DEPLOYED=false`
- `AUTO_PROMOTION_ENABLED=false`
- `REAL_LIVE_SHADOW_ENABLED=false`
- `SYNOLOGY_WRITEBACK_ENABLED=false`
- `PHASE5_CODEX_SELF_ACCEPTED=false`
- `PHASE5_INDEPENDENT_ACCEPTANCE=PENDING`
- `NEXT=INDEPENDENT_PHASE5_REVIEW`

If any state fails, report it false and STOP; never weaken gates.


## Validation clarification — exact entry/domain/operational invariants
Required exact input identity fields:
- `PHASE4_INTEGRATION_CONTRACT_SHA256=<exact>`
- `AMEC_MODULE_TRUTH_CONTRACT_SHA256=<exact>`

Required domain coverage is explicit:
`M1`, `M2`, `M3`, `M4`, `M5`, `M6`, `M7`, `FINANCE`, `MASTER_CONTENT`, `REPORTS`.

Operational boundary:
- `SECRET_REQUIRED=false`
- classification, event intake, review decisions, VerifiedAssertion promotion, and projection retries must be idempotent where the operation contract requires retry safety.
