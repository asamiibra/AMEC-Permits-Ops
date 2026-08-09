# Readiness language simplification

The readiness experience is a practical setup checklist for AMEC. Every screen drawer and the consolidated `/admin/go-live-readiness` view now use:

- What this screen uses
- What this screen produces
- What we need from AMEC
- Needed, Requested, Provided, Configured, Tested, Ready, and Not Needed
- Needed before go-live, Optional for now, Using a safe fallback, and Ready

The registry contains 38 setup items. Governance-only asks for signed scope, Stage 2 approval, Sign-off C, G10, formal production authorization, formal sponsor approval, formal change-control approval, technical acceptance signatories, and formal risk acceptance were removed. Practical setup needs remain: data, Synology, Excel, portal access, MFA, permissions, roles, rules, templates, mappings, regulations, communications, finance/handover contacts, test documents, and support.

Before/after summary for all 38 setup items:

| ID | Before | After |
| --- | --- | --- |
| PR-BRAND-01 | Official approved brand asset | AMEC logo files |
| PR-SUP-01 | Named owner and escalation contacts | Main AMEC setup contact |
| PR-SUP-02 | Change-control process | People who can confirm setup changes |
| PR-DATA-01 | Approved Synology project location | Synology project location |
| PR-DATA-02 | Approved Project Excel workbook | Project Excel workbook |
| PR-DATA-03 | Approved owner and property evidence | Owner and property source documents |
| PR-DATA-04 | Representative production documents | Real sample documents for testing |
| PR-DATA-05 | Municipality status and comment source | Municipality status and comment source |
| PR-ACC-01 | Production file and network access | Project file and network access |
| PR-ACC-02 | Municipality account and read access | Municipality account and access |
| PR-ACC-03 | Approved Municipality interaction mode | Municipality working mode |
| PR-ACC-04 | AI/provider route approval | AI/provider route and data geography |
| PR-ACC-05 | Communication send policy | Communication send setup |
| PR-ID-01 | Production identity and login model | Identity and login model |
| PR-ID-02 | Named pilot users and role mapping | Users and role mapping |
| PR-ID-03 | Separation of duties | Role separation and backup |
| PR-ID-04 | Final Submitter and Authorized Engineer | Final Submitter and Authorized Engineer |
| PR-ID-05 | MFA and attended-session procedure | MFA and attended-session setup |
| PR-SEC-01 | Permission to process customer data | Data handling and storage setup |
| PR-RULE-01 | Field authority matrix | Field authority and conflict rules |
| PR-RULE-02 | Approved requirement/dependency logic | Requirement and validity rules |
| PR-RULE-03 | Project and reference-number rules | Project and reference-number rules |
| PR-RULE-04 | Findings, closure, and escalation expectations | Findings, closure, and escalation rules |
| PR-RULE-05 | Approved portal mappings | Portal field and attachment mappings |
| PR-RULE-06 | Approved pilot scenario and project | Permit type and first project |
| PR-TPL-01 | Approved AMEC forms and templates | AMEC forms and templates |
| PR-TPL-02 | Approved Excel and output mappings | Excel and output mappings |
| PR-TPL-03 | Approved communication templates | Communication templates |
| PR-MAP-01 | Document and attachment matrix | Document and attachment matrix |
| PR-REG-01 | Approved regulation sources and editions | Regulation sources and editions |
| PR-REG-02 | Engineering disciplines and drawing formats | Engineering disciplines and drawing formats |
| PR-COM-01 | Communication recipients and delivery escalation | Communication recipients and delivery follow-up |
| PR-OPS-01 | Support, incident, and maintenance model | Support, incidents, and maintenance |
| PR-OPS-02 | Production volume and concurrency | Expected volume and concurrency |
| PR-OPS-03 | Backup, restore, retention, and exit | Backup, restore, retention, and handover |
| PR-ACCPT-01 | Acceptance corpus and ground truth | Test documents and expected results |
| PR-ACCPT-02 | Acceptance thresholds and signatories | Test targets and AMEC reviewer |
| PR-FIN-01 | Commercial, contract, finance, and handover authority | Commercial, contract, finance, and handover contacts |

The last row is intentionally a single practical contacts item for optional expanded modules; runtime commercial review, contract review, finance follow-up, and human handover boundaries remain unchanged.

The underlying status enum remains stable for compatibility, but user-facing labels are mapped to the simpler setup vocabulary. See [ProductionReadiness.tsx](../../frontend/src/ProductionReadiness.tsx), [readiness-language.test.ts](../../frontend/tests/readiness-language.test.ts), and [amec-logo-asset-readiness.md](16-amec-brand-asset-readiness.md).

## Review result

- Material screen routes reviewed: 49
- Screens with outdated readiness copy: 0
- Formal governance-only customer asks: 0
- Route coverage: 100%
- Practical AMEC setup asks preserved: yes
- Runtime approval, RBAC, MFA, staleness, lineage, audit, Human Send, and human final submission boundaries preserved: yes
