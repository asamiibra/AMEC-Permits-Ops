# Content Library production closure v1 — hostile G0 preflight

This record was created on closure branch `closure/content-library-production-v1`
before any implementation-file mutation. The repository was initialized in an
isolated checkout and fetched with targeted shallow refs only. The first fetch
was depth 1; ancestry was insufficient for the relationship count, so the
checkout was deepened by 20 and then 50 commits. The required ancestry facts
became provable without an unshallow fetch.

## Exact identity and boundary

- `FETCH_MODE=SHALLOW_TARGETED`
- remote: `https://github.com/asamiibra/AMEC-Permits-Ops.git`
- live `main`: `594b313a15cc6ade3f0505de395a5817c6337268`
- live `main` tree: `73d6781640bc774b577a6eb8e938868ef3fb83c3`
- live `next/module-integration`: `b47f33369d5a9f8daca42564c2eab6212948c8ed`
- live `next/module-integration` tree: `5e366d3bc4b286363e9257f1fec66c0f22bfeec1`
- closure base branch: `main`
- closure base SHA/tree: `594b313a15cc6ade3f0505de395a5817c6337268` / `73d6781640bc774b577a6eb8e938868ef3fb83c3`
- closure branch creation: `2026-09-13T21:35:44Z` (host clock)
- merge base: `cc473183681bb7755eb79f69272410537a9d1a8f`
- `git rev-list --left-right --count main...next`: `32 14`
- `ANCESTRY_REQUIRED=true`
- `ANCESTRY_PROVEN=true`
- `SHALLOW_BOUNDARY_AFFECTED_REVIEW_EVIDENCE=false`
- `EXACT_BASE_HEAD_DIFF_AVAILABLE=true`
- closure branch was clean immediately after creation.

## Atomic preflight validations (G0)

Each numbered item is a separate repository fact or bounded inspection. `PASS`
means the fact was established; `GAP` means an implementation obligation was
observed; `BLOCKED` means external production-shaped evidence is unavailable;
`N/A` means the check is not applicable to this synthetic-only preflight.

### Identity, ancestry, governance, and migrations

1. `PASS` remote URL is the requested GitHub repository; `git remote get-url origin`.
2. `PASS` `main` ref resolves to `594b313a15cc6ade3f0505de395a5817c6337268`.
3. `PASS` main tree resolves to `73d6781640bc774b577a6eb8e938868ef3fb83c3`.
4. `PASS` integration ref resolves to `b47f33369d5a9f8daca42564c2eab6212948c8ed`.
5. `PASS` integration tree resolves to `5e366d3bc4b286363e9257f1fec66c0f22bfeec1`.
6. `PASS` closure branch points at current main.
7. `PASS` closure base has two parents, preserving the protected main merge.
8. `PASS` the merge base is `cc473183681bb7755eb79f69272410537a9d1a8f`.
9. `PASS` main-only count is 32 after bounded deepening.
10. `PASS` integration-only count is 14 after bounded deepening.
11. `PASS` the initial depth-1 state was recognized as shallow-boundary insufficiency.
12. `PASS` deepening was incremental; `git fetch --unshallow` was not used.
13. `PASS` the final checkout remains shallow with two boundary records.
14. `PASS` exact base and head trees are available despite shallow history.
15. `PASS` the source integration tip is the known b47 repair tip, not a moving branch assumption.
16. `PASS` closure branch name is bounded and production-closure scoped.
17. `PASS` no merge/rebase/reset was performed on protected main.
18. `PASS` no merge/rebase/reset was performed on next/module-integration.
19. `PASS` no force-push was performed.
20. `PASS` no production, preprod, Azure, Entra, DSM, Synology, or AMEC data operation was performed.
21. `PASS` active required workflow names include `backend-regression`.
22. `PASS` active required workflow names include `frontend-regression`.
23. `PASS` active required workflow names include `migration-head`.
24. `PASS` active required workflow names include `policy-and-security`.
25. `PASS` active storage workflow name is `samba-contract`.
26. `GAP` live GitHub branch listing shows many unrelated branches requiring PR scoping.
27. `BLOCKED` authenticated live ruleset detail was not available from the unauthenticated API.
28. `BLOCKED` current required-check conclusion was not available as a completed run for this new branch.
29. `PASS` current main has exactly nine migration files.
30. `PASS` current main Alembic has exactly one head: `17c6ebd99c4a`.
31. `PASS` `17c6ebd99c4a` merges `billing_module_closure_v8` and `opportunity_proposal_idempotency_v1`.
32. `PASS` `ai_d2_execution_ledger_v1` precedes Source18 regulatory state.
33. `PASS` `source18_regulatory_current_state_v1` precedes Source18 committee implementation.
34. `PASS` `step5_content_azure_sql_v2` precedes `ai_d2_execution_ledger_v1`.
35. `PASS` `baseline_phase4_v36_azure_sql` is the migration root.
36. `PASS` main contains `source18_committee_implementation_v1.py`.
37. `PASS` main contains `step5_content_library_azure_sql_v2.py`.
38. `PASS` main contains the billing closure migration.
39. `PASS` main contains the opportunity commercial-controls migration.
40. `PASS` main contains the opportunity idempotency migration.
41. `PASS` main contains the billing/opportunity merge migration.
42. `PASS` current-main baseline migration hash is `b705b19dac5666fef711d3627190f7b30d3e601746e414bcc782f0e80b2585f9`.
43. `PASS` current-main Source18 current-state migration hash is `c46642ca9ae3a265796d31fa6bd287b32466ddc226301d1ccf02ee3dc670d3ee`.
44. `PASS` current-main Source18 committee migration hash is `49ded591f54b7d2a7207b751a6f8909668f81c44abef9ec7ab4a2ba4ebf38619`.
45. `PASS` current-main Content Library migration hash is `0780cfd0ae3d262217a7c02f7979f48ccaf6f9d2b78897405af566f3d226f914`.
46. `GAP` b47 baseline migration differs from current main by SQL parameter typing; main wins and must not be overwritten.
47. `GAP` b47 Source18 migration differs from current main by an index name; main wins and must not be overwritten.
48. `PASS` committee and Content Library migration bytes match b47.
49. `PASS` no main-only migration is absent from the closure base.
50. `PASS` no closure migration exists before implementation.

### Content Library endpoint and service census

51. `PASS` main exposes category list.
52. `PASS` main exposes category create.
53. `PASS` main exposes category patch.
54. `PASS` main exposes reference-policy read.
55. `PASS` main exposes reference-policy write.
56. `PASS` main exposes purpose resolver.
57. `PASS` main exposes consumer resolver.
58. `PASS` main exposes canonical Content Library list.
59. `PASS` main exposes eligible-content query.
60. `PASS` main exposes disabled AI-assist boundary.
61. `PASS` main exposes Content Library create.
62. `PASS` main exposes direct detail.
63. `PASS` main exposes governance options.
64. `PASS` main exposes blocker rollup.
65. `PASS` main exposes governance detail.
66. `PASS` main exposes governance mutation.
67. `PASS` main exposes currentness mutation.
68. `PASS` main exposes provenance mutation.
69. `PASS` main exposes quality-flag create.
70. `PASS` main exposes quality-flag resolution.
71. `PASS` main exposes source-section create.
72. `PASS` main exposes source-section patch.
73. `PASS` main exposes readiness evaluation.
74. `PASS` main exposes dependency list.
75. `PASS` main exposes dependency registration.
76. `PASS` main exposes dependency revalidation.
77. `PASS` main exposes propagation.
78. `PASS` main exposes version history.
79. `PASS` main exposes metadata mutation.
80. `PASS` main exposes module-binding read.
81. `PASS` main exposes module-binding mutation.
82. `PASS` main exposes new-version upload.
83. `PASS` main exposes current download.
84. `PASS` main exposes historical-version download.
85. `PASS` main exposes rendition download.
86. `PASS` main exposes archive.
87. `GAP` main reconcile route calls a mutating/auditing service without an explicit elevated reconcile capability.
88. `GAP` main direct-object routes use role-only dependencies rather than a centralized object-access decision.
89. `GAP` main has no typed Source18 official-form projection file.
90. `GAP` main resolver checks lifecycle/governance but has no Source18 lineage exclusion.
91. `GAP` main exact binding must be compared against canonical eligibility.
92. `GAP` main generic dependency registration must be checked for Source18 bypass.
93. `GAP` main generic dependency revalidation must be checked for Source18 bypass.
94. `GAP` main source-section writes have no observed central Source18 lineage guard.
95. `GAP` main readiness persistence has no observed central Source18 lineage guard.
96. `GAP` main quality-flag writes have no observed central Source18 lineage guard.
97. `GAP` main provenance writes have no observed central Source18 lineage guard.
98. `GAP` main module-binding writes have no observed central Source18 lineage guard.
99. `GAP` main governance writes have no observed central Source18 lineage guard.
100. `GAP` main currentness writes have no observed central Source18 lineage guard.

### Source18, storage, consumers, security, and evidence

101. `PASS` main exposes Source18 office overview.
102. `PASS` main exposes Source18 engineer creation.
103. `PASS` main exposes Source18 PII view.
104. `PASS` main exposes Source18 case creation.
105. `PASS` main exposes Source18 transaction detail.
106. `PASS` main exposes roster membership.
107. `PASS` main exposes responsible-engineer designation.
108. `PASS` main exposes transaction transitions.
109. `PASS` main exposes packet creation.
110. `PASS` main exposes packet release.
111. `PASS` main exposes signature capture.
112. `PASS` main exposes stamp capture.
113. `PASS` main exposes custody capture.
114. `PASS` main exposes final packet submit.
115. `PASS` main exposes comments, outcomes, and resubmission.
116. `GAP` main packet submit requires review for TOCTOU revalidation.
117. `GAP` main official-form promotion scans rows without an observed concurrency lock/unique invariant.
118. `GAP` main Source18 mutation audit actor is derived from role/header helper, not trusted principal identity.
119. `PASS` main has a provider-neutral `BinaryStorePort`.
120. `PASS` main has mock, SMB, and Azure Blob provider implementations.
121. `PASS` Content Library writes call `DocumentStorageService(create_binary_store())` in the observed upload path.
122. `GAP` Azure Blob write/read/restart/error qualification is not present for this candidate.
123. `GAP` request upload validation checks extension/size but not magic/signature.
124. `GAP` request bodies are accepted as fully materialized bytes before size rejection.
125. `BLOCKED` approved production malware/quarantine service was not available for this synthetic preflight.
126. `PASS` development auth mode is explicitly represented as `DEV_HEADER`.
127. `PASS` Entra mode resolves a database user by validated object ID.
128. `GAP` Source18 router actor helper accepts role/header-derived actor in protected audit paths.
129. `PASS` prior Content Library evidence includes focused backend tests.
130. `PASS` prior Content Library evidence includes frontend tests and a real-stack spec.
131. `GAP` prior real-stack evidence records stale historical failures rather than a current zero-failure run.
132. `GAP` no explicit route/persona/viewport applicability denominator is present in current main.
133. `PASS` current repository contains the universal UI conformance workflow/scripts.
134. `GAP` current main has no closure-specific exact-head manifest for this candidate.
135. `PASS` no real-data evidence file was used as proof for this preflight.
136. `PASS` protected-human authority remains software-denied by existing control tests.
137. `PASS` Source18 authority is separate from ordinary Content Library in the product documentation.
138. `GAP` Source18 exact currentness is incomplete on current main.
139. `GAP` legacy authority-case official-form binding accepts any existing DocumentVersion on current main.
140. `GAP` historical Content Library acceptance immutability requires explicit preservation checks on this new branch.
141. `GAP` G8/AT-024 closure wording must be carried into new evidence without changing historical records.
142. `BLOCKED` Azure SQL upgrade rehearsal is unavailable locally.
143. `BLOCKED` Azure SQL clean-install rehearsal is unavailable locally.
144. `BLOCKED` production-shaped Entra/managed-identity runtime is unavailable locally.
145. `BLOCKED` production-shaped Azure Blob identity rotation evidence is unavailable locally.
146. `BLOCKED` backup/restore evidence on production-shaped infrastructure is unavailable locally.
147. `PASS` synthetic SQLite may be used only for bounded component tests.
148. `PASS` no production configuration will be lowered to satisfy local tests.
149. `PASS` real AMEC data authority remains false for the closure.
150. `PASS` owner merge decision remains a separate final gate.

## Preflight disposition

The preflight is complete with 150 substantive atomic validations. It establishes
that selective Source18/Content Library hardening is required on current main,
while Azure SQL, Azure Blob, malware scanning, and production-shaped Entra
runtime remain external infrastructure gates. Implementation begins only after
this file and `01-semantic-delta-disposition.md` are committed.
