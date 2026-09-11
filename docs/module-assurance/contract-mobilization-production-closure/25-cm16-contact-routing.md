# CM-G16 purpose-specific operational contact routing

CM-G16 is implemented on the existing canonical domain. The resolver binds a
purpose-specific `ContactPoint` to the exact current Contract revision through
append-only `ContractAdminEvidence`, then requires the Project-scoped contact
to be verified/current and to have active, effective `OPERATIONAL_CONTACT` and
`OPERATIONAL_CONTACT_ORGANIZATION` PartyRoleAssignment rows. The organization
must match the ClientAccount canonical Party and a practical role is required.

Supported purposes are `GENERAL_PROJECT_FOLLOWUP`,
`MISSING_DOCUMENT_REQUEST`, `CONTRACT_COMMUNICATION`, `AUTHORITY_FOLLOWUP`,
`HANDOVER_COORDINATION`, and `BILLING_FOLLOWUP`.

Missing routing returns `CONTACT_RESOLUTION_REQUIRED`, creates a canonical
blocked/open WorkflowTask plus in-app NotificationEvent, and leaves actual
communication human-controlled. No raw contact value is placed in broad audit
or notification text. The resolver never reads `ClientContact` as a fallback;
`generic_fallback_used=false` and `generic_fallback_policy=DISALLOWED` are
explicit in every projection.

The focused synthetic persistence test covers distinct client/contact/owner
parties, organization and practical role, verified purpose-specific contact,
missing routing, purpose mismatch, stale/expired contact, history-preserving
contact replacement, and actionable blocked authority follow-up. It closes and
reopens database sessions before reading the canonical rows and audit trail.

CM_G16=CLOSED_AND_PROVEN
SOURCE11_OPERATIONAL_CONTACT_ROLE_ORGANIZATION=PASS
SOURCE11_MISSING_DOCUMENT_CONTACT_ROUTING=PASS
SOURCE11_CASE_HISTORY_EVENT_EVIDENCE=PASS
COMMUNICATION_AUTHORITY=HUMAN_CONTROLLED
GENERIC_CONTACT_FALLBACK=DISALLOWED
PROJECT_ISOLATION=PASS
PARTY_ISOLATION=PASS
