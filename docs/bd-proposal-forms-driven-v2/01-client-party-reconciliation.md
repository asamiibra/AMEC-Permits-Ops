# Client / Party reconciliation

The current commercial `ClientAccount` is the Proposal-facing buying/receiving organization and is not currently a foreign-key link to the canonical `Party` table. The canonical Party model already exists with bilingual names, identity fields, property ownership, representation, authorization, observations, and assertions. Historical Proposal and Contract records reference `ClientAccount`; that history must remain intact.

Decision: extend `ClientAccount` with a nullable canonical Party link rather than creating a Proposal legal-entity table. Existing ClientAccount identifiers remain valid compatibility references. Linking a Party is an explicit resolution action; name similarity alone does not create or merge a Party. The Proposal Contact remains a commercial contact and may reference a canonical Party/contact where available, but does not imply Owner, Applicant, Authorized Agent, or legal signatory.

Safe defaults retained: Commercial Client is distinct from Property Owner and Applicant; unresolved identity remains visible as unresolved; bilingual names are not machine-translated into verified counterparts.

Status: `RECONCILED_AND_VERIFIED`.
