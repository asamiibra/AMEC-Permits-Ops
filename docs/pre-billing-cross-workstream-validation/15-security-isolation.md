# Security and isolation

Party, subject, authorization, contact, and source-document IDs are validated against the case/project scope. Writes require Owner/System Admin or the scoped Engineering/Preparer/Steward roles; Process Champion is read-only. Sensitive contact values are never returned by context APIs. Existing QID/identifier and document classification controls remain canonical. Journey/case joins, Permit read models, and ContractBillingContext retain project boundaries; no cross-project party/evidence path is permitted.
