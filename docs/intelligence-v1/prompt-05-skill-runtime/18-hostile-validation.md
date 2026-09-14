# Hostile validation

Executed/static audit results:

- Pass A duplicate-engine audit: one manifest contract, one registry, one gateway, one generalized runtime, and reused P02 persistence stores; the legacy D3 function is a bounded compatibility adapter sharing the gateway.
- Pass B authority attack: non-`NONE` authority, real content, unregistered tool, unsupported model binding, unauthorized scope, and non-P04 context attempts fail closed by registry/gateway/compiler/runtime controls.
- Pass C failure-path attack: provider/validation failure finalizes `FAILED` with no successful work product/citations; completed duplicates replay; mutated keys conflict; active keys reject.
- Credential-pattern scan over P05 runtime/evidence/tests: no findings.
